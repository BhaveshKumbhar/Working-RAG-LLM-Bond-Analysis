# Bond Covenant Analysis RAG+LLM Pipeline - Complete Project Handoff

**Project:** EDI Industry Project - Keertana Finserv Bond Covenant Analysis  
**Student:** Bhavesh (Semester 5, CS Engineering)  
**Status:** Phase 3 - Ollama RAG + LLM analysis complete  
**Date:** October 3, 2026

---

## 📋 PROJECT OVERVIEW

### **Objective**
Analyze **120 bond covenants** from a 261-page Keertana Finserv bond issuance document to:
1. Identify covenant **PRESENCE** (mentioned in document or not)
2. Assess **INVESTOR PROTECTION** value of each covenant
3. Identify **CRITICAL GAPS** (missing protective covenants)
4. Generate professional **INVESTMENT-GRADE REPORTS**

### **NOT Required:**
- ❌ Compliance checking (not operational compliance)
- ❌ Generic favorability scoring
- ❌ Regulatory approval assessment

### **REQUIRED:**
- ✅ **Legal contract analysis** (what terms are in the bond?)
- ✅ **Investor protection focus** (how does this protect investors?)
- ✅ **Gap identification** (what critical protections are missing?)
- ✅ **Retrieval traceability** (numbered section references; raw excerpts are kept out of the investor report)

---

## 🔄 COMPLETE PROJECT TIMELINE

### **PHASE 1: Data Preparation ✅ COMPLETE**
**Deliverables:**
- `phase1_output/master_key.json` - 120 covenants structured as:
  ```
  {
    "by_type": {
      "positive": [65 covenants - Issuer obligations],
      "negative": [55 covenants - Issuer restrictions]
    }
  }
  ```
- `phase1_output/bond_cleaned.txt` - Cleaned 261-page bond document
- `master_key.json` contains actual covenant definitions with IDs (COV_P_A_1, etc.)

**Files Created:**
- Data extraction scripts
- Covenant list validation
- Document cleaning pipeline

---

### **PHASE 2: Document Chunking ✅ COMPLETE**
**Problem Identified:** Random 300-word chunks were inconsistent (11 chunks, 74-6906 words)

**Solution Implemented:** Section-aware Chunking Strategy
- Algorithm: numbered subsection boundaries with paragraph/list splitting
- Current result: **69 bounded retrieval sections**, 22-450 words each
- Duplicate subsection labels receive unique occurrence IDs
- Oversized sections are split without overlap and without combining unrelated sections

**Deliverables:**
- `phase2_output/hybrid_chunks.json` - 46 chunks with:
  - `id`: chunk identifier
  - `text`: chunk content (400-600 words typical)
  - `source_section`: document section reference
  - Word count, embedding status, metadata
- `phase2_output/hybrid_chunking_stats.json` - Quality metrics

**Files Created:**
- `phase2_hybrid_chunking.py` - Chunking algorithm
- Statistics validation
- Embedding quality assessment

### **Section-aware chunking improvement**
The recommended Phase 2 entry point is now:

```powershell
.\.venv\Scripts\python.exe phase2_section_aware_chunking.py
```

It reads `phase1_output/bond_cleaned.txt`, detects numbered subsection boundaries
such as `2.1`, `2.2`, and `8.38`, preserves each subsection as an independent
retrieval unit, carries the parent section and nearest page number, and splits
only oversized sections at paragraph or numbered-list boundaries. It does not
combine unrelated sections and does not use fixed-size word overlap.

Outputs:

- `phase2_output/section_aware_chunks.json`
- `phase2_output/section_aware_chunking_stats.json`

Phase 3 automatically prefers `section_aware_chunks.json` and falls back to the
legacy `hybrid_chunks.json` only when the improved output has not been generated.

---

### **PHASE 3: Ollama RAG + Covenant Analysis ✅ COMPLETE**

The primary Phase 3 entry point is:

```powershell
.\.venv\Scripts\python.exe phase3_rag_llm_pipeline.py
```

The pipeline embeds the section-aware bond chunks with Ollama
`nomic-embed-text:latest`, persists them in ChromaDB, retrieves the top three
sections for each of the 120 covenant requirements, and asks the local
`qwen3.5:0.8b` model to classify contractual presence as `present`, `absent`,
or `unclear`. It does not assess current issuer compliance. If the LLM response
is unavailable or malformed, the covenant is marked `unclear` rather than
silently treated as protected.

