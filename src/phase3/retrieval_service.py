# src/phase3/retrieval_service.py - FIXED: Use embedding service for queries

import json
import os
from typing import List, Dict, Tuple, Optional

try:
    import chromadb
except ImportError:
    print("❌ chromadb not installed. Run: pip install chromadb")
    raise

class RetrievalService:
    """Retrieve bond chunks similar to each master covenant"""
    
    def __init__(self, 
                 vector_db_path: str = "phase2_output/chroma_db",
                 embedding_service=None):
        """Initialize retrieval service with ChromaDB"""
        self.vector_db_path = vector_db_path
        self.client = None
        self.bond_collection = None
        self.master_collection = None
        self.embedding_service = embedding_service  # IMPORTANT: Accept embedding service
        
        self._initialize_db()
    
    def _initialize_db(self):
        """Load ChromaDB collections from Phase 2"""
        print(f"📂 Loading ChromaDB from {self.vector_db_path}...")
        
        try:
            self.client = chromadb.PersistentClient(path=self.vector_db_path)
            
            # Load collections from Phase 2
            self.bond_collection = self.client.get_collection(
                name="bond_chunks"
            )
            print(f"   ✓ Loaded bond_chunks collection")
            
            self.master_collection = self.client.get_collection(
                name="master_covenants"
            )
            print(f"   ✓ Loaded master_covenants collection")
            
            # Verify counts
            bond_count = self.bond_collection.count()
            master_count = self.master_collection.count()
            
            print(f"✅ Vector DB loaded: {master_count} covenants, {bond_count} chunks")
            
        except Exception as e:
            print(f"❌ Error loading ChromaDB: {e}")
            raise
    
    def retrieve_for_covenant(self, 
                             covenant_id: str,
                             covenant_text: str,
                             top_k: int = 5,
                             similarity_threshold: float = 0.3) -> List[Dict]:
        """
        Retrieve bond chunks similar to a covenant
        
        CRITICAL: Use embedding service to embed query (NOT ChromaDB's built-in)
        This ensures consistency: same 768-dim embeddings as indexing
        """
        
        try:
            # CRITICAL FIX: Embed query using OUR embedding service
            # This returns 768-dim (same as indexing)
            if self.embedding_service:
                query_embedding = self.embedding_service.embed_text(covenant_text)
                
                # Query using embedding (NOT text)
                results = self.bond_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k * 2
                )
            else:
                # Fallback: Use text-based query (NOT recommended, may cause dimension mismatch)
                print(f"⚠️  No embedding service provided - using text query (may fail)")
                results = self.bond_collection.query(
                    query_texts=[covenant_text],
                    n_results=top_k * 2
                )
            
            # Process results
            matched_chunks = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i, chunk_id in enumerate(results['ids'][0]):
                    # Calculate similarity score
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = max(0, 1 - distance)
                    
                    # Only include if above threshold
                    if similarity >= similarity_threshold:
                        chunk_text = results['documents'][0][i]
                        chunk_metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        
                        matched_chunks.append({
                            "chunk_id": chunk_id,
                            "text": chunk_text,
                            "similarity_score": round(similarity, 3),
                            "page": int(chunk_metadata.get('page', 0)),
                            "section": chunk_metadata.get('section', 'Unknown'),
                            "word_count": int(chunk_metadata.get('words', 0))
                        })
            
            return matched_chunks[:top_k]
        
        except Exception as e:
            print(f"❌ Error retrieving chunks for {covenant_id}: {e}")
            return []
    
    def retrieve_all_covenants(self, 
                              master_covenants: List[Dict],
                              top_k: int = 5,
                              similarity_threshold: float = 0.3) -> Dict:
        """
        Retrieve bond chunks for all master covenants
        
        Returns:
            Dict mapping covenant_id -> list of matched chunks
        """
        print(f"\n🔍 Retrieving bond chunks for {len(master_covenants)} covenants...")
        
        if not self.embedding_service:
            print("⚠️  WARNING: No embedding service provided!")
            print("   This may cause dimension mismatch errors")
            print("   Pass embedding_service to RetrievalService constructor")
        
        retrieval_results = {}
        matched_count = 0
        
        for i, covenant in enumerate(master_covenants):
            covenant_id = covenant.get('id', '')
            covenant_text = covenant.get('description', '')
            
            # Retrieve similar chunks
            matched_chunks = self.retrieve_for_covenant(
                covenant_id=covenant_id,
                covenant_text=covenant_text,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            retrieval_results[covenant_id] = {
                "covenant": covenant,
                "matched_chunks": matched_chunks,
                "match_count": len(matched_chunks),
                "best_similarity": matched_chunks[0]['similarity_score'] if matched_chunks else 0
            }
            
            matched_count += len(matched_chunks)
            
            # Progress update
            if (i + 1) % 20 == 0:
                print(f"  ✓ Retrieved for {i+1}/{len(master_covenants)} covenants ({matched_count} chunk matches)")
        
        print(f"✅ Retrieval complete: {matched_count} chunk matches across all covenants")
        
        return retrieval_results
    
    def get_retrieval_stats(self, retrieval_results: Dict) -> Dict:
        """Calculate statistics about retrieval results"""
        
        total_covenants = len(retrieval_results)
        covenants_with_matches = len([r for r in retrieval_results.values() if r['match_count'] > 0])
        total_matches = sum(r['match_count'] for r in retrieval_results.values())
        avg_matches_per_covenant = total_matches / total_covenants if total_covenants > 0 else 0
        
        # Similarity scores
        all_scores = []
        for result in retrieval_results.values():
            if result['matched_chunks']:
                all_scores.extend([c['similarity_score'] for c in result['matched_chunks']])
        
        avg_similarity = sum(all_scores) / len(all_scores) if all_scores else 0
        
        return {
            "total_covenants_analyzed": total_covenants,
            "covenants_with_matches": covenants_with_matches,
            "total_chunk_matches": total_matches,
            "avg_matches_per_covenant": round(avg_matches_per_covenant, 2),
            "avg_similarity_score": round(avg_similarity, 3),
            "covenants_without_matches": total_covenants - covenants_with_matches
        }