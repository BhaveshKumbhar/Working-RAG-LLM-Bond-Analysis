# OpenJev Consequence Analysis

## Purpose

This project uses a two-part analysis workflow for investor-focused bond covenant
review:

1. **Covenant existence analysis:** RAG retrieves relevant bond-document sections,
   and local OpenJev classifies whether each canonical covenant is present, absent,
   or unclear.
2. **Detail and consequence analysis:** Ollama extracts limits, frequency,
   exceptions, and investor explanations from the OpenJev decision and grounded
   text. OpenJev then ranks the investor consequences supported by exact evidence.

OpenJev is authoritative for the existence decision. Ollama does not replace that
decision; it enriches it with structured contractual details and readable
explanations.

This separation follows the recommended review approach: first determine whether a
covenant exists, then independently identify what may happen if that covenant is
breached.

## What OpenJev is

The project uses the local OpenJev model published at:

```text
AlexWortega/openjev
```

The configured model subfolder is:

```text
qwen3.5-0.8b-nli-v2s-long
```

This is a sequence-classification/NLI model. It receives two pieces of text:

- **Premise:** an exact evidence quote extracted from the bond document.
- **Hypothesis:** a possible investor consequence.

It returns scores for the model's labels:

- `contradiction`
- `entailment`
- `neutral`

The project reads the label mapping from the model configuration instead of
assuming that entailment has a particular numeric index.

OpenJev scores are used as **rankings**, not as calibrated legal probabilities.
A higher entailment score means that the source evidence more strongly supports
the tested consequence hypothesis relative to the other hypotheses.

## Why OpenJev is used

The Ollama model is useful for flexible detail extraction and explanation, while
both existence and consequence analysis benefit from a focused discriminative model:

- It does not generate free-form legal explanations.
- It compares source evidence against predefined consequence hypotheses.
- It produces structured scores that can be ranked deterministically.
- It reduces the risk of an autoregressive model inventing a remedy that is not
  supported by the document.
- It keeps the existence and consequence decisions grounded in source evidence.

OpenJev is therefore used to answer questions such as:

- Does this evidence support an event-of-default consequence?
- Does it support additional or default interest?
- Does it support a cure period?
- Does it support acceleration or early repayment?
- Does it support a trustee enforcement remedy?
- Does it support a waiver or consent requirement?

## Hardware and runtime

The integration was tested on:

```text
Operating system: Windows 11
GPU: NVIDIA GeForce RTX 3050 Laptop GPU
VRAM: 4 GB
Runtime device: CUDA
Python: project virtual environment
```

The model successfully loaded and ran on the RTX 3050 using CUDA. CPU fallback is
implemented for machines without a CUDA-compatible GPU, although inference will
be slower.

The local adapter is:

```text
openjev_consequence.py
```

The Phase 3 integration is in:

```text
phase3_rag_llm_pipeline.py
```

## Installation

Activate the existing project environment:

```powershell
& .\.venv\Scripts\Activate.ps1
```

Install the OpenJev Python dependencies:

```powershell
& .\.venv\Scripts\python.exe -m pip install transformers accelerate
```

Install a CUDA-compatible PyTorch build if PyTorch is not already installed:

```powershell
& .\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Verify CUDA:

```powershell
& .\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

The OpenJev model is downloaded automatically from Hugging Face the first time
the adapter is executed. The downloaded files are stored in the local Hugging
Face cache, not in the Git repository.

## Configuration

The default configuration in `openjev_consequence.py` is:

```python
REPO = "AlexWortega/openjev"
SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
```

The model subfolder can be overridden without editing source code:

```powershell
$env:OPENJEV_SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"
```

The default subfolder is recommended for this project's RTX 3050 hardware. Larger
OpenJev variants may require substantially more memory and are not selected by
the project.

## OpenJev adapter

The adapter exposes these important functions:

```python
load_openjev()
entailment_prob(premise, hypothesis)
consequence_entailment(premise, hypotheses)
```

### `load_openjev`

`load_openjev()`:

1. Loads the tokenizer.
2. Loads the sequence-classification model.
3. Places it on CUDA when available.
4. Switches the model to evaluation mode.
5. Reads the label mapping from `model.config.id2label`.
6. Caches the tokenizer and model globally.

The model is loaded once and reused across all covenant consequence evaluations.

### `entailment_prob`

`entailment_prob(premise, hypothesis)`:

1. Tokenizes the premise and hypothesis as a pair.
2. Truncates the pair to 512 tokens.
3. Runs inference without gradients.
4. Applies softmax to the output logits.
5. Returns the score associated with the dynamically discovered entailment label.

### `consequence_entailment`

`consequence_entailment()` evaluates multiple hypotheses against one premise in
one batched model call. This is used by Phase 3 to score all six consequence types
against one exact covenant evidence quote.

## Phase 3 workflow

The complete workflow is:

```text
data/master_list.txt
        |
        v
Phase 1: parse covenant master list and clean bond PDF
        |
        v
phase1_output/master_key.json
phase1_output/bond_cleaned.txt
        |
        v
Phase 2: detect numbered sections and create section-aware chunks
        |
        v
phase2_output/section_aware_chunks.json
        |
        v
Ollama embedding with nomic-embed-text
        |
        v
ChromaDB retrieval and lexical evidence grounding
        |
        v
OpenJev covenant existence analysis
        |
        v
Exact evidence quotes for present/partial covenants
        |
        v
OpenJev consequence entailment ranking
        |
        v
Investor Markdown report and JSON output
```