Generated outputs:

- `phase2_output/chroma_rag_db/` - persistent ChromaDB bond-section index
- `phase3_output/covenant_analysis_rag_llm.json` - retrieval metadata and analysis
- `phase3_output/covenant_analysis_investor_rag_report.md` - concise investor report

The report omits raw evidence excerpts to reduce reading time, but retains the
retrieved contract section references for targeted legal follow-up.

#### **What We Achieved:**
Implemented a grounded bond covenant analyzer with:
1. **Semantic retrieval** - ChromaDB matches each covenant to its most relevant bond sections
2. **LLM contractual analysis** - Ollama evaluates only the retrieved text
3. **Investor protection classification** - Critical, strong, and moderate safeguards
4. **Critical gap analysis** - Missing and unclear protections are surfaced

#### **Current Results (from execution):**
```
COVENANT PRESENCE:
  ✅ Present: 107/120 (89.2%)
  ❓ Unclear: 13/120 (10.8%)
  ❌ Absent: 0/120 (0.0%)

INVESTOR FAVORABILITY (of 107 present):
  🟢 Favorable: 107 (100.0%)

COVENANT STRENGTH CLASSIFICATION:
  🔴 CRITICAL: 23 covenants (protect core investor rights)
  🟠 STRONG: 10 covenants (important safeguards)
  🟡 MODERATE: 74 covenants (standard protections)

INVESTOR PROTECTION SCORE: 100.0%
AVERAGE CONFIDENCE: 79.2%

CRITICAL GAPS IDENTIFIED: 5 covenants
  1. Maintain CRAR (capital adequacy)
  2. Maintain profitability
  3. No additional indebtedness without consent
  4. Restrict dividend declaration
  5. Submit audited financials
```

#### **Methodology:**
- Uses knowledge-based analysis (NOT machine learning classifiers)
- Searches 46 hybrid chunks for covenant presence
- Classifies by investor impact category
- Extracts evidence from document
- Identifies critical gaps
- Calculates protection score

#### **Why This Approach:**
- ✅ Distilbert (sequence classifier) failed (gave 0% score - wrong model)
- ✅ Ollama was slow (15+ minutes)
- ✅ Knowledge-based is fast (<1 second), accurate, explainable
- ✅ Directly implements professor's methodology

---

## 🎯 CURRENT STATUS & BLOCKERS

### **What's Complete:**
✅ Phase 1 - Data preparation (120 covenants extracted)  
✅ Phase 2 - Document chunking (46 optimal chunks)  
✅ Phase 3 - Covenant analysis engine (all 120 analyzed)  
✅ Analysis results generated (JSON output created)  

### **Report Generation:**
The professional report is generated from the deterministic analysis results. The original
report-generation blocker was a zero-argument logging call:
```python
# ERROR:
logger.info()  # ❌ Missing message argument

# FIX:
logger.info("")  # ✅ Empty message or use logger.info("---")
```

**Status:** Resolved. The report generator now includes presence analysis, strength breakdown,
critical gaps, protective covenant evidence, risk assessment, score explanation, and investor
recommendations. “Unclear” critical covenants are reported as gaps rather than being silently
omitted.

---

## 📂 PROJECT STRUCTURE & FILES

### **Input Files (Already Exist):**
```
C:\Bhavesh\Semester_5\EDI\RAG_Industry_Project\

phase1_output/
  ├── master_key.json          [120 covenants - by_type.positive & by_type.negative]
  └── bond_cleaned.txt         [261-page bond document]

phase2_output/
  ├── hybrid_chunks.json       [46 document chunks with metadata]
  └── hybrid_chunking_stats.json
```

### **Analysis Script (Working):**
```
phase3_corrected_real.py
  ├── BondCovenantAnalyzer class
  ├── analyze_covenant() method
  ├── search_covenant_in_chunks() - PRESENCE detection
  ├── assess_investor_favorability() - Protection classification
  ├── identify_critical_gaps() - Gap analysis
  └── _generate_report() - Report generation (HAS MINOR BUG)
```

