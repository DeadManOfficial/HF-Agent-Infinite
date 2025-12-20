"""
Knowledge Base Module
=====================

Vector-based semantic search and knowledge management.
Uses FAISS for efficient similarity search (free, local).
"""

import os
import json
import pickle
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result with relevance score."""
    id: str
    resource_type: str
    name: str
    description: str
    score: float
    metadata: Dict[str, Any]


class KnowledgeBase:
    """
    Vector-based knowledge management system.
    
    Features:
    - Semantic search using embeddings
    - FAISS index for fast similarity search
    - SQLite backend for metadata storage
    - Automatic embedding generation
    """
    
    def __init__(
        self,
        db_path: str = "data/hf_infinite.db",
        index_path: str = "data/embeddings/faiss_index",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        self.db_path = Path(db_path)
        self.index_path = Path(index_path)
        self.embedding_model_name = embedding_model
        
        self.index = None
        self.embedding_model = None
        self.id_mapping: Dict[int, str] = {}  # FAISS index -> resource ID
        
        self._init_embedding_model()
        self._load_or_create_index()
    
    def _init_embedding_model(self):
        """Initialize the sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            self.embedding_model = None
    
    def _load_or_create_index(self):
        """Load existing FAISS index or create new one."""
        try:
            import faiss
            
            index_file = self.index_path.with_suffix('.index')
            mapping_file = self.index_path.with_suffix('.mapping')
            
            if index_file.exists() and mapping_file.exists():
                self.index = faiss.read_index(str(index_file))
                with open(mapping_file, 'rb') as f:
                    self.id_mapping = pickle.load(f)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index (384 dimensions for all-MiniLM-L6-v2)
                dimension = 384
                self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
                self.id_mapping = {}
                logger.info("Created new FAISS index")
                
        except ImportError:
            logger.warning("FAISS not installed. Install with: pip install faiss-cpu")
            self.index = None
    
    def _save_index(self):
        """Save FAISS index to disk."""
        if self.index is None:
            return
        
        try:
            import faiss
            
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            index_file = self.index_path.with_suffix('.index')
            mapping_file = self.index_path.with_suffix('.mapping')
            
            faiss.write_index(self.index, str(index_file))
            with open(mapping_file, 'wb') as f:
                pickle.dump(self.id_mapping, f)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a text string."""
        if self.embedding_model is None:
            return None
        
        try:
            import numpy as np
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
    
    def add_document(
        self,
        doc_id: str,
        resource_type: str,
        text: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a document to the knowledge base.
        
        Args:
            doc_id: Unique document identifier
            resource_type: Type of resource (model, dataset, space)
            text: Text content to embed
            metadata: Additional metadata to store
        """
        if self.index is None or self.embedding_model is None:
            logger.warning("Index or embedding model not available")
            return False
        
        try:
            import numpy as np
            
            # Generate embedding
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            embedding = np.array([embedding], dtype=np.float32)
            
            # Add to FAISS index
            idx = self.index.ntotal
            self.index.add(embedding)
            self.id_mapping[idx] = f"{resource_type}:{doc_id}"
            
            # Store metadata in SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO embeddings (id, resource_type, resource_id, embedding, model_name)
                VALUES (?, ?, ?, ?, ?)
            """, (
                f"{resource_type}:{doc_id}",
                resource_type,
                doc_id,
                pickle.dumps(embedding[0]),
                self.embedding_model_name
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            return False
    
    def build_index_from_db(self, batch_size: int = 1000) -> int:
        """
        Build FAISS index from all resources in database.
        
        Returns:
            Number of documents indexed
        """
        if self.index is None or self.embedding_model is None:
            logger.warning("Index or embedding model not available")
            return 0
        
        try:
            import numpy as np
            import faiss
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Reset index
            dimension = 384
            self.index = faiss.IndexFlatIP(dimension)
            self.id_mapping = {}
            
            total_indexed = 0
            
            # Index models
            cursor.execute("SELECT id, name, description FROM models WHERE description IS NOT NULL")
            models = cursor.fetchall()
            
            for model_id, name, description in models:
                text = f"{name}. {description}" if description else name
                if self.add_document(model_id, "model", text):
                    total_indexed += 1
            
            # Index datasets
            cursor.execute("SELECT id, name, description FROM datasets WHERE description IS NOT NULL")
            datasets = cursor.fetchall()
            
            for ds_id, name, description in datasets:
                text = f"{name}. {description}" if description else name
                if self.add_document(ds_id, "dataset", text):
                    total_indexed += 1
            
            # Index spaces
            cursor.execute("SELECT id, name, description FROM spaces WHERE description IS NOT NULL")
            spaces = cursor.fetchall()
            
            for space_id, name, description in spaces:
                text = f"{name}. {description}" if description else name
                if self.add_document(space_id, "space", text):
                    total_indexed += 1
            
            conn.close()
            self._save_index()
            
            logger.info(f"Built index with {total_indexed} documents")
            return total_indexed
            
        except Exception as e:
            logger.error(f"Failed to build index: {e}")
            return 0
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        resource_type: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform semantic search over the knowledge base.
        
        Args:
            query: Search query
            top_k: Number of results to return
            resource_type: Filter by resource type (optional)
        
        Returns:
            List of SearchResult objects
        """
        if self.index is None or self.embedding_model is None:
            logger.warning("Index or embedding model not available")
            return []
        
        if self.index.ntotal == 0:
            logger.warning("Index is empty")
            return []
        
        try:
            import numpy as np
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query, normalize_embeddings=True)
            query_embedding = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index
            scores, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))
            
            results = []
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                
                full_id = self.id_mapping.get(idx)
                if not full_id:
                    continue
                
                res_type, res_id = full_id.split(":", 1)
                
                # Filter by resource type if specified
                if resource_type and res_type != resource_type:
                    continue
                
                # Get metadata from database
                table = f"{res_type}s"
                cursor.execute(f"SELECT name, description FROM {table} WHERE id = ?", (res_id,))
                row = cursor.fetchone()
                
                if row:
                    results.append(SearchResult(
                        id=res_id,
                        resource_type=res_type,
                        name=row[0] or res_id,
                        description=row[1] or "",
                        score=float(score),
                        metadata={"table": table}
                    ))
                
                if len(results) >= top_k:
                    break
            
            conn.close()
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def get_similar(
        self,
        doc_id: str,
        resource_type: str,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Find similar documents to a given document."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        table = f"{resource_type}s"
        cursor.execute(f"SELECT name, description FROM {table} WHERE id = ?", (doc_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return []
        
        query_text = f"{row[0]}. {row[1]}" if row[1] else row[0]
        results = self.semantic_search(query_text, top_k + 1, resource_type)
        
        # Remove the query document itself
        return [r for r in results if r.id != doc_id][:top_k]


# Export
__all__ = ["KnowledgeBase", "SearchResult"]
