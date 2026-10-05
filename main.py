#!/usr/bin/env python
"""Run the complete bond covenant analysis pipeline.

The pipeline runs:
1. Phase 1: parse the covenant master list and clean the bond PDF.
2. Phase 2: create numbered-section-aware bond chunks.
3. Phase 3: embed, retrieve, and analyze covenants with Ollama + ChromaDB.

Start Ollama before running this script. The configured local endpoint is
http://127.0.0.1:11434.
"""

import logging
import os
from pathlib import Path

from src.phase1.phase1_pipeline import Phase1Pipeline
from phase2_section_aware_chunking import main as run_phase2
from phase3_rag_llm_pipeline import main as run_phase3


ROOT = Path(__file__).resolve().parent


def run_pipeline() -> None:
    os.chdir(ROOT)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    print("=" * 72)
    print("BOND COVENANT ANALYSIS PIPELINE")
    print("=" * 72)

    print("\n[1/3] Preparing source data and cleaning the bond document...")
    Phase1Pipeline(
        master_list_path=str(ROOT / "data" / "master_list.txt"),
        bond_pdf_path=str(ROOT / "data" / "bond_memorandum.pdf"),
        output_dir=str(ROOT / "phase1_output"),
    ).run()

    print("\n[2/3] Creating section-aware bond chunks...")
    run_phase2()

    print("\n[3/3] Running ChromaDB retrieval and Ollama covenant analysis...")
    run_phase3()

    print("\n" + "=" * 72)
    print("PIPELINE COMPLETE")
    print("=" * 72)
    print("Investor report:")
    print(ROOT / "phase3_output" / "covenant_analysis_investor_rag_report.md")
    print("Analysis JSON:")
    print(ROOT / "phase3_output" / "covenant_analysis_rag_llm.json")


if __name__ == "__main__":
    run_pipeline()