### **Output Files (Generated):**
```
phase3_output/
  ├── covenant_analysis_corrected.json
  │   ├── metadata (protection score, recommendation, gaps)
  │   ├── statistics (presence counts, confidence, etc.)
  │   └── results (all 120 covenants analyzed)
  └── covenant_analysis_professional_report.md (generated)
```

---

## 👨‍🎓 PROFESSOR'S REQUIREMENTS

### **Analysis Methodology (MUST FOLLOW):**

#### **1. NOT Compliance Checking**
- ❌ Don't check "is issuer complying with this covenant?"
- ✅ Check "is this covenant PRESENT in the bond document?"
- Focus: Legal contract terms, not operational performance

#### **2. Identify Terms That Protect INVESTORS**
- ✅ Classify each covenant by investor protection value
- ✅ Categories: CRITICAL / STRONG / MODERATE
- ✅ Explain protection mechanism (how it helps investors)
- ✅ Calculate risk if covenant absent

**Example - CRITICAL covenant:**
```
Covenant: "Maintain CRAR above 9%"
Protection: Ensures issuer has capital buffer
Investor Impact: CRITICAL (protects against unexpected losses)
Risk if Absent: "Issuer can deplete capital; default risk increases"
```

**Example - STRONG covenant:**
```
Covenant: "Submit audited financials quarterly"
Protection: Transparency for investor monitoring
Investor Impact: HIGH (enables early warning signals)
Risk if Absent: "Blind spot for investor; risks materialize without notice"
```

**Example - MODERATE covenant:**
```
Covenant: "Comply with tax laws"
Protection: Standard legal compliance
Investor Impact: MEDIUM (indirect benefit)
Risk if Absent: "Regulatory penalties could impair operations"
```

#### **3. Shows GAPS in Investor Protection**
- ✅ Identify CRITICAL covenants that are ABSENT
- ✅ Explain what this means for investors
- ✅ List specific missing protections
- ✅ Quantify gap impact on protection score

**Current Gaps Found (5 critical):**
1. Maintain CRAR → No capital adequacy check
2. Maintain profitability → No earnings requirement
3. No additional debt without consent → Can over-leverage
4. Restrict dividend → Cash could leak to promoters
5. Submit audited financials → No transparency

#### **4. Legal Contract Analysis (Not Operational Compliance)**
- ✅ Analyze what's WRITTEN in the bond document
- ✅ Extract actual covenant language
- ✅ Show section references
- ✅ Provide evidence from document
- ❌ Don't check if issuer is actually complying
- ❌ Don't assess regulatory compliance
- ❌ Don't check operational performance

---

## 🔧 TECHNICAL APPROACH - KAGGLE LLM INFERENCE ONLY

### **LLM Usage Strategy:**
For the code editor to enhance reports, use **Kaggle LLM inference ONLY** for:
- ✅ Detailed explanation of investor impact
- ✅ Risk assessment narratives
- ✅ Gap analysis explanations
- ✅ Recommendation justification
- ✅ Professional report polishing

### **DO NOT Use LLM For:**
- ❌ Presence detection (use pattern matching on chunks)
- ❌ Covenant classification (use knowledge base)
- ❌ Gap identification (use defined critical list)
- ❌ Score calculation (use formula-based)

### **Kaggle LLM Inference Pattern:**
```python
# Example: Use LLM for explanation only
if covenant_is_critical and covenant_is_absent:
    # LLM inference: Generate detailed explanation
    llm_prompt = f"""
    Explain investor impact of missing this covenant:
    Covenant: {covenant_name}
    Type: CRITICAL (missing)
    Brief description: {covenant_description}
    
    Provide 2-3 sentences on investor risk impact.
    Focus on financial/operational consequences.
    """
    
    investor_impact = llm_service.generate_explanation(llm_prompt)
    report.add(investor_impact)
```

### **Model to Use:**
- Kaggle default: distilbert-based (unless project specifies otherwise)
- For enhanced text: Kaggle Llama 2 7B or Mistral 7B available
- GPU-optimized: RTX 3050 compatible (4GB VRAM)

---

## 📊 ANALYSIS DATA STRUCTURE