For each covenant, Part 1:

1. Embeds the covenant query with Ollama.
2. Retrieves candidate numbered bond sections from ChromaDB.
3. Reranks candidates using direct covenant vocabulary.
4. Extracts exact matching evidence spans.
5. Sends each grounded section and the covenant hypothesis to OpenJev.
6. Classifies the covenant as `present`, `absent`, or `unclear`.
7. Sends the OpenJev decision and grounded context to Ollama for limits,
   frequency, exceptions, and investor explanation extraction.

Only results classified as `present` or `partial` and containing an exact evidence
quote are passed to the consequence-ranking stage of OpenJev.

For each eligible covenant, Part 2:

1. Uses the exact source quote as the premise.
2. Scores the six consequence hypotheses.
3. Sorts the hypotheses from highest to lowest entailment score.
4. Stores all scores and the ranked order in the JSON output.
5. Displays the highest-ranked consequence in the Markdown report.

## Consequence hypotheses

The current hypotheses are defined in
`phase3_rag_llm_pipeline.py`:

| Category | Hypothesis tested |
|---|---|
| `event_of_default` | A breach of this covenant can constitute an event of default. |
| `default_interest` | A breach of this covenant can trigger additional or default interest. |
| `cure_period` | The issuer receives a defined period to cure or rectify a breach of this covenant. |
| `acceleration` | A breach of this covenant can permit acceleration, early repayment, or redemption. |
| `trustee_remedy` | The debenture trustee has an enforcement or remedy right for a breach of this covenant. |
| `waiver_and_consent` | Waiver or amendment of this covenant requires investor, lender, or trustee consent. |

These are deliberately short and consistent so the model compares the same
decision categories across all covenants.

## Running the project

Start Ollama first because it is still required for embeddings and detail
extraction; OpenJev performs the covenant existence classification:

```powershell
ollama serve
```

Verify that the required Ollama models are available:

```powershell
ollama list
```

The project expects:

```text
nomic-embed-text:latest
qwen3.5:0.8b
```

Run the complete pipeline:

```powershell
& .\.venv\Scripts\python.exe main.py
```

To rerun only Phase 3 after Phase 1 and Phase 2 outputs already exist:

```powershell
& .\.venv\Scripts\python.exe phase3_rag_llm_pipeline.py
```

The first OpenJev run may take longer because Hugging Face downloads and caches
the model. Later runs reuse the cached model.

## Output files

### JSON output

The complete machine-readable output is:

```text
phase3_output/covenant_analysis_rag_llm.json
```

OpenJev results are stored under:

```json
"openjev_consequence_analysis"
```

The object contains:

```json
{
  "provider": "openjev_local",
  "status": "success",
  "covenants_analyzed": 106,
  "model": {
    "repository": "AlexWortega/openjev",
    "subfolder": "qwen3.5-0.8b-nli-v2s-long",
    "device": "cuda",
    "label2id": {
      "contradiction": 0,
      "entailment": 1,
      "neutral": 2
    }
  },
  "results": []
}
```

Each result includes:

- `covenant_id`
- `covenant_name`
- `evidence_section`
- `evidence_quote`
- `ranked_consequences`
- `entailment_score` for every consequence category

### Investor Markdown report

The professor-facing report is:

```text
phase3_output/covenant_analysis_investor_rag_report.md
```

OpenJev output appears in:

```text
## Part 2 — Breach consequences and waiver mechanics
### OpenJev-ranked consequence support
```

The report table contains:

```text
| Covenant | Evidence section | Highest-ranked consequence | Score |
```

The report therefore gives the reader:

1. The covenant existence result.
2. The exact supporting document evidence.
3. The contract section containing that evidence.
4. The highest-ranked consequence identified by OpenJev.
5. The OpenJev entailment ranking score.

## Verified run

The local integration was tested successfully with:

```text
Canonical covenants: 111
Present or partial covenants passed to OpenJev: 106
OpenJev status: success
Runtime device: cuda
Model: qwen3.5-0.8b-nli-v2s-long
```

The model label mapping was detected as:

```text
contradiction -> 0
entailment    -> 1
neutral       -> 2
```

A smoke test also confirmed that a payment-default premise ranked acceleration
higher than an unrelated default-interest hypothesis.

## Error handling and limitations

If OpenJev cannot load, the pipeline:

- Logs the loading error.
- Records the OpenJev status as `error`.
- Records any label mapping discovered before the failure.
- Does not substitute Ollama or another generative model for OpenJev.

Important limitations:

- Entailment scores are rankings, not calibrated probabilities.
- A high score does not constitute legal advice.
- The model evaluates the supplied evidence quote; it does not search the entire
  bond document itself.
- If Part 1 cannot find a grounded quote, the existence result remains `unclear`
  and no consequence ranking is attempted.
- A consequence ranking must still be reviewed against the complete executed
  transaction documents by a legal professional.
- The exact source quote is more important than the score when interpreting a
  result.

## Summary for the professor

The implemented design separates the analysis into two auditable stages:

### Part 1: Covenant existence

RAG and Ollama identify whether a canonical covenant appears in the bond document.
The result is grounded in an exact source quote, section, page, and line range.

### Part 2: Covenant consequences

Local OpenJev receives that exact quote and ranks predefined investor consequences
using NLI entailment scores. It does not generate unsupported legal text.

This means the final report can show not only that a covenant exists, but also
which breach consequences are most strongly supported by the actual document
language.
