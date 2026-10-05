# phase2_pipeline_bulletproof.py - FINAL WORKING VERSION

import json
import os
from typing import Dict, List
from datetime import datetime

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from phase2.chunking_strategy import ChunkingStrategy, Chunk
from phase2.embedding_service import EmbeddingService, EmbeddingConfig
from phase2.vector_indexing import VectorIndexing, IndexingConfig

class Phase2Pipeline:
    """Phase 2: Chunking & Vector Indexing - BULLETPROOF VERSION"""
    
    def __init__(self, 
                 phase1_output_dir: str = "phase1_output",
                 phase2_output_dir: str = "phase2_output",
                 chunk_size: int = 300,
                 chunk_overlap: int = 50):
        self.phase1_dir = phase1_output_dir
        self.phase2_dir = phase2_output_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        os.makedirs(phase2_output_dir, exist_ok=True)
        
        self.chunks = []
        self.chunking_stats = {}
        self.indexing_stats = {}
    
    def run(self) -> Dict:
        """Run Phase 2"""
        
        print("=" * 70)
        print("PHASE 2: CHUNKING & VECTOR INDEXING (BULLETPROOF VERSION)")
        print("=" * 70)
        
        # Step 1: Load Phase 1 outputs
        print("\n[STEP 1] LOADING PHASE 1 OUTPUTS")
        print("-" * 70)
        
        master_key = self._load_master_key()
        bond_text = self._load_bond_text()
        
        # Step 2: Chunk document
        print("\n[STEP 2] CHUNKING BOND DOCUMENT")
        print("-" * 70)
        
        self.chunks, self.chunking_stats = self._chunk_document(bond_text)
        self._save_chunking_report()
        
        # Step 3: Initialize embeddings
        print("\n[STEP 3] INITIALIZING EMBEDDING SERVICE")
        print("-" * 70)
        
        embedding_service = self._initialize_embeddings()
        
        # Step 4: Initialize vector DB
        print("\n[STEP 4] INITIALIZING VECTOR DATABASE")
        print("-" * 70)
        
        vector_indexing = self._initialize_vector_db(embedding_service)
        
        # Step 5: Index master covenants
        print("\n[STEP 5] INDEXING MASTER COVENANTS")
        print("-" * 70)
        
        master_stats = vector_indexing.index_master_covenants(master_key)
        self.indexing_stats['master_covenants'] = master_stats
        
        # Step 6: Index bond chunks
        print("\n[STEP 6] INDEXING BOND CHUNKS")
        print("-" * 70)
        
        bond_stats = vector_indexing.index_bond_chunks(self.chunks)
        self.indexing_stats['bond_chunks'] = bond_stats
        
        # Step 7: Verify
        print("\n[STEP 7] VERIFYING VECTOR DATABASE")
        print("-" * 70)
        
        verification = vector_indexing.verify_indexing()
        self.indexing_stats['verification'] = verification
        
        # Step 8: Test retrieval
        print("\n[STEP 8] TESTING RETRIEVAL")
        print("-" * 70)
        
        self._test_retrieval(vector_indexing)
        
        # Step 9: Save reports
        print("\n[STEP 9] SAVING REPORTS")
        print("-" * 70)
        
        self._save_indexing_report()
        self._save_chunk_metadata()
        
        # Summary
        return self._print_summary()
    
    def _load_master_key(self) -> Dict:
        """Load master covenants"""
        path = os.path.join(self.phase1_dir, "master_key.json")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = len(data.get('all_covenants', []))
        print(f"✅ Loaded master key: {count} covenants")
        
        return data
    
    def _load_bond_text(self) -> str:
        """Load bond text"""
        path = os.path.join(self.phase1_dir, "bond_cleaned.txt")
        
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        words = len(text.split())
        print(f"✅ Loaded bond document: {len(text)} chars, {words} words")
        
        return text
    
    def _chunk_document(self, bond_text: str):
        """Chunk the document"""
        chunker = ChunkingStrategy(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=100
        )
        
        chunks, stats = chunker.chunk_full_document(bond_text)
        
        print(f"\n📊 CHUNKING STATISTICS:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
        
        return chunks, stats
    
    def _initialize_embeddings(self) -> EmbeddingService:
        """Initialize embedding service"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        if not service.test_connection():
            raise ConnectionError("Cannot connect to Ollama")
        
        return service
    
    def _initialize_vector_db(self, embedding_service: EmbeddingService) -> VectorIndexing:
        """Initialize vector database"""
        config = IndexingConfig(
            persist_dir=os.path.join(self.phase2_dir, "chroma_db")
        )
        
        return VectorIndexing(embedding_service, config)
    
    def _test_retrieval(self, vector_indexing: VectorIndexing):
        """Test retrieval"""
        queries = [
            "debt-to-equity ratio requirements",
            "dividend restrictions",
            "reporting and disclosure requirements"
        ]
        
        for query in queries:
            try:
                vector_indexing.test_retrieval(query, n_results=2)
            except Exception as e:
                print(f"  ⚠️  Test failed: {e}")
    
    def _save_chunking_report(self):
        """Save chunking report"""
        path = os.path.join(self.phase2_dir, "chunking_report.json")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "parameters": {
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "min_chunk_size": 200
            },
            "statistics": self.chunking_stats,
            "samples": [
                {
                    "id": c.id,
                    "words": c.word_count,
                    "preview": c.text[:100]
                }
                for c in self.chunks[:3]
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {path}")
    
    def _save_indexing_report(self):
        """Save indexing report"""
        path = os.path.join(self.phase2_dir, "indexing_report.json")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": self.indexing_stats,
            "vector_database": {
                "type": "ChromaDB",
                "location": os.path.join(self.phase2_dir, "chroma_db"),
                "metric": "cosine"
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {path}")
    
    def _save_chunk_metadata(self):
        """Save chunk metadata"""
        path = os.path.join(self.phase2_dir, "chunk_metadata.json")
        
        metadata = [
            {
                "id": c.id,
                "page": c.page_number,
                "section": c.section_reference,
                "words": c.word_count,
                "has_table": c.contains_table
            }
            for c in self.chunks
        ]
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {path}")
    
    def _print_summary(self) -> Dict:
        """Print summary"""
        print("\n" + "=" * 70)
        print("PHASE 2 SUMMARY")
        print("=" * 70)
        
        print(f"""
📊 CHUNKING RESULTS:
   - Total chunks: {self.chunking_stats.get('total_chunks', 0)}
   - Avg chunk size: {self.chunking_stats.get('avg_chunk_size', 0):.0f} words
   - Min/Max: {self.chunking_stats.get('min_chunk_size', 0)}/{self.chunking_stats.get('max_chunk_size', 0)}

🔍 INDEXING RESULTS:
   - Master covenants: {self.indexing_stats.get('master_covenants', {}).get('total_covenants_indexed', 0)}
   - Bond chunks: {self.indexing_stats.get('bond_chunks', {}).get('total_chunks_indexed', 0)}
   - Status: {self.indexing_stats.get('verification', {}).get('status', 'Unknown')}

💾 OUTPUTS:
   ✅ phase2_output/chunking_report.json
   ✅ phase2_output/indexing_report.json
   ✅ phase2_output/chunk_metadata.json
   ✅ phase2_output/chroma_db/ (vector database)

🎯 NEXT: Phase 3 - RAG + LLM Analysis
        """)
        
        return {
            "chunking": self.chunking_stats,
            "indexing": self.indexing_stats
        }


if __name__ == "__main__":
    pipeline = Phase2Pipeline()
    
    try:
        summary = pipeline.run()
        print("\n✅ Phase 2 COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ Phase 2 FAILED: {e}")
        import traceback
        traceback.print_exc()