### **JSON Analysis Results Format:**
```json
{
  "metadata": {
    "analysis_date": "2026-10-03T16:58:20",
    "methodology": "Knowledge-based PRESENCE & FAVORABILITY",
    "total_covenants": 120,
    "present": 107,
    "absent": 0,
    "unclear": 13,
    "avg_confidence": 79.2,
    "protection_score": 100.0,
    "critical_gaps": 5,
    "recommendation": "🟢 STRONG INVESTOR PROTECTION - FAVORABLE BOND"
  },
  "statistics": {
    "present": 107,
    "absent": 0,
    "unclear": 13,
    "favorable": 107,
    "critical_count": 23,
    "strong_count": 10,
    "avg_confidence": 79.2,
    "protection_score": 100.0
  },
  "results": [
    {
      "covenant_id": "COV_P_A_1",
      "covenant_name": "Comply with all applicable laws, RBI regulations...",
      "covenant_type": "positive",
      "present": true,
      "favorable": true,
      "confidence": 85.5,
      "investor_impact": "CRITICAL",
      "protection_mechanism": "Ensures issuer operates within legal framework",
      "risk_if_absent": "Issuer can violate regulations; regulatory action could impair operations",
      "strength": "CRITICAL",
      "section_reference": "Section 2-4 (Operating covenants)",
      "evidence": "[Document excerpt showing covenant]",
      "status": "success"
    },
    ...120 total
  ]
}
```

### **Covenant Strength Classification:**
```python
CRITICAL = {
    "description": "Core investor protection (if absent = major risk)",
    "examples": [
        "Maintain CRAR/capital adequacy",
        "Limit Gross/Net NPA",
        "Maintain DSCR",
        "Create/maintain security",
        "Restrict additional debt",
        "Maintain profitability"
    ]
}

STRONG = {
    "description": "Important investor safeguards",
    "examples": [
        "Financial monitoring (quarterly reports)",
        "Audit requirements",
        "Compliance with standards",
        "Restrict dividend payments"
    ]
}

MODERATE = {
    "description": "Standard investor protections",
    "examples": [
        "Legal/regulatory compliance",
        "Standard operating covenants",
        "Governance requirements"
    ]
}
```

---

## 📄 REQUIRED REPORT STRUCTURE

### **Professional Report Should Include:**

#### **1. Executive Summary**
- Investment recommendation (🟢 STRONG / 🟡 MODERATE / 🔴 WEAK)
- Protection score (0-100%)
- Key findings (covenants present, gaps, confidence)
- Bottom line for investors

#### **2. Covenant Presence Analysis**
- Table: Present / Absent / Unclear breakdown
- Percentage distribution
- Quality metrics (success rate, confidence)

#### **3. Investor Favorability Assessment**
- Breakdown by strength: CRITICAL / STRONG / MODERATE
- Count and percentage for each
- Examples of each category

#### **4. Critical Covenant Gaps**
- List missing CRITICAL covenants (if any)
- For each gap:
  - What it is
  - Why it matters
  - Investor risk exposure
  - What should be there instead

#### **5. Top Protective Covenants** (if space)
- Most important covenants present
- Why they matter
- How they protect investors
- Section references

#### **6. Risk Assessment**
- Financial risk (no capital checks)
- Reporting risk (no transparency)
- Operational risk (can over-leverage)
- Investor exposure for each category

#### **7. Investor Protection Score Explanation**
- How calculated: (favorable_present / total_present) × 100
- Interpretation:
  - 80-100%: STRONG protection
  - 50-80%: MODERATE protection
  - <50%: WEAK protection
- Confidence level and what it means

#### **8. Investment Recommendation**
- For conservative investors: (score > 75%)
- For moderate investors: (50% < score < 75%)
- For aggressive investors: (score < 50%)
- Suggested next steps

---

## 🚀 IMMEDIATE NEXT STEPS FOR CODE EDITOR

### **Task 1: Fix Report Generation Bug** (completed)
```python
# In phase3_corrected_real.py, line ~385
# Change: logger.info()
# To: logger.info("")
```
Then re-run: `python phase3_corrected_real.py` (completed successfully)

### **Task 2: Enhance Report with LLM (optional)**
Use Kaggle LLM inference to:
1. Generate detailed investor impact explanations for each covenant
2. Create narrative descriptions of gaps
3. Polish professional language
4. Add investment thesis narrative

### **Task 3: Validate Output**
- [ ] `covenant_analysis_corrected.json` has all 120 covenants
- [ ] All results have: covenant_name, present, favorable, confidence, protection_mechanism
- [ ] Critical gaps list is populated (5+ expected)
- [ ] Protection score > 75% (current: 100.0%)
- [ ] Report markdown is generated and professional

