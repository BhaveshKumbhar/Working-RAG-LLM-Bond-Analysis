# code/phase2/embedding_service.py - CORRECT DIMENSION DETECTION

from typing import List, Optional
from dataclasses import dataclass

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    print("❌ langchain-ollama not installed. Run: pip install langchain-ollama")
    raise

@dataclass
class EmbeddingConfig:
    """Configuration for embedding service"""
    model: str = "nomic-embed-text"
    ollama_base_url: str = "http://localhost:11434"
    embedding_dim: int = None  # Will be auto-detected from ACTUAL embeddings

class EmbeddingService:
    """Generate embeddings with ACTUAL dimension detection"""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """Initialize embedding service"""
        if config is None:
            config = EmbeddingConfig()
        
        self.config = config
        self.embeddings_model = None
        self.actual_embedding_dim = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Ollama embeddings"""
        print(f"🔌 Connecting to Ollama at {self.config.ollama_base_url}...")
        
        try:
            self.embeddings_model = OllamaEmbeddings(
                model=self.config.model,
                base_url=self.config.ollama_base_url
            )
            print(f"✅ Embeddings model loaded: {self.config.model}")
        except Exception as e:
            print(f"❌ Error initializing embeddings: {e}")
            raise
        
        # IMPORTANT: Test connection only, dimension will be detected from ACTUAL embeddings
        print(f"🔗 Testing connection...")
        if not self.test_connection():
            raise ConnectionError("Cannot connect to Ollama")
    
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text"""
        try:
            embedding = self.embeddings_model.embed_query(text)
            return embedding
        except Exception as e:
            print(f"❌ Error embedding text: {e}")
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Embed multiple texts in batches
        IMPORTANT: Dimension is detected from FIRST batch (actual embeddings)
        """
        print(f"🧠 Embedding {len(texts)} texts (batch size: {batch_size})...")
        
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            try:
                batch_embeddings = self.embeddings_model.embed_documents(batch)
                embeddings.extend(batch_embeddings)
                
                # CRITICAL: Detect actual dimension from FIRST batch
                if self.actual_embedding_dim is None and batch_embeddings:
                    self.actual_embedding_dim = len(batch_embeddings[0])
                    self.config.embedding_dim = self.actual_embedding_dim
                    print(f"   📊 Detected actual embedding dimension: {self.actual_embedding_dim}-dim (from batch)")
                
                # Progress update
                if (i + batch_size) % 50 == 0:
                    print(f"  ✅ Embedded {min(i + batch_size, len(texts))}/{len(texts)} texts")
            
            except Exception as e:
                print(f"❌ Error embedding batch at index {i}: {e}")
                raise
        
        print(f"✅ Embedding complete: {len(embeddings)} vectors ({self.actual_embedding_dim}-dim)")
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get actual embedding dimension (detected from batch)"""
        return self.actual_embedding_dim
    
    def test_connection(self) -> bool:
        """Test Ollama connection"""
        try:
            test_embedding = self.embed_text("connection test")
            
            if test_embedding:
                dim = len(test_embedding)
                print(f"✅ Connection test passed: {dim}-dim embedding")
                print(f"   (Actual dimension will be confirmed during batch embedding)")
                return True
            else:
                print(f"❌ Empty embedding returned")
                return False
        
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
            return False


if __name__ == "__main__":
    config = EmbeddingConfig()
    service = EmbeddingService(config)
    
    print(f"\n📊 Embedding dimension will be detected during batch processing")