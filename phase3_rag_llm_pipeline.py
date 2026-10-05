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
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import chromadb
import requests

ROOT = Path(__file__).resolve().parent
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text:latest"
ANALYSIS_MODEL = "qwen3.5:0.8b"
TOP_K = 3

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
            "options": {"temperature": 0.0, "num_predict": 256},
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
    if not covenants or not chunks:
        raise ValueError("Covenants or section-aware bond chunks are empty")
    return covenants, chunks


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


def classify_strength(name: str) -> tuple[str, str, str]:
    lowered = name.lower()
    critical = {
        "crar": "Capital adequacy is a core solvency buffer.",
        "npa": "Asset-quality limits protect the issuer's repayment capacity.",
        "dscr": "Debt-service capacity protects timely interest and principal payment.",
        "capital": "Capital maintenance absorbs losses before creditors are affected.",
        "security": "Collateral and security support repayment priority.",
        "reserve": "Reserves provide loss-absorption capacity.",
        "profit": "Profitability supports sustainable debt service.",
    }
    strong = {
        "audit": "Audited reporting improves independently verifiable monitoring.",
        "financial": "Financial reporting gives investors early-warning visibility.",
        "report": "Reporting supports ongoing investor monitoring.",
        "dividend": "Dividend restrictions preserve cash for creditors.",
        "borrowing": "Debt restrictions control leverage and creditor dilution.",
        "indebtedness": "Debt restrictions control leverage and creditor dilution.",
        "compliance": "Regulatory compliance reduces legal and operational disruption.",
    }
    for term, explanation in critical.items():
        if term in lowered:
            return "CRITICAL", explanation, f"Missing this safeguard increases investor risk: {explanation}"
    for term, explanation in strong.items():
        if term in lowered:
            return "STRONG", explanation, f"Without this safeguard, investor monitoring or cash preservation is weaker: {explanation}"
    return "MODERATE", "Standard contractual protection.", "The absence reduces a standard layer of protection."


def analyze_covenant(covenant: Dict[str, Any], retrieved: List[Dict[str, Any]]) -> Dict[str, Any]:
    name = covenant.get("name", covenant.get("description", ""))
    context = "\n\n".join(
        f"[{item['section']}] {item['title']}\n{item['text']}" for item in retrieved
    )
    prompt = f"""You are reviewing a bond contract for an investor.
Do not assess current issuer compliance or financial performance.
Decide only whether this contractual covenant is explicitly present in the retrieved bond text.
Use "unclear" when the text is only a weak or indirect match.

COVENANT:
{name}

RETRIEVED BOND SECTIONS:
{context[:9000]}

Return only JSON with exactly these keys:
{{"presence":"present|absent|unclear","confidence":0,"rationale":"one or two sentences",
"investor_protection":"one sentence","investor_risk":"one sentence"}}
"""
    strength, protection, risk = classify_strength(name)
    try:
        llm = ollama_analyze(prompt)
        presence = str(llm.get("presence", "unclear")).lower()
        if presence not in {"present", "absent", "unclear"}:
            presence = "unclear"
        confidence = float(llm.get("confidence", 50))
        if 0.0 <= confidence <= 1.0:
            confidence *= 100.0
        confidence = max(0.0, min(95.0, confidence))
        rationale = str(llm.get("rationale", "LLM returned no rationale."))
        investor_protection = str(llm.get("investor_protection", protection))
        investor_risk = str(llm.get("investor_risk", risk))
        llm_status = "success"
    except Exception as exc:
        logger.warning("LLM fallback for %s: %s", covenant.get("id"), exc)
        presence, confidence = "unclear", 0.0
        rationale = "LLM analysis was unavailable; manual review is required."
        investor_protection, investor_risk = protection, risk
        llm_status = "fallback"

    return {
        "covenant_id": covenant.get("id"),
        "covenant_name": name,
        "covenant_type": covenant.get("covenant_type"),
        "presence": presence,
        "present": presence == "present",
        "favorable": presence == "present",
        "confidence": round(confidence, 1),
        "investor_impact": "CRITICAL" if strength == "CRITICAL" else "HIGH" if strength == "STRONG" else "MEDIUM",
        "strength": strength,
        "protection_mechanism": investor_protection,
        "risk_if_absent": investor_risk,
        "rationale": rationale,
        "retrieved_sections": [item["section"] for item in retrieved],
        "retrieval_distances": [round(item["distance"], 5) for item in retrieved],
        "llm_status": llm_status,
        "status": "success",
    }


