# code/phase2/chunking_strategy.py - TOKEN-AWARE VERSION

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Chunk:
    """Individual chunk with metadata"""
    id: str
    text: str
    page_number: int
    section_reference: str
    chunk_index: int
    word_count: int
    start_char_pos: int
    end_char_pos: int
    contains_table: bool
    source: str = "text"

class ChunkingStrategy:
    """Token-aware chunking that respects embedding model limits"""
    
    def __init__(self, 
                 chunk_size: int = 300,  # REDUCED: was 600, now 300 words
                 chunk_overlap: int = 50,  # REDUCED: was 150, now 50 words
                 min_chunk_size: int = 100):  # REDUCED: was 200, now 100 words
        """
        Reduced chunk sizes to avoid embedding model token limits.
        
        nomic-embed-text has ~2000 token context window
        - 300 words ≈ 400-600 tokens (safe)
        - 600 words ≈ 800-1200 tokens (risky with overlap)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def extract_section_reference(self, text: str) -> str:
        """Extract section from text"""
        matches = re.findall(r'(?:Section|Article|Clause)\s+[\d\.]+', text, re.IGNORECASE)
        return matches[0] if matches else "Unknown"
    
    def is_table_content(self, text: str) -> bool:
        """Detect table content"""
        return '|' in text or bool(re.search(r'^\s*[\-=]{5,}', text, re.MULTILINE))
    
    def word_count(self, text: str) -> int:
        """Count words"""
        return len(text.split())
    
    def chunk_full_document(self, bond_text: str) -> Tuple[List[Chunk], Dict]:
        """
        Split text into word-based chunks respecting token limits
        """
        
        print("🔪 Starting TOKEN-AWARE chunking...")
        
        # Clean: remove page markers
        clean_text = re.sub(r'\[PAGE BOUNDARY:\s*Page\s+\d+\]', '', bond_text)
        clean_text = clean_text.strip()
        
        # Split into words
        words = clean_text.split()
        
        print(f"   Total words: {len(words)}")
        print(f"   Chunk size: {self.chunk_size} words (~400-600 tokens)")
        print(f"   Overlap: {self.chunk_overlap} words (small to reduce token count)")
        
        chunks = []
        chunk_idx = 0
        i = 0
        
        while i < len(words):
            # Define chunk boundaries
            chunk_start_idx = i
            chunk_end_idx = min(i + self.chunk_size, len(words))
            
            # Extract chunk words
            chunk_words = words[chunk_start_idx:chunk_end_idx]
            
            # Only create chunk if meets minimum size
            if len(chunk_words) >= self.min_chunk_size:
                chunk_text = ' '.join(chunk_words)
                
                # Estimate page number
                char_position = len(' '.join(words[:chunk_start_idx]))
                estimated_page = min((char_position // 1000) + 1, 261)
                
                section_ref = self.extract_section_reference(chunk_text)
                
                chunk = Chunk(
                    id=f"chunk_{chunk_idx:05d}",
                    text=chunk_text,
                    page_number=estimated_page,
                    section_reference=section_ref,
                    chunk_index=chunk_idx,
                    word_count=len(chunk_words),
                    start_char_pos=char_position,
                    end_char_pos=char_position + len(chunk_text),
                    contains_table=self.is_table_content(chunk_text)
                )
                
                chunks.append(chunk)
                chunk_idx += 1
                
                # Move forward with small overlap
                if chunk_end_idx >= len(words):
                    break
                
                i += (self.chunk_size - self.chunk_overlap)
            else:
                break
        
        stats = self._calculate_stats(chunks)
        
        print(f"✅ Chunking complete: {len(chunks)} chunks created")
        
        return chunks, stats
    
    def _calculate_stats(self, chunks: List[Chunk]) -> Dict:
        """Calculate statistics"""
        
        if not chunks:
            return {}
        
        word_counts = [c.word_count for c in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(word_counts) / len(chunks),
            "min_chunk_size": min(word_counts),
            "max_chunk_size": max(word_counts),
            "total_words": sum(word_counts),
            "chunks_with_tables": len([c for c in chunks if c.contains_table]),
            "pages_covered": 261,
            "avg_chunks_per_page": len(chunks) / 261 if 261 > 0 else 0
        }


if __name__ == "__main__":
    print("Testing TOKEN-AWARE chunking strategy...\n")
    
    with open("phase1_output/bond_cleaned.txt", 'r', encoding='utf-8') as f:
        bond_text = f.read()
    
    print(f"📄 Loaded: {len(bond_text)} chars, {len(bond_text.split())} words\n")
    
    chunker = ChunkingStrategy(chunk_size=300, chunk_overlap=50, min_chunk_size=100)
    chunks, stats = chunker.chunk_full_document(bond_text)
    
    print("\n📊 CHUNKING STATISTICS:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")
    
    print(f"\n📋 SAMPLE CHUNKS (first 3):")
    for chunk in chunks[:3]:
        print(f"\n   {chunk.id}: {chunk.word_count} words (~{chunk.word_count * 4 // 3} tokens)")
        print(f"   Text: {chunk.text[:80]}...")
    
    print("\n✅ Done!")