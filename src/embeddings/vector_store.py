import numpy as np
import torch
from typing import Dict, Optional, List, Tuple
from sentence_transformers import SentenceTransformer

class LocalVectorStore:
    """
    Fast Retrieval Layer (GSW).
    Uses BGE-M3 for high-quality dense embeddings.
    Currently strictly in-memory (Dict) for the Pilot Phase.
    """
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        print(f"Initializing Vector Store with BAAI/bge-m3 on {device}...")
        self.model = SentenceTransformer('BAAI/bge-m3', device=device)
        # Maps UUID -> Embedding Vector
        self.index: Dict[str, np.ndarray] = {}
        self.names: Dict[str, str] = {} # UUID -> Name (for debugging/verification)

    def add_entity(self, entity_id: str, text_representation: str):
        """
        Adds or updates an entity in the vector index.
        text_representation: Usually the entity name + description.
        """
        embedding = self.model.encode(text_representation, normalize_embeddings=True)
        self.index[entity_id] = embedding
        self.names[entity_id] = text_representation

    def find_similar_entity(self, query_text: str, threshold: float = 0.92) -> Optional[str]:
        """
        Finds the best matching entity ID for the given query text.
        Returns None if no match exceeds the threshold.
        """
        if not self.index:
            return None

        query_emb = self.model.encode(query_text, normalize_embeddings=True)
        
        best_score = -1.0
        best_id = None

        # Linear scan (Acceptable for <10k entities in Pilot)
        # For production, upgrade to FAISS or Qdrant
        for eid, vector in self.index.items():
            # Cosine similarity
            score = np.dot(query_emb, vector)
            if score > best_score:
                best_score = score
                best_id = eid
        
        if best_score > threshold:
            return best_id
        
        return None