def report(results: List[Dict[str, Any]], output_file: Path) -> None:
    present = [item for item in results if item["presence"] == "present"]
    absent = [item for item in results if item["presence"] == "absent"]
    unclear = [item for item in results if item["presence"] == "unclear"]
    critical = [item for item in results if item["strength"] == "CRITICAL"]
    critical_gaps = [item for item in critical if item["presence"] != "present"]
    favorable = [item for item in present if item["favorable"]]
    score = len(favorable) / len(present) * 100 if present else 0
    lines = [
        "# INVESTOR BOND COVENANT RISK REPORT\n\n",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n",
        f"**RAG embedding model:** Ollama `{EMBED_MODEL}`  \n",
        f"**Analysis model:** Ollama `{ANALYSIS_MODEL}`  \n",
        "**Scope:** Contractual covenant presence and investor protection; not operational compliance.  \n\n",
        "## Executive conclusion\n\n",
        f"**Investor protection score among present covenants:** {score:.1f}%\n\n",
        f"The review analyzed {len(results)} covenant requirements against the most relevant "
        f"{TOP_K} numbered bond sections for each requirement. {len(present)} were classified "
        f"present, {len(absent)} absent, and {len(unclear)} unclear. "
        f"An unclear result should be treated as requiring legal review rather than as protection.\n\n",
        "## Covenant coverage\n\n",
        "| Status | Count | Percentage |\n|---|---:|---:|\n",
        f"| Present | {len(present)} | {len(present)/len(results)*100:.1f}% |\n",
        f"| Absent | {len(absent)} | {len(absent)/len(results)*100:.1f}% |\n",
        f"| Unclear | {len(unclear)} | {len(unclear)/len(results)*100:.1f}% |\n\n",
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
        "| Covenant | Strength | Protection | Contract sections |\n|---|---|---|---|\n",
    ])
    for item in sorted(present, key=lambda value: {"CRITICAL": 0, "STRONG": 1, "MODERATE": 2}[value["strength"]])[:20]:
        lines.append(
            f"| {item['covenant_name'].replace('|', '/')} | {item['strength']} | "
            f"{item['protection_mechanism'].replace('|', '/')} | {', '.join(item['retrieved_sections'])} |\n"
        )
    lines.extend([
        "\n## Investor risk interpretation\n\n",
        "- **Financial risk:** Missing capital, profitability, asset-quality, or debt-service protections can weaken the issuer's repayment buffer.\n",
        "- **Leverage risk:** Missing additional-indebtedness restrictions can increase leverage and dilute creditor protection.\n",
        "- **Cash leakage risk:** Missing dividend restrictions can reduce cash retained for debt service.\n",
        "- **Information risk:** Missing or unclear audited-reporting covenants can delay early warning of deterioration.\n",
        "- **Legal review risk:** Semantic retrieval and LLM analysis accelerate review but do not replace counsel's reading of the executed documents.\n\n",
        "## Method and limitations\n\n",
        f"Each covenant was embedded and matched against the top {TOP_K} ChromaDB results built from numbered bond sections. "
        "The LLM received only those retrieved sections and was instructed to classify contractual presence, not compliance. "
        "The report intentionally omits raw evidence excerpts to keep the investor view concise; section references remain "
        "for targeted follow-up. LLM failures are marked as fallbacks in the JSON output and are treated as unclear.\n",
    ])
    output_file.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    covenants, chunks = load_inputs()
    collection = build_index(chunks)
    results: List[Dict[str, Any]] = []
    for index, covenant in enumerate(covenants, start=1):
        logger.info("Retrieving and analyzing covenant %d/%d: %s", index, len(covenants), covenant["id"])
        query = covenant.get("name", covenant.get("description", ""))
        query_embedding = ollama_embed(query)
        retrieved_data = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(TOP_K, len(chunks)),
            include=["documents", "metadatas", "distances"],
        )
        retrieved = [
            {
                "text": retrieved_data["documents"][0][i],
                "section": retrieved_data["metadatas"][0][i]["source_section"],
                "title": retrieved_data["metadatas"][0][i]["source_title"],
                "distance": retrieved_data["distances"][0][i],
            }
            for i in range(len(retrieved_data["documents"][0]))
        ]
        results.append(analyze_covenant(covenant, retrieved))

    present = sum(item["presence"] == "present" for item in results)
    absent = sum(item["presence"] == "absent" for item in results)
    unclear = sum(item["presence"] == "unclear" for item in results)
    payload = {
        "metadata": {
            "analysis_date": datetime.now().isoformat(),
            "methodology": "RAG + Ollama LLM contractual covenant presence analysis",
            "embedding_model": EMBED_MODEL,
            "analysis_model": ANALYSIS_MODEL,
            "retrieval_k": TOP_K,
            "total_covenants": len(results),
            "present": present,
            "absent": absent,
            "unclear": unclear,
            "llm_fallbacks": sum(item["llm_status"] == "fallback" for item in results),
        },
        "results": results,
    }
    output_dir = ROOT / "phase3_output"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "covenant_analysis_rag_llm.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report(results, output_dir / "covenant_analysis_investor_rag_report.md")
    logger.info("RAG + LLM analysis complete: %d present, %d absent, %d unclear", present, absent, unclear)


if __name__ == "__main__":
    main()
