#!/usr/bin/env python3
"""RAG + local Ollama LLM pipeline for investor-focused covenant analysis.

Pipeline:
1. Load the cleaned master covenant list and cleaned bond text-derived sections.
2. Embed every numbered bond section with Ollama nomic-embed-text.
3. Store section embeddings in a persistent ChromaDB collection.
4. Retrieve the three most relevant sections for every covenant.
5. Ask a local Ollama model to classify contractual presence and explain investor impact.
6. Apply deterministic critical-gap and score logic and write an investor report.

The LLM is never asked whether the issuer is currently complying. It only evaluates
whether the contractual covenant is present in the retrieved bond text.
"""

import json
import logging
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import chromadb
import requests

ROOT = Path(__file__).resolve().parent
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text:latest"
ANALYSIS_MODEL = "qwen3.5:0.8b"
ISSUER_TYPE = os.getenv("ISSUER_TYPE", "nbfc").strip().lower()
TOP_K = 3
RETRIEVAL_CANDIDATES = 10
MIN_LEXICAL_MATCH = 0.08
OPENJEV_PRESENCE_THRESHOLD = 0.35
OPENJEV_PRESENCE_MARGIN = 0.08

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def ollama_embed(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=120,
    )
    if response.status_code == 400 and "context length" in response.text.lower():
        words = text.split()
        shortened = " ".join(words[:450])
        logger.warning("Embedding text exceeded Ollama context; truncating to 450 words")
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": shortened},
            timeout=120,
        )
    response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if not embeddings or not embeddings[0]:
        raise RuntimeError("Ollama returned no embedding")
    return embeddings[0]


def ollama_analyze(prompt: str) -> Dict[str, Any]:
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": ANALYSIS_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "think": False,
            "options": {"temperature": 0.0, "num_predict": 512},
        },
        timeout=90,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "")
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError(f"LLM did not return JSON: {content[:200]}")
        result = json.loads(match.group(0))
    if not isinstance(result, dict):
        raise ValueError("LLM response was not a JSON object")
    return result


def load_inputs() -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    master = json.loads((ROOT / "phase1_output" / "master_key.json").read_text(encoding="utf-8"))
    covenants: List[Dict[str, Any]] = []
    for covenant_type in ("positive", "negative"):
        for covenant in master.get("by_type", {}).get(covenant_type, []):
            item = dict(covenant)
            item["covenant_type"] = covenant_type
            covenants.append(item)
    chunks = json.loads(
        (ROOT / "phase2_output" / "section_aware_chunks.json").read_text(encoding="utf-8")
    )
    covenants = canonicalize_covenants(covenants)
    if not covenants or not chunks:
        raise ValueError("Covenants or section-aware bond chunks are empty")
    return covenants, chunks


