# phase1_pipeline.py - FIXED with UTF-8 encoding

import json
import os
from src.phase1.master_list_parser_v2 import MasterListParserV2
from src.phase1.bond_pdf_processor import BondPDFProcessor, ExtractedPage
from src.phase1.text_cleaner import BondTextCleaner, CleanedPage
from typing import Dict, Tuple

class Phase1Pipeline:
    """Complete Phase 1: Data Preparation"""
    
    def __init__(self, master_list_path: str = "data/master_list.txt", bond_pdf_path: str = "data/bond_memorandum.pdf", output_dir: str = "phase1_output"):
        self.master_list_path = master_list_path
        self.bond_pdf_path = bond_pdf_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def run(self) -> Tuple[Dict, Dict[int, CleanedPage], str]:
        """
        Run complete Phase 1 pipeline
        
        Returns:
            - master_key (structured JSON)
            - cleaned_bond_pages (per-page data with metadata)
            - processed_bond_text (full cleaned text for chunking)
        """
        
        print("=" * 70)
        print("PHASE 1: DATA PREPARATION")
        print("=" * 70)
        
        # Step 1: Parse Master List
        print("\n[STEP 1] PARSING MASTER LIST")
        print("-" * 70)
        parser = MasterListParserV2()
        
        with open(self.master_list_path, 'r', encoding='utf-8') as f:
            master_list_text = f.read()
        
        covenants = parser.parse_master_list(master_list_text)
        master_key = parser.save_to_json(covenants, f"{self.output_dir}/master_key.json")
        
        # Step 2: Process Bond PDF
        print("\n[STEP 2] PROCESSING BOND PDF")
        print("-" * 70)
        processor = BondPDFProcessor(self.bond_pdf_path, self.output_dir)
        
        text_by_page = processor.extract_text_from_pdf()
        ocr_results = processor.extract_images_and_ocr()
        merged_pages = processor.merge_text_and_ocr(text_by_page, ocr_results)
        
        # Save intermediate extraction
        extraction_report = {
            "total_pages": len(merged_pages),
            "pages_with_images": sum(1 for p in merged_pages.values() if p.has_images),
            "extraction_method": {
                page_num: page.source 
                for page_num, page in merged_pages.items()
            }
        }
        
        with open(f"{self.output_dir}/extraction_report.json", 'w', encoding='utf-8') as f:
            json.dump(extraction_report, f, indent=2, ensure_ascii=False)
        
        # Step 3: Clean Text
        print("\n[STEP 3] CLEANING AND NORMALIZING TEXT")
        print("-" * 70)
        cleaner = BondTextCleaner()
        
        text_dict = {page.page_number: page.text_content for page in merged_pages.values()}
        cleaned_pages = cleaner.clean_full_document(text_dict)
        
        # Step 4: Aggregate Cleaned Text
        print("\n[STEP 4] AGGREGATING CLEANED DOCUMENT")
        print("-" * 70)
        
        aggregated_text = ""
        page_boundaries = {}  # Track where each page starts
        
        for page_num in sorted(cleaned_pages.keys()):
            page_start_pos = len(aggregated_text)
            page_boundary_marker = f"\n\n[PAGE BOUNDARY: Page {page_num}]\n\n"
            
            aggregated_text += page_boundary_marker
            aggregated_text += cleaned_pages[page_num].cleaned_text
            
            page_boundaries[page_num] = {
                "start_position": page_start_pos,
                "end_position": len(aggregated_text),
                "sections": cleaned_pages[page_num].section_references,
                "warnings": cleaned_pages[page_num].warnings
            }
        
        # Step 5: Save All Outputs
        print("\n[STEP 5] SAVING OUTPUTS")
        print("-" * 70)
        
        # FIX: Save cleaned full document with UTF-8 encoding
        with open(f"{self.output_dir}/bond_cleaned.txt", 'w', encoding='utf-8') as f:
            f.write(aggregated_text)
        print(f"✅ Saved cleaned bond document: {self.output_dir}/bond_cleaned.txt")
        
        # FIX: Save page boundaries and metadata with UTF-8 encoding
        with open(f"{self.output_dir}/page_metadata.json", 'w', encoding='utf-8') as f:
            json.dump(page_boundaries, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved page metadata: {self.output_dir}/page_metadata.json")
        
        # Save per-page cleaned data
        per_page_data = {
            str(page_num): {
                "cleaned_text": page.cleaned_text,
                "sections": page.section_references,
                "has_tables": page.has_tables,
                "warnings": page.warnings
            }
            for page_num, page in cleaned_pages.items()
        }
        
        # FIX: Save per-page data with UTF-8 encoding
        with open(f"{self.output_dir}/per_page_cleaned_data.json", 'w', encoding='utf-8') as f:
            json.dump(per_page_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved per-page data: {self.output_dir}/per_page_cleaned_data.json")
        
        # Print Summary
        print("\n" + "=" * 70)
        print("PHASE 1 SUMMARY")
        print("=" * 70)
        print(f"""
📋 MASTER LIST:
   - Total covenants parsed: {len(covenants)}
   - Output: master_key.json

📄 BOND DOCUMENT:
   - Total pages: {len(cleaned_pages)}
   - Pages with images: {extraction_report['pages_with_images']}
   - Total text length: {len(aggregated_text)} characters
   - Outputs:
     • bond_cleaned.txt (full document)
     • page_metadata.json (page locations + sections)
     • per_page_cleaned_data.json (detailed per-page data)
     • extraction_report.json (processing summary)

✅ Phase 1 Complete! Ready for Phase 2 (Chunking & Indexing)
        """)
        
        return master_key, cleaned_pages, aggregated_text

# Main execution
if __name__ == "__main__":
    pipeline = Phase1Pipeline(
        master_list_path="Covenants.txt",
        bond_pdf_path="your_bond_document.pdf",
        output_dir="phase1_output"
    )
    
    master_key, cleaned_pages, full_text = pipeline.run()