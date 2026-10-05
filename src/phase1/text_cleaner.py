# text_cleaner.py

import re
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CleanedPage:
    page_number: int
    original_text: str
    cleaned_text: str
    section_references: List[str]  # e.g., ["Section 4.2.1", "Article 5"]
    has_tables: bool
    warnings: List[str]

class BondTextCleaner:
    """Clean and normalize bond document text"""
    
    def __init__(self):
        self.section_pattern = r'(?:Section|Article|Clause|Provision)\s+[\d\.]+[A-Za-z]*'
        self.warning_phrases = [
            "incomplete text",
            "low ocr confidence",
            "possible formatting error",
            "table structure"
        ]
    
    def remove_header_footer(self, text: str) -> str:
        """Remove typical PDF headers/footers"""
        lines = text.split('\n')
        
        # Remove common footer patterns
        cleaned_lines = []
        for line in lines:
            # Skip page numbers, dates at end of lines
            if re.match(r'^\s*\d+\s*$', line):  # Just page number
                continue
            if re.match(r'^(Page|page)\s+\d+\s*$', line):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize excessive whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Strip trailing whitespace from lines
        lines = text.split('\n')
        text = '\n'.join(line.rstrip() for line in lines)
        
        return text
    
    def fix_ocr_errors(self, text: str) -> str:
        """Fix common OCR errors"""
        # Common OCR misreadings
        ocr_fixes = {
            r'\bl\s+(?=[a-z])': 'l',  # "l " → "l"
            r'\bIl\b': 'Il',  # OCR often mistakes 'Il' combinations
            r'\brn\b': 'in',  # "rn" → "in" (common mistake)
            r'\b0\s+(?=[A-Z][a-z])': 'O',  # "0 Smith" → "O Smith"
            r'(?<=[a-z])\s+(?=[A-Z])(?=[a-z])': '',  # Space before lowercase after capital (likely error)
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def extract_section_references(self, text: str) -> List[str]:
        """Extract all section/article references"""
        references = re.findall(self.section_pattern, text, re.IGNORECASE)
        return list(set(references))  # Unique references
    
    def detect_tables(self, text: str) -> bool:
        """Detect if text contains tables"""
        # Look for patterns typical of tables
        has_pipes = '|' in text
        has_dashes = bool(re.search(r'^\s*[\-=]{5,}', text, re.MULTILINE))
        has_columns = bool(re.search(r'\s{2,}\d+\s{2,}', text))
        
        return has_pipes or has_dashes or has_columns
    
    def clean_page(self, page_text: str, page_number: int) -> CleanedPage:
        """Clean a single page"""
        warnings = []
        original_text = page_text
        
        # Step 1: Remove header/footer
        text = self.remove_header_footer(page_text)
        
        # Step 2: Normalize whitespace
        text = self.normalize_whitespace(text)
        
        # Step 3: Fix OCR errors
        text = self.fix_ocr_errors(text)
        
        # Step 4: Extract metadata
        section_refs = self.extract_section_references(text)
        has_tables = self.detect_tables(text)
        
        # Step 5: Add warnings
        if len(text.strip()) < 100:
            warnings.append("Page has very little text - may be image-only")
        
        if '[OCR' in original_text and len(section_refs) == 0:
            warnings.append("OCR extracted text with no section references")
        
        if has_tables:
            warnings.append("Page contains tables - structure may be preserved")
        
        return CleanedPage(
            page_number=page_number,
            original_text=original_text,
            cleaned_text=text,
            section_references=section_refs,
            has_tables=has_tables,
            warnings=warnings
        )
    
    def clean_full_document(self, pages: Dict[int, str]) -> Dict[int, CleanedPage]:
        """Clean entire document"""
        print("🧹 Cleaning bond document...")
        
        cleaned_pages = {}
        
        for page_num, text in pages.items():
            cleaned_page = self.clean_page(text, page_num)
            cleaned_pages[page_num] = cleaned_page
            
            if cleaned_page.warnings:
                print(f"  ⚠️  Page {page_num}: {', '.join(cleaned_page.warnings)}")
        
        print(f"✅ Cleaning complete: {len(cleaned_pages)} pages")
        return cleaned_pages

# Usage
if __name__ == "__main__":
    cleaner = BondTextCleaner()
    # After extraction, clean the text
    # cleaned_pages = cleaner.clean_full_document(extracted_pages)