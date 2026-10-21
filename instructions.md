# instruction.md: OpenJev Setup for Bond Covenant Project

## Context
This project analyzes 120 covenants from the Keertana Finserv bond document. Part 1 finds whether each covenant is present in the document. Part 2 uses OpenJev to check which investor consequences each present covenant supports. Do not use Ollama or a generative LLM for Part 2.

## How OpenJev is set up
- **Model:** AlexWortega/openjev on Hugging Face (MIT license). It is a Qwen3.5-based cross-encoder. It takes a premise and a hypothesis and returns entailment, contradiction, or neutral.
- **Runtime:** Python with `transformers`, `accelerate`, and PyTorch with CUDA, installed in the existing `.venv`.
- **Hardware:** NVIDIA RTX 3050, 4 GB VRAM, Windows 11 with PowerShell.
- **Model folder:** Load the model from a subfolder of the repo. The page references `qwen3.5-4b-nli`. Use the 0.8B subfolder if it fits, and check the model card for its exact name. The 4B model needs 4-bit quantization to fit in 4 GB.
- **Not used:** Ollama. Its GGUF builds are generative 9B models that do not fit in 4 GB VRAM.

## Installation (already documented steps)
```powershell
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate
python -c "import torch; print(torch.cuda.is_available())"
```

## Code
Use `openjev_consequence.py`. It exposes one function:

```python
entailment_prob(premise: str, hypothesis: str) -> float
```

- `premise` is a covenant clause from the bond document.
- `hypothesis` is an investor consequence, for example "Investors can demand early repayment after a default."
- Read label indices from `model.config.id2label`. Do not assume their order.
- Truncate inputs to 512 tokens. Keep premises to one clause or short paragraph.

## Rules for Copilot
1. Keep the OpenJev model loaded once and reuse it across calls.
2. Run on GPU when available, fall back to CPU otherwise.
3. Treat scores as rankings, not calibrated probabilities.
4. Do not hardcode favorability or gap logic. Derive results from entailment scores and the document text.
5. If model loading fails, print the error and the label mapping. Do not invent a substitute model.