def canonicalize_covenants(covenants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse only known duplicate families without hiding distinct controls."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for covenant in covenants:
        name = covenant["name"].lower()
        if "security cover certificate" in name:
            group = "security_cover_certificates"
        elif "promoter shareholding" in name or "promoter stake" in name:
            group = "promoter_shareholding"
        elif covenant["covenant_type"] == "negative" and any(
            name.startswith(prefix)
            for prefix in (
                "no merger", "no demerger", "no amalgamation",
                "no consolidation", "no restructuring",
                "no scheme of arrangement", "no corporate reorganization",
            )
        ):
            group = "merger_restructuring_restrictions"
        else:
            group = covenant["id"]
        groups.setdefault(group, []).append(covenant)

    canonical: List[Dict[str, Any]] = []
    for group, members in groups.items():
        primary = dict(members[0])
        primary["canonical_group"] = group
        primary["member_ids"] = [item["id"] for item in members]
        primary["member_names"] = [item["name"] for item in members]
        if len(members) > 1:
            primary["name"] = (
                f"{primary['name']} "
                f"(also covers: {'; '.join(item['name'] for item in members[1:])})"
            )
            primary["description"] = primary["name"]
        canonical.append(primary)
    logger.info(
        "Canonicalized %d master-list entries into %d covenant requirements",
        len(covenants),
        len(canonical),
    )
    return canonical


def build_index(chunks: List[Dict[str, Any]]):
    client = chromadb.PersistentClient(path=str(ROOT / "phase2_output" / "chroma_rag_db"))
    collection = client.get_or_create_collection(
        name="bond_numbered_sections",
        metadata={"embedding_model": EMBED_MODEL, "chunking": "numbered_section_aware"},
    )
    ids = [str(chunk["id"]) for chunk in chunks]
    documents = [str(chunk["text"]) for chunk in chunks]
    metadatas = [
        {
            "source_section": str(chunk.get("source_section", "")),
            "source_title": str(chunk.get("source_title", "")),
            "parent_section": str(chunk.get("parent_section", "")),
            "page": int(chunk.get("page") or 0),
            "source_line_start": int(chunk.get("source_line_start") or 0),
            "source_line_end": int(chunk.get("source_line_end") or 0),
            "word_count": int(chunk.get("word_count", 0)),
        }
        for chunk in chunks
    ]
    embeddings: List[List[float]] = []
    for index, document in enumerate(documents, start=1):
        logger.info("Embedding bond section %d/%d", index, len(documents))
        embeddings.append(ollama_embed(document))
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    return collection


def normalized_terms(text: str) -> List[str]:
    """Return meaningful alphanumeric terms while preserving terms such as CHG-9."""
    normalized = re.sub(r"(?i)(chg)[\s-]*(\d+)", r"\1-\2", text)
    return [
        term.lower()
        for term in re.findall(r"[a-zA-Z]{3,}(?:-\d+)?|\b\d+(?:\.\d+)?\b", normalized)
        if term.lower() not in {
            "the", "and", "for", "with", "from", "below", "above", "within",
            "under", "where", "into", "this", "that", "shall", "ensure",
            "maintain", "provide", "submit", "no",
        }
    ]


def lexical_match_score(covenant_name: str, text: str) -> float:
    """Measure direct covenant-term support in a retrieved section."""
    query_terms = Counter(normalized_terms(covenant_name))
    if not query_terms:
        return 0.0
    text_lower = text.lower()
    compact_text = re.sub(r"[\s-]+", "", text_lower)
    weights = {
        term: (8 if any(char.isdigit() for char in term) else 2 if len(term) >= 9 else 1)
        for term in query_terms
    }
    matched = sum(
        count * weights[term]
        for term, count in query_terms.items()
        if term in text_lower or term.replace("-", "") in compact_text
    )
    total = sum(count * weights[term] for term, count in query_terms.items())
    return min(1.0, matched / max(1, total))


def exact_evidence(covenant_name: str, text: str, max_items: int = 2) -> List[str]:
    """Extract exact source spans containing the strongest covenant terms."""
    terms = [term for term in normalized_terms(covenant_name)
             if len(term) >= 4 and not term.isdigit()]
    if not terms:
        return []
    spans = re.split(r"(?<=[.!?])\s+|\n+", text)
    scored = []
    for span in spans:
        compact = span.strip()
        if not compact:
            continue
        compact_lower = compact.lower()
        compact_normalized = re.sub(r"[\s-]+", "", compact_lower)
        score = sum(
            term in compact_lower or term.replace("-", "") in compact_normalized
            for term in terms
        )
        if score:
            scored.append((score, compact))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [span[:700] for _, span in scored[:max_items]]


def rerank_retrieved(
    covenant_name: str,
    retrieved: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Prefer sections with direct covenant vocabulary over generic semantic hits."""
    for item in retrieved:
        item["lexical_match"] = round(
            lexical_match_score(covenant_name, item["text"]), 4
        )
        item["evidence"] = exact_evidence(covenant_name, item["text"])
        semantic_score = 1.0 / (1.0 + max(0.0, float(item["distance"])))
        item["grounding_score"] = round(
            0.7 * item["lexical_match"] + 0.3 * semantic_score, 4
        )
    return sorted(
        retrieved,
        key=lambda item: (item["grounding_score"], item["lexical_match"]),
        reverse=True,
    )[:TOP_K]


def classify_strength(name: str) -> tuple[str, str, str]:
    lowered = name.lower()
    if any(term in lowered for term in ("payment", "event of default", "acceleration", "early repayment")):
        explanation = "Payment and default remedies directly determine investor cash recovery."
        return "CRITICAL", explanation, f"Missing this safeguard increases recovery risk: {explanation}"
    if any(term in lowered for term in ("security", "collateral", "charge", "asset cover")):
        explanation = "Collateral and security controls support repayment priority."
        return "HIGH", explanation, f"Without this safeguard, recovery support is weaker: {explanation}"
    if any(term in lowered for term in (
        "crar", "capital adequacy", "npa", "dscr", "debt/equity",
        "financial", "profitability", "portfolio quality", "liquidity",
    )):
        explanation = "Financial thresholds provide early warning of repayment deterioration."
        return "HIGH", explanation, f"Without this safeguard, deterioration may go undetected: {explanation}"
    if any(term in lowered for term in (
        "dividend", "borrowing", "indebtedness", "leverage", "capital structure",
    )):
        explanation = "Capital and cash-distribution restrictions limit creditor dilution."
        return "HIGH", explanation, f"Without this safeguard, leverage and leakage risk increase: {explanation}"
    if any(term in lowered for term in ("report", "statement", "certificate", "audit", "information")):
        explanation = "Reporting supports ongoing investor monitoring."
        return "MEDIUM", explanation, f"Without this safeguard, monitoring becomes less timely: {explanation}"
    return "LOW", "Routine contractual protection.", "The absence reduces a routine layer of protection."


def priority_rank(strength: str) -> int:
    return {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}.get(strength, 4)


def not_applicable_reason(name: str, issuer_type: str) -> str | None:
    """Avoid treating issuer-specific metrics as missing protections."""
    if issuer_type not in {"manufacturing", "corporate", "general"}:
        return None
    lowered = name.lower()
    if any(term in lowered for term in ("crar", "gross npa", "net npa", "nbfc registration")):
        return f"{name} is issuer-specific and is not applicable to a {issuer_type} issuer."
    return None


def make_not_applicable(covenant: Dict[str, Any], reason: str) -> Dict[str, Any]:
    strength, protection, risk = classify_strength(covenant["name"])
    return {
        "covenant_id": covenant.get("id"),
        "canonical_group": covenant.get("canonical_group", covenant.get("id")),
        "source_covenant_ids": covenant.get("member_ids", [covenant.get("id")]),
        "source_covenant_names": covenant.get("member_names", [covenant["name"]]),
        "covenant_name": covenant["name"],
        "covenant_type": covenant.get("covenant_type"),
        "presence": "not_applicable",
        "present": False,
        "favorable": True,
        "confidence": 100.0,
        "investor_impact": strength,
        "priority_tier": strength,
        "priority_rank": priority_rank(strength),
        "protection_mechanism": protection,
        "risk_if_absent": risk,
        "rationale": reason,
        "limit": None, "frequency": None, "exceptions": None,
        "evidence_section": None, "evidence_quote": None,
        "retrieved_sections": [], "retrieved_evidence": [],
        "retrieval_distances": [], "max_lexical_match": 0.0,
        "llm_status": "not_applicable", "status": "success",
    }


def extract_consequence_analysis(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministically locate remedy and waiver language for a later JEV adapter."""
    searches = {
        "event_of_default": "event of default",
        "default_interest": "default interest additional interest penal interest",
        "cure_period": "cure period remedy period days rectify",
        "acceleration": "accelerate early redemption repayment immediately due",
        "trustee_remedy": "debenture trustee enforce remedy take action",
        "waiver_and_consent": "waiver majority consent trustee deemed consent silence",
    }
    output: Dict[str, Any] = {}
    for category, query in searches.items():
        candidates = []
        for chunk in chunks:
            score = lexical_match_score(query, chunk["text"])
            quotes = exact_evidence(query, chunk["text"], max_items=2)
            if score and quotes:
                candidates.append({
                    "section": chunk["source_section"],
                    "title": chunk["source_title"],
                    "match_score": round(score, 4),
                    "quotes": quotes,
                })
        candidates.sort(key=lambda item: item["match_score"], reverse=True)
        output[category] = candidates[:3]
    return output


CONSEQUENCE_HYPOTHESES = {
    "event_of_default": "A breach of this covenant can constitute an event of default.",
    "default_interest": "A breach of this covenant can trigger additional or default interest.",
    "cure_period": "The issuer receives a defined period to cure or rectify a breach of this covenant.",
    "acceleration": "A breach of this covenant can permit acceleration, early repayment, or redemption.",
    "trustee_remedy": "The debenture trustee has an enforcement or remedy right for a breach of this covenant.",
    "waiver_and_consent": "Waiver or amendment of this covenant requires investor, lender, or trustee consent.",
}


def classify_consequences_with_jev(
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Use local OpenJev to rank consequences supported by each present covenant."""
    try:
        from openjev_consequence import consequence_entailment, load_openjev

        model = load_openjev()
        covenant_results = []
        for item in results:
            if item["presence"] not in {"present", "partial"} or not item.get("evidence_quote"):
                continue
            scores = consequence_entailment(
                item["evidence_quote"],
                CONSEQUENCE_HYPOTHESES,
            )
            ranked = sorted(
                scores["scores"].items(),
                key=lambda pair: pair[1],
                reverse=True,
            )
            covenant_results.append({
                "covenant_id": item["covenant_id"],
                "covenant_name": item["covenant_name"],
                "evidence_section": item["evidence_section"],
                "evidence_quote": item["evidence_quote"],
                "ranked_consequences": [
                    {"category": category, "entailment_score": score}
                    for category, score in ranked
                ],
            })
        return {
            "provider": "openjev_local",
            "status": "success",
            "model": model,
            "covenants_analyzed": len(covenant_results),
            "results": covenant_results,
        }
    except Exception as exc:
        logger.exception("OpenJev consequence classification failed")
        model_info = getattr(exc, "label2id", None)
        logger.error("OpenJev error: %s; label mapping: %s", exc, model_info or {})
        return {
            "provider": "openjev_local",
            "status": "error",
            "results": [],
            "message": str(exc),
            "label_mapping": model_info,
        }


def classify_presence_with_jev(
    covenant_name: str,
    retrieved: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Classify covenant existence before any generative explanation."""
    from openjev_consequence import load_openjev, nli_entailment_scores

    evidence_items = [
        item for item in retrieved
        if item.get("evidence") and item.get("text")
    ]
    if not evidence_items:
        return {
            "presence": "unclear",
            "confidence": 0.0,
            "reason": "No exact evidence span was extracted.",
            "model": load_openjev(),
            "section_scores": [],
        }
    hypothesis = (
        f'The bond document explicitly contains this covenant: "{covenant_name}"'
    )
    scored = nli_entailment_scores(
        [item["text"] for item in evidence_items],
        hypothesis,
    )
    section_scores = []
    for item, scores in zip(evidence_items, scored["scores"]):
        scores = dict(scores)
        scores.update({
            "section": item["section"],
            "quote": item["evidence"][0],
        })
        section_scores.append(scores)
    best = max(section_scores, key=lambda item: item["entailment"])
    margin = best["entailment"] - max(
        best["contradiction"], best["neutral"]
    )
    contradiction_margin = best["contradiction"] - best["entailment"]
    if (
        best["entailment"] >= OPENJEV_PRESENCE_THRESHOLD
        and margin >= OPENJEV_PRESENCE_MARGIN
    ):
        presence = "present"
    elif (
        max(item["lexical_match"] for item in retrieved) >= MIN_LEXICAL_MATCH
        and contradiction_margin >= OPENJEV_PRESENCE_MARGIN
    ):
        presence = "absent"
    else:
        presence = "unclear"
    return {
        "presence": presence,
        "confidence": round(max(0.0, min(1.0, margin)) * 100, 1),
        "entailment_score": best["entailment"],
        "contradiction_score": best["contradiction"],
        "neutral_score": best["neutral"],
        "confidence_margin": round(margin, 6),
        "contradiction_margin": round(contradiction_margin, 6),
        "reason": "Highest OpenJev entailment score across grounded sections.",
        "model": scored["model"],
        "section_scores": section_scores,
    }


def analyze_covenant(
    covenant: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
    jev_presence: Dict[str, Any],
) -> Dict[str, Any]:
    name = covenant.get("name", covenant.get("description", ""))
    context = "\n\n".join(
        f"[{item['section']}] {item['title']}\n"
        f"EXACT MATCHING SPANS: {item['evidence']}\n{item['text']}"
        for item in retrieved
    )
    prompt = f"""You are reviewing a bond contract for an investor.
Do not assess current issuer compliance or financial performance.
OpenJev has already decided whether the covenant is supported by the retrieved text.
Do not change its presence decision. Extract details and write investor explanations
only from the supplied source sections. Use "partial" only if the covenant is
supported but its limit, frequency, or exceptions materially weaken it.

COVENANT:
{name}

RETRIEVED BOND SECTIONS:
{context[:9000]}

OpenJev decision: {jev_presence['presence']}
OpenJev confidence: {jev_presence['confidence']}

Return only JSON with exactly these keys:
{{"presence":"present|partial|absent|unclear","rationale":"one or two sentences",
"investor_protection":"one sentence","investor_risk":"one sentence",
"limit":"exact threshold or null","frequency":"testing frequency or null",
"exceptions":"material exceptions or null","evidence_section":"section id or null",
"evidence_quote":"exact supplied text span or null"}}
"""
    strength, protection, risk = classify_strength(name)
    try:
        llm = ollama_analyze(prompt)
        presence = jev_presence["presence"]
        confidence = float(jev_presence["confidence"])
        if presence == "present" and str(llm.get("presence", "")).lower() == "partial":
            presence = "partial"
        rationale = str(llm.get("rationale", "LLM returned no rationale."))
        investor_protection = str(llm.get("investor_protection", protection))
        investor_risk = str(llm.get("investor_risk", risk))
        limit = llm.get("limit")
        frequency = llm.get("frequency")
        exceptions = llm.get("exceptions")
        evidence_section = llm.get("evidence_section")
        evidence_quote = llm.get("evidence_quote")
        llm_status = "success"
    except Exception as exc:
        logger.warning("LLM fallback for %s: %s", covenant.get("id"), exc)
        presence, confidence = jev_presence["presence"], float(jev_presence["confidence"])
        rationale = "LLM analysis was unavailable; manual review is required."
        investor_protection, investor_risk = protection, risk
        limit = frequency = exceptions = evidence_section = evidence_quote = None
        llm_status = "fallback"

    if max((item["lexical_match"] for item in retrieved), default=0.0) < MIN_LEXICAL_MATCH:
        presence = "unclear"
        rationale = "Retrieved sections lack a direct vocabulary match; manual review is required."
    best_evidence = next(
        (item for item in retrieved if item.get("evidence")),
        retrieved[0] if retrieved else {},
    )
    if not evidence_section or evidence_section not in [item["section"] for item in retrieved]:
        evidence_section = best_evidence.get("section")
    supplied_quotes = [
        quote
        for item in retrieved
        for quote in item.get("evidence", [])
    ]
    if not evidence_quote or not any(
        str(evidence_quote).strip() in quote for quote in supplied_quotes
    ):
        evidence_quote = (best_evidence.get("evidence") or [None])[0]

    return {
        "covenant_id": covenant.get("id"),
        "canonical_group": covenant.get("canonical_group", covenant.get("id")),
        "source_covenant_ids": covenant.get("member_ids", [covenant.get("id")]),
        "source_covenant_names": covenant.get("member_names", [name]),
        "covenant_name": name,
        "covenant_type": covenant.get("covenant_type"),
        "presence": presence,
        "present": presence == "present",
        "favorable": presence in {"present", "partial"},
        "confidence": round(confidence, 1),
        "openjev_presence": jev_presence,
        "investor_impact": strength,
        "priority_tier": strength,
        "priority_rank": priority_rank(strength),
        "strength": strength,
        "protection_mechanism": investor_protection,
        "risk_if_absent": investor_risk,
        "rationale": rationale,
        "limit": limit,
        "frequency": frequency,
        "exceptions": exceptions,
        "evidence_section": evidence_section,
        "evidence_quote": evidence_quote,
        "evidence_page": best_evidence.get("page"),
        "evidence_line_start": best_evidence.get("line_start"),
        "evidence_line_end": best_evidence.get("line_end"),
        "retrieved_sections": [item["section"] for item in retrieved],
        "retrieved_evidence": [
            {"section": item["section"], "quotes": item["evidence"]}
            for item in retrieved
        ],
        "max_lexical_match": max(
            (item["lexical_match"] for item in retrieved), default=0.0
        ),
        "retrieval_distances": [round(item["distance"], 5) for item in retrieved],
        "llm_status": llm_status,
        "status": "success",
    }


def report(
    results: List[Dict[str, Any]],
    output_file: Path,
    consequence_analysis: Dict[str, Any] | None = None,
    jev_analysis: Dict[str, Any] | None = None,
) -> None:
    applicable = [item for item in results if item["presence"] != "not_applicable"]
    denominator = len(applicable) or 1
    present = [item for item in applicable if item["presence"] in {"present", "partial"}]
    absent = [item for item in applicable if item["presence"] == "absent"]
    unclear = [item for item in applicable if item["presence"] == "unclear"]
    critical = [item for item in applicable if item["strength"] == "CRITICAL"]
    critical_gaps = [item for item in critical if item["presence"] not in {"present", "partial"}]
    favorable = [item for item in present if item["favorable"]]
    score = len(favorable) / len(present) * 100 if present else 0
    results = sorted(results, key=lambda item: (item["priority_rank"], item["covenant_name"]))
    lines = [
        "# INVESTOR BOND COVENANT RISK REPORT\n\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**RAG embedding model:** Ollama `{EMBED_MODEL}`  \n",
        f"**Analysis model:** Ollama `{ANALYSIS_MODEL}`  \n",
        f"**Issuer profile:** `{ISSUER_TYPE}` (issuer-specific non-applicable items are excluded from coverage)\n",
        "**Scope:** Contractual covenant presence and investor protection; not operational compliance.  \n\n",
        "## Executive conclusion\n\n",
        f"**Investor protection score among present covenants:** {score:.1f}%\n\n",
        f"The review analyzed {len(results)} canonical covenant requirements against the most relevant "
        f"{TOP_K} numbered bond sections for each requirement. {len(present)} were classified "
        f"present, {len(absent)} absent, and {len(unclear)} unclear. "
        f"An unclear result should be treated as requiring legal review rather than as protection.\n\n",
        "## Covenant coverage\n\n",
        "| Status | Count | Percentage |\n|---|---:|---:|\n",
        f"| Present/partial | {len(present)} | {len(present)/denominator*100:.1f}% |\n",
        f"| Partial | {sum(item['presence'] == 'partial' for item in applicable)} | {sum(item['presence'] == 'partial' for item in applicable)/denominator*100:.1f}% |\n",
        f"| Absent | {len(absent)} | {len(absent)/denominator*100:.1f}% |\n",
        f"| Unclear | {len(unclear)} | {len(unclear)/denominator*100:.1f}% |\n",
        f"| Not applicable | {sum(item['presence'] == 'not_applicable' for item in results)} | excluded |\n\n",
        "## Critical missing or unclear protections\n\n",
    ]
    if critical_gaps:
        for item in critical_gaps:
            lines.append(
                f"- **{item['covenant_name']}** — {item['risk_if_absent']} "
                f"(retrieved sections: {', '.join(item['retrieved_sections'])})\n"
            )
    else:
        lines.append("- No critical covenant gaps were identified by the RAG + LLM review.\n")

    lines.extend([
        "\n## Present protective covenants\n\n",
        "| Covenant | Strength | Protection | Exact document line | Contract section |\n|---|---|---|---|---|\n",
    ])
    for item in sorted(present, key=lambda value: (value["priority_rank"], value["covenant_name"]))[:20]:
        lines.append(
            f"| {item['covenant_name'].replace('|', '/')} | {item['strength']} | "
            f"{item['protection_mechanism'].replace('|', '/')} | "
            f"{str(item.get('evidence_quote') or 'No exact match extracted').replace('|', '/')} | "
            f"{item.get('evidence_section') or ', '.join(item['retrieved_sections'])}"
            f" (p. {item.get('evidence_page') or '?'}, lines "
            f"{item.get('evidence_line_start') or '?'}-{item.get('evidence_line_end') or '?'}) |\n"
        )
    lines.extend([
        "\n## Part 2 — Breach consequences and waiver mechanics\n\n",
        "These source spans are extracted separately from covenant existence. They identify "
        "default remedies, cure periods, acceleration, trustee powers, and waiver mechanics "
        "for review by the consequence engine (JEV).\n\n",
        f"Jev classification status: **{(jev_analysis or {}).get('status', 'not run')}**\n\n",
    ])
    openjev_results = (jev_analysis or {}).get("results", [])
    if openjev_results:
        lines.extend([
            "### OpenJev-ranked consequence support\n\n",
            "Scores are entailment rankings, not calibrated probabilities. Higher scores "
            "indicate that the exact covenant evidence more strongly supports the consequence hypothesis.\n\n",
            "| Covenant | Evidence section | Highest-ranked consequence | Score |\n|---|---|---|---:|\n",
        ])
        for item in openjev_results[:20]:
            top = item["ranked_consequences"][0]
            lines.append(
                f"| {item['covenant_name'].replace('|', '/')} | {item['evidence_section']} | "
                f"{top['category'].replace('_', ' ')} | {top['entailment_score']:.4f} |\n"
            )
        lines.append("\n")
    for category, items in (consequence_analysis or {}).items():
        lines.append(f"### {category.replace('_', ' ').title()}\n\n")
        if not items:
            lines.append("No directly matching source span was found.\n\n")
            continue
        for item in items:
            lines.append(
                f"- **{item['section']}** — {item['quotes'][0].replace('|', '/')}\n"
            )
        lines.append("\n")
    lines.extend([
        "\n## Investor risk interpretation\n\n",
        "- **Financial risk:** Missing capital, profitability, asset-quality, or debt-service protections can weaken the issuer's repayment buffer.\n",
        "- **Leverage risk:** Missing additional-indebtedness restrictions can increase leverage and dilute creditor protection.\n",
        "- **Cash leakage risk:** Missing dividend restrictions can reduce cash retained for debt service.\n",
        "- **Information risk:** Missing or unclear audited-reporting covenants can delay early warning of deterioration.\n",
        "- **Legal review risk:** Semantic retrieval and LLM analysis accelerate review but do not replace counsel's reading of the executed documents.\n\n",
        "## Method and limitations\n\n",
        f"Each covenant was embedded and matched against the top {TOP_K} ChromaDB results built from numbered bond sections. "
        "OpenJev first classified contractual existence from grounded retrieved sections. "
        "Ollama then received the OpenJev decision and extracted limits, frequency, exceptions, and investor explanations; "
        "it was not allowed to override the OpenJev existence decision. "
        "Each result includes a short exact source span and section identifier so an investor can verify "
        "the classification quickly. Ollama failures are marked as fallbacks in the JSON output; "
        "the OpenJev existence decision remains authoritative.\n",
    ])
    output_file.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    covenants, chunks = load_inputs()
    consequence_analysis = extract_consequence_analysis(chunks)
    collection = build_index(chunks)
    results: List[Dict[str, Any]] = []
    pending_analysis: List[tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]] = []
    for index, covenant in enumerate(covenants, start=1):
        logger.info("Retrieving and analyzing covenant %d/%d: %s", index, len(covenants), covenant["id"])
        applicability = not_applicable_reason(covenant["name"], ISSUER_TYPE)
        if applicability:
            results.append(make_not_applicable(covenant, applicability))
            continue
        query = covenant.get("name", covenant.get("description", ""))
        query_embedding = ollama_embed(query)
        retrieved_data = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(RETRIEVAL_CANDIDATES, len(chunks)),
            include=["documents", "metadatas", "distances"],
        )
        retrieved = [
            {
                "text": retrieved_data["documents"][0][i],
                "section": retrieved_data["metadatas"][0][i]["source_section"],
                "title": retrieved_data["metadatas"][0][i]["source_title"],
                "page": retrieved_data["metadatas"][0][i].get("page"),
                "line_start": retrieved_data["metadatas"][0][i].get("source_line_start"),
                "line_end": retrieved_data["metadatas"][0][i].get("source_line_end"),
                "distance": retrieved_data["distances"][0][i],
            }
            for i in range(len(retrieved_data["documents"][0]))
        ]
        retrieved = rerank_retrieved(query, retrieved)
        try:
            jev_presence = classify_presence_with_jev(query, retrieved)
        except Exception as exc:
            logger.exception("OpenJev presence classification failed for %s", covenant["id"])
            jev_presence = {
                "presence": "unclear",
                "confidence": 0.0,
                "reason": f"OpenJev failed: {exc}",
                "section_scores": [],
            }
        pending_analysis.append((covenant, retrieved, jev_presence))

    # OpenJev and Ollama may both reserve GPU memory. Finish existence scoring
    # before handing the device to Ollama for detail extraction.
    from openjev_consequence import unload_openjev

    unload_openjev()
    for covenant, retrieved, jev_presence in pending_analysis:
        results.append(analyze_covenant(covenant, retrieved, jev_presence))

    present = sum(item["presence"] == "present" for item in results)
    partial = sum(item["presence"] == "partial" for item in results)
    absent = sum(item["presence"] == "absent" for item in results)
    unclear = sum(item["presence"] == "unclear" for item in results)
    payload = {
        "metadata": {
            "analysis_date": datetime.now().isoformat(),
            "methodology": "RAG + OpenJev covenant existence classification + Ollama detail extraction",
            "embedding_model": EMBED_MODEL,
            "analysis_model": ANALYSIS_MODEL,
            "retrieval_k": TOP_K,
            "total_covenants": len(results),
            "present": present,
            "partial": partial,
            "absent": absent,
            "unclear": unclear,
            "not_applicable": sum(item["presence"] == "not_applicable" for item in results),
            "issuer_type": ISSUER_TYPE,
            "llm_fallbacks": sum(item["llm_status"] == "fallback" for item in results),
            "openjev_presence_status": sum(
                item.get("openjev_presence", {}).get("presence") == "present"
                for item in results
            ),
            "openjev_presence_model": next(
                (
                    item.get("openjev_presence", {}).get("model")
                    for item in results
                    if item.get("openjev_presence", {}).get("model")
                ),
                None,
            ),
        },
        "results": results,
    }
    output_dir = ROOT / "phase3_output"
    output_dir.mkdir(exist_ok=True)
    payload["consequence_analysis"] = consequence_analysis
    jev_analysis = classify_consequences_with_jev(results)
    payload["openjev_consequence_analysis"] = jev_analysis
    (output_dir / "covenant_analysis_rag_llm.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report(
        results,
        output_dir / "covenant_analysis_investor_rag_report.md",
        consequence_analysis,
        jev_analysis,
    )
    logger.info("RAG + LLM analysis complete: %d present, %d absent, %d unclear", present, absent, unclear)


if __name__ == "__main__":
    main()