### **Task 4: Final Deliverables**
Generate 3 files for professor:
1. `covenant_analysis_corrected.json` - Full analysis
2. `covenant_analysis_professional_report.md` - Summary report
3. `phase3_corrected_real.py` - Source code

---

## 📋 VALIDATION CHECKLIST

Before submitting to professor, verify:

### **Analysis Quality:**
- [ ] All 120 covenants analyzed (covenant_analysis_corrected.json)
- [ ] Presence field: true/false/null (not string)
- [ ] Confidence scores: 0-95% range
- [ ] Investor impact: CRITICAL/HIGH/MEDIUM (not generic)
- [ ] Section references: "Section X-Y" format
- [ ] Evidence: Non-empty quotes from document
- [ ] Status: All "success" (no errors)

### **Report Quality:**
- [ ] Executive summary present
- [ ] Investment recommendation clear (🟢/🟡/🔴)
- [ ] Presence breakdown table
- [ ] Top covenants listed with explanations
- [ ] Critical gaps explicitly listed (5 gaps: CRAR, profitability, debt, dividend, financials)
- [ ] Risk assessment section
- [ ] Professional formatting
- [ ] No generic explanations (each covenant explained specifically)

### **Methodology Compliance:**
- [ ] ✅ Presence-focused (not compliance)
- [ ] ✅ Investor protection focus
- [ ] ✅ Gap identification
- [ ] ✅ Legal contract analysis (not operational)
- [ ] ✅ Evidence extraction
- [ ] ✅ Professional assessment

---

## 📞 PROFESSOR'S FEEDBACK TRACKING

### **Feedback #1: Analysis Type (IMPLEMENTED ✅)**
> "Don't check compliance. Check covenant PRESENCE. Identify which terms protect INVESTORS."

**Implementation:**
- ✅ Searches for PRESENCE (is covenant in document?)
- ✅ Classifies by INVESTOR PROTECTION value (CRITICAL/STRONG/MODERATE)
- ✅ NOT checking compliance (not "is issuer complying?")
- ✅ NOT checking regulatory approval

### **Feedback #2: Gap Analysis (IMPLEMENTED ✅)**
> "Shows GAPS in investor protection (missing covenants)."

**Implementation:**
- ✅ Critical covenant list defined
- ✅ Identifies missing critical covenants
- ✅ Lists gaps with investor risk explanation
- ✅ Quantified in report (5 gaps identified)

### **Feedback #3: Legal Analysis (IMPLEMENTED ✅)**
> "Legal contract analysis, not operational compliance check."

**Implementation:**
- ✅ Analyzes what's WRITTEN in document
- ✅ Evidence extraction from sections
- ✅ NOT checking if issuer complies operationally
- ✅ NOT checking regulatory performance

### **Feedback #4: Report Quality (IMPLEMENTED ✅)**
> "Generate professional investor-grade reports with detailed explanations."

**Implementation:**
- ✅ Report structure defined
- ✅ Deterministic investor-impact explanations grounded in covenant metadata
- ✅ Professional formatting with required analysis sections
- ✅ Investor recommendation and risk narrative

---

## 🔐 CONSTRAINTS & BEST PRACTICES

