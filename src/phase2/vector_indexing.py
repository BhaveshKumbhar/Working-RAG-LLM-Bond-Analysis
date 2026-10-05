# code/phase2/vector_indexing.py - FIXED RETRIEVAL (Use our embedding service for queries)

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    import chromadb
except ImportError:
    print("❌ chromadb not installed. Run: pip install chromadb")
    raise

from .chunking_strategy import Chunk
from .embedding_service import EmbeddingService

@dataclass
class IndexingConfig:
    """Configuration for vector indexing"""
    persist_dir: str = "phase2_output/chroma_db"
    distance_metric: str = "cosine"
    collection_master: str = "master_covenants"
    collection_bond: str = "bond_chunks"

class VectorIndexing:
    """Index chunks to ChromaDB - use OUR embedding service for queries"""
    
    def __init__(self, 
                 embedding_service: EmbeddingService,
                 config: Optional[IndexingConfig] = None):
        """Initialize vector indexing"""
        if config is None:
            config = IndexingConfig()
        
        self.config = config
        self.embedding_service = embedding_service
        self.client = None
        self.master_collection = None
        self.bond_collection = None
        
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize ChromaDB"""
        print(f"🗄️  Initializing ChromaDB at {self.config.persist_dir}...")
        
        # Create persist directory
        os.makedirs(self.config.persist_dir, exist_ok=True)
        
        try:
            # Initialize Chroma client
            self.client = chromadb.PersistentClient(path=self.config.persist_dir)
            
            # Delete old collections
            print(f"  Cleaning up old collections...")
            try:
                self.client.delete_collection(name=self.config.collection_master)
            except:
                pass
            
            try:
                self.client.delete_collection(name=self.config.collection_bond)
            except:
                pass
            
            # Create NEW collections
            print(f"  Creating new collections...")
            self.master_collection = self.client.get_or_create_collection(
                name=self.config.collection_master,
                metadata={
                    "description": "Master covenant list",
                    "hnsw:space": self.config.distance_metric
                }
            )
            print(f"  ✓ Created {self.config.collection_master}")
            
            self.bond_collection = self.client.get_or_create_collection(
                name=self.config.collection_bond,
                metadata={
                    "description": "Bond document chunks",
                    "hnsw:space": self.config.distance_metric
                }
            )
            print(f"  ✓ Created {self.config.collection_bond}")
            
            print(f"✅ ChromaDB initialized successfully")
        
        except Exception as e:
            print(f"❌ Error initializing ChromaDB: {e}")
            raise
    
    def index_master_covenants(self, master_key: Dict) -> Dict:
        """Index master covenants"""
        print(f"\n📑 Indexing master covenants...")
        
        covenants = master_key.get("all_covenants", [])
        
        if not covenants:
            print("❌ No covenants found")
            return {}
        
        # Prepare data
        ids = []
        documents = []
        metadatas = []
        
        for covenant in covenants:
            covenant_id = covenant.get("id", "")
            
            # Rich text for embedding
            text = f"""
Covenant: {covenant.get('name', '')}
Type: {covenant.get('type', '')}
Section: {covenant.get('section', '')}
Description: {covenant.get('description', '')}
Keywords: {', '.join(covenant.get('keywords', []))}
            """.strip()
            
            ids.append(covenant_id)
            documents.append(text)
            metadatas.append({
                "covenant_id": covenant_id,
                "name": covenant.get("name", ""),
                "type": covenant.get("type", ""),
            })
        
        # Generate embeddings
        print(f"  Generating embeddings for {len(documents)} covenants...")
        embeddings = self.embedding_service.embed_texts(documents)
        
        # Add to ChromaDB
        print(f"  Adding to ChromaDB...")
        try:
            self.master_collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            print(f"✅ Master covenants indexed: {len(covenants)} covenants")
        except Exception as e:
            print(f"❌ Error adding to ChromaDB: {e}")
            raise
        
        return {
            "total_covenants_indexed": len(covenants),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0
        }
    
    def index_bond_chunks(self, chunks: List[Chunk]) -> Dict:
        """Index bond chunks"""
        print(f"\n📄 Indexing bond chunks...")
        
        if not chunks:
            print("❌ No chunks provided")
            return {}
        
        # Prepare data
        ids = []
        documents = []
        metadatas = []
        
        for chunk in chunks:
            ids.append(chunk.id)
            documents.append(chunk.text)
            metadatas.append({
                "page": str(chunk.page_number),
                "section": chunk.section_reference,
                "words": str(chunk.word_count),
            })
        
        # Generate embeddings
        print(f"  Generating embeddings for {len(documents)} chunks...")
        embeddings = self.embedding_service.embed_texts(documents, batch_size=20)
        
        # Add to ChromaDB
        print(f"  Adding to ChromaDB...")
        try:
            self.bond_collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
            print(f"✅ Bond chunks indexed: {len(chunks)} chunks")
        except Exception as e:
            print(f"❌ Error adding to ChromaDB: {e}")
            raise
        
        return {
            "total_chunks_indexed": len(chunks),
            "embedding_dimension": len(embeddings[0]) if embeddings else 0
        }
    
    def verify_indexing(self) -> Dict:
        """Verify indexing"""
        print(f"\n✔️  Verifying indexing...")
        
        master_count = self.master_collection.count()
        bond_count = self.bond_collection.count()
        
        print(f"  Master covenants: {master_count}")
        print(f"  Bond chunks: {bond_count}")
        
        status = "✅ Ready for retrieval" if master_count > 0 and bond_count > 0 else "❌ Incomplete"
        
        return {
            "master_count": master_count,
            "bond_count": bond_count,
            "status": status
        }
    
    def test_retrieval(self, query: str, n_results: int = 3) -> Dict:
        """
        Test retrieval using OUR embedding service for the query
        CRITICAL: Do NOT use ChromaDB's built-in query text embedding
                  Use our embedding service to ensure consistency
        """
        print(f"\n🔍 Testing retrieval: '{query}'...")
        
        try:
            # CRITICAL: Embed query using OUR service (same as indexing)
            query_embedding = self.embedding_service.embed_text(query)
            
            print(f"   Query embedding dimension: {len(query_embedding)}-dim")
            
            # Query using the embedding (not text)
            master_results = self.master_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            bond_results = self.bond_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            print(f"  ✅ Master: {len(master_results['documents'][0])} results")
            if master_results['documents'][0]:
                print(f"     Top match: {master_results['documents'][0][0][:60]}...")
            
            print(f"  ✅ Bond: {len(bond_results['documents'][0])} results")
            if bond_results['documents'][0]:
                print(f"     Top match: {bond_results['documents'][0][0][:60]}...")
            
            return {"success": True}
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            raise