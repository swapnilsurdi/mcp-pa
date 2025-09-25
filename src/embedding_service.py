"""
Embedding Service for Vector Search

Provides embedding generation using OpenAI's text-embedding models
and local alternatives for semantic search capabilities.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
import os
from functools import lru_cache

import openai
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings for vector search"""
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-ada-002"):
        self.provider = provider
        self.model = model
        self.client = None
        self.local_model = None
        self.dimension = 1536  # Default for OpenAI ada-002
        
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the embedding provider"""
        if self.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not found, falling back to local model")
                self.provider = "local"
                self._initialize_local_model()
            else:
                self.client = openai.AsyncOpenAI(api_key=api_key)
                self.dimension = 1536  # ada-002 dimensions
                
        elif self.provider == "local":
            self._initialize_local_model()
        
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
    
    def _initialize_local_model(self):
        """Initialize local sentence transformer model"""
        try:
            # Use a lightweight but effective model
            model_name = "all-MiniLM-L6-v2"  # 384 dimensions, fast and good quality
            self.local_model = SentenceTransformer(model_name)
            self.dimension = 384
            self.provider = "local"
            logger.info(f"Initialized local embedding model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize local embedding model: {e}")
            raise
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        try:
            if self.provider == "openai":
                return await self._generate_openai_embedding(text)
            else:
                return await self._generate_local_embedding(text)
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dimension
    
    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches"""
        if not texts:
            return []
        
        # Filter out empty texts
        filtered_texts = [text.strip() for text in texts if text and text.strip()]
        
        if not filtered_texts:
            return [[0.0] * self.dimension] * len(texts)
        
        try:
            if self.provider == "openai":
                return await self._generate_openai_embeddings_batch(filtered_texts, batch_size)
            else:
                return await self._generate_local_embeddings_batch(filtered_texts)
                
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimension] * len(texts)
    
    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text.replace("\n", " ")  # OpenAI recommendation
        )
        return response.data[0].embedding
    
    async def _generate_openai_embeddings_batch(self, texts: List[str], batch_size: int) -> List[List[float]]:
        """Generate embeddings in batches using OpenAI API"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Clean texts for OpenAI
            cleaned_batch = [text.replace("\n", " ") for text in batch]
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=cleaned_batch
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            # Rate limiting for OpenAI API
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        return embeddings
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: self.local_model.encode([text], convert_to_numpy=True)[0].tolist()
        )
        return embedding
    
    async def _generate_local_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model in batch"""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.local_model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        )
        return embeddings.tolist()
    
    def cosine_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if len(embedding1) != len(embedding2):
            return 0.0
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norms == 0:
            return 0.0
        
        return dot_product / norms
    
    async def find_most_similar(self, query_embedding: List[float], candidate_embeddings: List[List[float]], top_k: int = 5) -> List[tuple]:
        """Find most similar embeddings to query"""
        if not candidate_embeddings:
            return []
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.cosine_similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


class ContextAwareEmbeddingService(EmbeddingService):
    """Enhanced embedding service with context awareness"""
    
    def __init__(self, provider: str = "openai", model: str = "text-embedding-ada-002"):
        super().__init__(provider, model)
        self.context_cache = {}
    
    async def generate_contextual_embedding(self, text: str, context_type: str = "general", metadata: Optional[Dict[str, Any]] = None) -> List[float]:
        """Generate embedding with contextual enhancement"""
        
        # Enhance text with context information
        enhanced_text = self._enhance_text_with_context(text, context_type, metadata)
        
        # Generate embedding
        return await self.generate_embedding(enhanced_text)
    
    def _enhance_text_with_context(self, text: str, context_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Enhance text with contextual information"""
        enhanced_parts = [text]
        
        # Add context type information
        if context_type == "project":
            enhanced_parts.append("This is a project description.")
        elif context_type == "todo":
            enhanced_parts.append("This is a task or todo item.")
        elif context_type == "document":
            enhanced_parts.append("This is a document content.")
        elif context_type == "event":
            enhanced_parts.append("This is a calendar event.")
        
        # Add metadata context
        if metadata:
            if metadata.get("priority"):
                enhanced_parts.append(f"Priority: {metadata['priority']}")
            if metadata.get("tags"):
                enhanced_parts.append(f"Tags: {', '.join(metadata['tags'])}")
            if metadata.get("status"):
                enhanced_parts.append(f"Status: {metadata['status']}")
        
        return " ".join(enhanced_parts)
    
    @lru_cache(maxsize=1000)
    def _cached_similarity(self, emb1_hash: str, emb2_hash: str, emb1_tuple: tuple, emb2_tuple: tuple) -> float:
        """Cached cosine similarity calculation"""
        return self.cosine_similarity(list(emb1_tuple), list(emb2_tuple))


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None

def get_embedding_service(provider: str = "local", model: str = "all-MiniLM-L6-v2") -> EmbeddingService:
    """Get or create global embedding service instance"""
    global _embedding_service
    
    if _embedding_service is None:
        _embedding_service = ContextAwareEmbeddingService(provider, model)
    
    return _embedding_service

async def generate_content_embedding(content: str, content_type: str = "general", metadata: Optional[Dict[str, Any]] = None) -> List[float]:
    """Convenience function to generate embeddings"""
    service = get_embedding_service()
    
    if isinstance(service, ContextAwareEmbeddingService):
        return await service.generate_contextual_embedding(content, content_type, metadata)
    else:
        return await service.generate_embedding(content)