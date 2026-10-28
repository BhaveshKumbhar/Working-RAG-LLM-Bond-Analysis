import os
from typing import Any, Dict, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO = "AlexWortega/openjev"
SUBFOLDER = os.getenv("OPENJEV_SUBFOLDER", "qwen3.5-0.8b-nli-v2s-long")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

_tokenizer: Optional[Any] = None
_model: Optional[Any] = None
_label2id: Optional[Dict[str, int]] = None


class OpenJevLoadError(RuntimeError):
    """Model loading failure with any label mapping discovered before the failure."""

    def __init__(self, message: str, label2id: Optional[Dict[str, int]] = None):
        super().__init__(message)
        self.label2id = label2id or {}


def unload_openjev() -> None:
    """Release OpenJev memory before the Ollama model is used."""
    global _tokenizer, _model, _label2id
    _tokenizer = None
    _model = None
    _label2id = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def load_openjev() -> Dict[str, Any]:
    """Load the local OpenJev classifier once and expose its runtime metadata."""
    global _tokenizer, _model, _label2id
    if _model is None or _tokenizer is None or _label2id is None:
        dtype = torch.float16 if DEVICE == "cuda" else torch.float32
        try:
            _tokenizer = AutoTokenizer.from_pretrained(REPO, subfolder=SUBFOLDER)
            _model = AutoModelForSequenceClassification.from_pretrained(
                REPO,
                subfolder=SUBFOLDER,
                dtype=dtype,
            ).to(DEVICE).eval()
            _label2id = {
                str(label).lower(): int(index)
                for index, label in _model.config.id2label.items()
            }
        except Exception as exc:
            raise OpenJevLoadError(
                f"Could not load {REPO}/{SUBFOLDER} on {DEVICE}: {exc}",
                _label2id,
            ) from exc
        if "entailment" not in _label2id:
            raise OpenJevLoadError(
                f"OpenJev model has no entailment label: {_label2id}",
                _label2id,
            )
    return {
        "repository": REPO,
        "subfolder": SUBFOLDER,
        "device": DEVICE,
        "label2id": dict(_label2id),
    }


def entailment_prob(premise: str, hypothesis: str) -> float:
    """Probability that the premise (covenant clause) entails the hypothesis (consequence)."""
    load_openjev()
    inputs = _tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(DEVICE)
    with torch.no_grad():
        probs = _model(**inputs).logits.softmax(dim=-1)[0]
    return probs[_label2id["entailment"]].item()


def consequence_entailment(
    premise: str,
    hypotheses: Dict[str, str],
) -> Dict[str, Any]:
    """Score multiple consequence hypotheses against one source clause."""
    metadata = load_openjev()
    names = list(hypotheses)
    inputs = _tokenizer(
        [premise] * len(names),
        [hypotheses[name] for name in names],
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    ).to(DEVICE)
    with torch.no_grad():
        probabilities = _model(**inputs).logits.softmax(dim=-1)
    scores = {
        name: round(
            probabilities[index, _label2id["entailment"]].item(),
            6,
        )
        for index, name in enumerate(names)
    }
    return {"scores": scores, "model": metadata}


def nli_entailment_scores(
    premises: list[str],
    hypothesis: str,
) -> Dict[str, Any]:
    """Score one existence hypothesis against multiple retrieved premises."""
    metadata = load_openjev()
    inputs = _tokenizer(
        premises,
        [hypothesis] * len(premises),
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    ).to(DEVICE)
    with torch.no_grad():
        probabilities = _model(**inputs).logits.softmax(dim=-1)
    return {
        "scores": [
            {
                "contradiction": round(row[_label2id["contradiction"]].item(), 6),
                "entailment": round(row[_label2id["entailment"]].item(), 6),
                "neutral": round(row[_label2id["neutral"]].item(), 6),
            }
            for row in probabilities
        ],
        "model": metadata,
    }


if __name__ == "__main__":
    clause = ("In the event of a payment default, the Debenture Trustee may "
              "accelerate the redemption of all outstanding debentures.")
    consequences = [
        "Investors can demand early repayment after a default.",
        "Investors have no right to accelerate repayment.",
    ]
    for c in consequences:
        print(f"{entailment_prob(clause, c):.3f}  {c}")