### **Constraints:**
1. **Do NOT** use distilbert for analysis (it's wrong for bonds)
2. **Do NOT** use compliance checking logic
3. **Do NOT** use generic LLM inference for presence/gap detection
4. **Do NOT** submit Ollama-based results (too slow)
5. **Do NOT** over-rely on LLM for structured decisions

### **Best Practices:**
1. **Use knowledge-based approach** for presence/classification
2. **Use LLM ONLY** for explanation/narrative generation
3. **Kaggle LLM inference** for enhanced reports (not core logic)
4. **Evidence extraction** must be from actual document chunks
5. **Confidence scores** must be based on keyword matching strength
6. **Gap analysis** must reference defined critical covenant list
7. **Reports** must be investor-focused (not issuer-focused)

---

## 📚 REFERENCE DOCUMENTS

### **Files Provided:**
- `phase3_corrected_real.py` - Main analysis engine
- `PHASE3_CORRECTED_README.md` - Usage guide
- `00_START_HERE.txt` - Quick start
- This file - Comprehensive handoff

### **Available Inputs:**
- `phase1_output/master_key.json` - 120 covenants
- `phase2_output/hybrid_chunks.json` - 46 document chunks
- `phase1_output/bond_cleaned.txt` - Full bond document

### **Expected Outputs:**
- `phase3_output/covenant_analysis_corrected.json` - Analysis data
- `phase3_output/covenant_analysis_professional_report.md` - Report

---

## ✅ SUCCESS CRITERIA

### **For Code Editor:**
1. ✅ Fix `logger.info()` bug and run analysis
2. ✅ Verify all 120 covenants in output
3. ✅ Generate professional report
4. ✅ Use Kaggle LLM for explanation generation (optional enhancement)
5. ✅ Produce investor-grade output
6. ✅ Align with professor's 4 requirements

### **Expected Final Output:**
```
INVESTOR PROTECTION ASSESSMENT:
  Covenants Present: 107/120 (89.2%)
  Investor Favorable: 107/107 (100%)
  Protection Score: 100.0%
  
CRITICAL GAPS: 5
  - Missing: Maintain CRAR
  - Missing: Maintain profitability
  - Missing: No additional debt
  - Missing: Restrict dividend
  - Missing: Audited financials
  
RECOMMENDATION:
  🟢 STRONG INVESTOR PROTECTION
  Suitable for: Conservative to moderate risk investors
  Key Risk: Missing 5 critical covenants reduces flexibility
```

---

## 🎯 FINAL NOTES FOR CODE EDITOR

**This project is complete through grounded local RAG + LLM report generation.**
The deterministic analyzer remains available as a fallback/reference implementation,
but it is no longer the primary Phase 3 workflow:

1. Run the section-aware chunker
2. Run the Ollama RAG + LLM pipeline
3. Review the JSON retrieval metadata and investor report
4. Deliver the report with the source section references for legal follow-up

**Key Principle:** Retrieval grounds every covenant decision in numbered bond
sections. LLM failures are visible as `unclear` in the JSON output and are not
silently converted into positive protection.

The local Ollama model is used for contractual presence classification and
investor-facing explanations. ChromaDB retrieval and deterministic strength/
score logic remain separate so the report distinguishes semantic analysis from
investor risk interpretation.

**Estimated Time:** 30-60 minutes to completion

---

## 📞 Contact / Documentation

**Project Status:** Ready for handoff to code editor
**Last Updated:** October 3, 2026

---

## PROFESSOR HANDOVER: CLEAN SETUP AND EXECUTION

This section is the authoritative setup guide for running the working version
from a fresh clone. The project is a Windows Python application. Ollama may run
on Windows or inside WSL2, provided that its HTTP API is reachable from Windows
at `http://127.0.0.1:11434`.

### 1. Required software

Install the following before running the project:

- Python 3.10 or newer
- Git
- Ollama
- Tesseract OCR for Windows

Tesseract is used by Phase 1 when the PDF contains image-based text. The
default executable path expected by the project is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is installed elsewhere, update the path in
`src/phase1/bond_pdf_processor.py`.

### 2. Clone and enter the repository

Replace the repository URL with the URL supplied to you:

```powershell
git clone <NEW_REPOSITORY_URL>
cd Working-RAG-LLM-Bond-Analysis
```

The suggested GitHub repository slug is
`Working-RAG-LLM-Bond-Analysis`. GitHub repository names cannot contain the
literal `+` character in the same way as the display title, so the display
title can remain **Working RAG+LLM Bond Analysis** while the URL uses the
hyphenated slug.

### 3. Create and activate a Python virtual environment

PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run the project without activation by using
the interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Install and start Ollama models

Start Ollama and confirm that its API responds:

```powershell
ollama serve
```

In a second PowerShell window, download the exact models used by the project:

```powershell
ollama pull nomic-embed-text:latest
ollama pull qwen3.5:0.8b
```

Confirm that both models are installed:

```powershell
ollama list
```

The pipeline uses:

- `nomic-embed-text:latest` for 768-dimensional bond-section embeddings.
- `qwen3.5:0.8b` for structured covenant presence analysis and investor
  explanations.

The pipeline does not call Kaggle, Groq, OpenAI, Hugging Face, or any external
LLM API. All model requests are sent to the local Ollama service.

### 5. Run the complete pipeline

From the repository root, run only this command:

```powershell
.\.venv\Scripts\python.exe main.py
```

`main.py` runs every project phase in order:

1. **Phase 1** reads `data/master_list.txt` and
   `data/bond_memorandum.pdf`, then creates cleaned source files.
2. **Phase 2** detects numbered bond sections such as `2.1`, `2.2`, and
   `8.38`, then creates section-aware chunks without random overlap windows.
3. **Phase 3** embeds the chunks, stores them in ChromaDB, retrieves the three
   most relevant sections for each covenant, and analyzes all 120 covenant
   requirements with Ollama.

The command may take several minutes because it performs local embedding and
LLM calls. It is normal to see progress messages for each bond section and
each covenant.

### 6. Review the output

After a successful run, open:

```text
phase3_output/covenant_analysis_investor_rag_report.md
```

This is the concise investor-facing report. It contains:

- Covenant coverage counts
- Present, absent, and unclear classifications
- Critical missing or unclear protections
- Investor protection interpretation
- Contract section references for follow-up
- Methodology and limitations

The structured analysis is stored in:

```text
phase3_output/covenant_analysis_rag_llm.json
```

The JSON includes retrieved sections, similarity distances, confidence values,
LLM status, and covenant-level rationale. Raw evidence excerpts are
intentionally omitted from the Markdown report to keep it readable for an
investor.

Intermediate files are stored in:

```text
phase1_output/master_key.json
phase1_output/bond_cleaned.txt
phase2_output/section_aware_chunks.json
phase2_output/section_aware_chunking_stats.json
phase2_output/chroma_rag_db/
```

### 7. Troubleshooting

#### Ollama connection refused

Check that Ollama is running and reachable:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

If Ollama is running inside WSL2 and Windows cannot reach it, start Ollama
with a host binding that allows Windows access, or run Ollama on Windows.

#### Model not found

Run:

```powershell
ollama pull nomic-embed-text:latest
ollama pull qwen3.5:0.8b
```

The model names are configured in
`phase3_rag_llm_pipeline.py`. Do not substitute a different embedding model
without rebuilding the ChromaDB index.

#### Tesseract not found

Install Tesseract OCR or update the executable path in
`src/phase1/bond_pdf_processor.py`. The PDF's embedded text can still be
processed, but image-only text may be missing without OCR.

#### Starting over with fresh generated data

The source files in `data/` are preserved. To rebuild generated artifacts,
remove only these directories and files before rerunning `main.py`:

```powershell
Remove-Item -Recurse -Force .\phase2_output\chroma_rag_db
Remove-Item .\phase2_output\section_aware_chunks.json
Remove-Item .\phase2_output\section_aware_chunking_stats.json
Remove-Item .\phase3_output\covenant_analysis_rag_llm.json
Remove-Item .\phase3_output\covenant_analysis_investor_rag_report.md
```

Do not remove `data/bond_memorandum.pdf` or `data/master_list.txt`.

### 8. Project limitations

- The system determines whether contractual covenant language is present in
  the supplied bond document. It does not determine whether the issuer is
  currently complying with the covenant.
- The report is an analytical aid and not legal, credit, or investment advice.
- An `unclear` result requires manual legal review and must not be treated as
  confirmed investor protection.
- Ollama must be running locally; no hosted LLM service is required.

### 9. New repository handoff

The working version should be placed in a separate repository so that the
professor receives an independent history rather than the old branch history.
The recommended repository display name is:

```text
Working RAG+LLM Bond Analysis
```

The recommended URL-safe repository slug is:

```text
Working-RAG-LLM-Bond-Analysis
```

After the new repository is created, initialize and publish this working
directory as its own Git history:

```powershell
git init
git add .
git commit -m "Initial working RAG and LLM bond analysis pipeline"
git branch -M main
git remote add origin <NEW_REPOSITORY_URL>
git push -u origin main
```

Before publishing, confirm that `.env`, `.venv`, ChromaDB databases, caches, and
logs are ignored by `.gitignore`. Never commit API keys or other secrets.
**Tested On:** Windows 11 + Python 3.10+ (WSL Ubuntu for Ollama initially, now knowledge-based)
**GPU:** NVIDIA RTX 3050 4GB (optional - not needed for this phase)

---

**🚀 Ready to proceed! Code editor can now take it from here.**