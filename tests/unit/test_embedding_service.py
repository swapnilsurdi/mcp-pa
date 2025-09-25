"""
Unit tests for embedding service
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
from typing import List

from src.embedding_service import (
    EmbeddingService,
    ContextAwareEmbeddingService,
    get_embedding_service,
    generate_content_embedding
)


class TestEmbeddingService:
    """Test EmbeddingService class"""
    
    def test_init_local_provider(self):
        """Test initialization with local provider"""
        service = EmbeddingService(provider="local", model="all-MiniLM-L6-v2")
        
        assert service.provider == "local"
        assert service.model == "all-MiniLM-L6-v2"
        assert service.dimension == 384
        assert service.local_model is not None
    
    def test_init_openai_provider_without_key(self):
        """Test initialization with OpenAI provider but no API key"""
        with patch.dict('os.environ', {}, clear=True):
            service = EmbeddingService(provider="openai")
            # Should fallback to local model
            assert service.provider == "local"
            assert service.local_model is not None
    
    def test_init_openai_provider_with_key(self):
        """Test initialization with OpenAI provider and API key"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            with patch('openai.AsyncOpenAI') as mock_client:
                service = EmbeddingService(provider="openai")
                
                assert service.provider == "openai"
                assert service.dimension == 1536
                assert mock_client.called
    
    def test_invalid_provider(self):
        """Test initialization with invalid provider"""
        with pytest.raises(ValueError, match="Unsupported embedding provider"):
            EmbeddingService(provider="invalid_provider")
    
    @pytest_asyncio.fixture
    async def local_service(self):
        """Create local embedding service for testing"""
        return EmbeddingService(provider="local", model="all-MiniLM-L6-v2")
    
    @pytest_asyncio.fixture
    async def mock_openai_service(self):
        """Create mock OpenAI service"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            with patch('openai.AsyncOpenAI') as mock_client:
                service = EmbeddingService(provider="openai")
                
                # Mock the client response
                mock_response = MagicMock()
                mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
                service.client.embeddings.create = AsyncMock(return_value=mock_response)
                
                return service
    
    @pytest.mark.asyncio
    async def test_generate_embedding_local(self, local_service):
        """Test embedding generation with local model"""
        text = "This is a test sentence for embedding generation"
        
        embedding = await local_service.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        assert not all(x == 0.0 for x in embedding)  # Should not be all zeros
    
    @pytest.mark.asyncio
    async def test_generate_embedding_openai(self, mock_openai_service):
        """Test embedding generation with OpenAI API"""
        text = "This is a test sentence for embedding generation"
        
        embedding = await mock_openai_service.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert embedding == [0.1] * 1536  # Mock response
    
    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, local_service):
        """Test embedding generation with empty text"""
        embedding = await local_service.generate_embedding("")
        
        assert isinstance(embedding, list)
        assert len(embedding) == local_service.dimension
        assert all(x == 0.0 for x in embedding)  # Should be zero vector
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_local(self, local_service):
        """Test batch embedding generation with local model"""
        texts = [
            "First test sentence",
            "Second test sentence", 
            "Third test sentence"
        ]
        
        embeddings = await local_service.generate_embeddings_batch(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_openai(self, mock_openai_service):
        """Test batch embedding generation with OpenAI API"""
        texts = ["First text", "Second text"]
        
        # Mock batch response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        mock_openai_service.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        embeddings = await mock_openai_service.generate_embeddings_batch(texts)
        
        assert len(embeddings) == 2
        assert embeddings[0] == [0.1] * 1536
        assert embeddings[1] == [0.2] * 1536
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty(self, local_service):
        """Test batch embedding generation with empty list"""
        embeddings = await local_service.generate_embeddings_batch([])
        
        assert embeddings == []
    
    def test_cosine_similarity(self, local_service):
        """Test cosine similarity calculation"""
        # Identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = local_service.cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 1e-6
        
        # Orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = local_service.cosine_similarity(vec1, vec2)
        assert abs(similarity - 0.0) < 1e-6
        
        # Opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = local_service.cosine_similarity(vec1, vec2)
        assert abs(similarity - (-1.0)) < 1e-6
    
    def test_cosine_similarity_different_lengths(self, local_service):
        """Test cosine similarity with different length vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0]
        
        similarity = local_service.cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    def test_cosine_similarity_zero_vectors(self, local_service):
        """Test cosine similarity with zero vectors"""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        similarity = local_service.cosine_similarity(vec1, vec2)
        assert similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_find_most_similar(self, local_service):
        """Test finding most similar embeddings"""
        query_embedding = [1.0, 0.0, 0.0]
        candidates = [
            [1.0, 0.0, 0.0],  # Identical - highest similarity
            [0.8, 0.6, 0.0],  # Similar
            [0.0, 1.0, 0.0],  # Orthogonal - lowest similarity
            [-1.0, 0.0, 0.0]  # Opposite - negative similarity
        ]
        
        results = await local_service.find_most_similar(query_embedding, candidates, top_k=2)
        
        assert len(results) == 2
        assert results[0][0] == 0  # Index of identical vector
        assert results[0][1] == 1.0  # Perfect similarity
        assert results[1][0] == 1  # Index of similar vector
        assert results[1][1] > 0.5  # High similarity
    
    @pytest.mark.asyncio
    async def test_find_most_similar_empty_candidates(self, local_service):
        """Test finding most similar with empty candidates"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await local_service.find_most_similar(query_embedding, [], top_k=5)
        assert results == []
    
    @pytest.mark.asyncio
    async def test_error_handling(self, local_service):
        """Test error handling in embedding generation"""
        # Mock local model to raise exception
        with patch.object(local_service.local_model, 'encode', side_effect=Exception("Model error")):
            embedding = await local_service.generate_embedding("test text")
            
            # Should return zero vector on error
            assert len(embedding) == local_service.dimension
            assert all(x == 0.0 for x in embedding)


class TestContextAwareEmbeddingService:
    """Test ContextAwareEmbeddingService class"""
    
    @pytest_asyncio.fixture
    async def context_service(self):
        """Create context-aware embedding service for testing"""
        return ContextAwareEmbeddingService(provider="local", model="all-MiniLM-L6-v2")
    
    @pytest.mark.asyncio
    async def test_generate_contextual_embedding_project(self, context_service):
        """Test contextual embedding generation for project"""
        text = "Build a web application"
        
        embedding = await context_service.generate_contextual_embedding(
            text, 
            context_type="project",
            metadata={"priority": "high", "tags": ["web", "development"]}
        )
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert not all(x == 0.0 for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_contextual_embedding_todo(self, context_service):
        """Test contextual embedding generation for todo"""
        text = "Write unit tests"
        
        embedding = await context_service.generate_contextual_embedding(
            text,
            context_type="todo",
            metadata={"priority": "high"}
        )
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
    
    def test_enhance_text_with_context_project(self, context_service):
        """Test text enhancement with project context"""
        enhanced = context_service._enhance_text_with_context(
            "Build API",
            "project",
            {"priority": "high", "tags": ["api", "backend"]}
        )
        
        assert "Build API" in enhanced
        assert "This is a project description" in enhanced
        assert "Priority: high" in enhanced
        assert "Tags: api, backend" in enhanced
    
    def test_enhance_text_with_context_todo(self, context_service):
        """Test text enhancement with todo context"""
        enhanced = context_service._enhance_text_with_context(
            "Fix bug",
            "todo",
            {"priority": "urgent", "status": "in_progress"}
        )
        
        assert "Fix bug" in enhanced
        assert "This is a task or todo item" in enhanced
        assert "Priority: urgent" in enhanced
        assert "Status: in_progress" in enhanced
    
    def test_enhance_text_with_context_no_metadata(self, context_service):
        """Test text enhancement without metadata"""
        enhanced = context_service._enhance_text_with_context(
            "Test text",
            "general",
            None
        )
        
        assert enhanced == "Test text"
    
    def test_cached_similarity(self, context_service):
        """Test cached similarity calculation"""
        emb1 = (0.1, 0.2, 0.3)
        emb2 = (0.4, 0.5, 0.6)
        
        # First calculation
        similarity1 = context_service._cached_similarity("hash1", "hash2", emb1, emb2)
        
        # Second calculation should use cache
        similarity2 = context_service._cached_similarity("hash1", "hash2", emb1, emb2)
        
        assert similarity1 == similarity2


class TestGlobalFunctions:
    """Test global functions"""
    
    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns singleton"""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_generate_content_embedding_project(self):
        """Test generate_content_embedding for project"""
        embedding = await generate_content_embedding(
            "Build web app",
            content_type="project",
            metadata={"priority": "high"}
        )
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_content_embedding_general(self):
        """Test generate_content_embedding for general content"""
        embedding = await generate_content_embedding("General text")
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0


class TestPerformance:
    """Performance tests for embedding service"""
    
    @pytest.mark.asyncio
    async def test_batch_vs_individual_performance(self, local_service):
        """Test that batch processing is more efficient than individual calls"""
        import time
        
        texts = [f"Test sentence number {i}" for i in range(10)]
        
        # Time individual calls
        start_time = time.time()
        individual_embeddings = []
        for text in texts:
            emb = await local_service.generate_embedding(text)
            individual_embeddings.append(emb)
        individual_time = time.time() - start_time
        
        # Time batch call
        start_time = time.time()
        batch_embeddings = await local_service.generate_embeddings_batch(texts)
        batch_time = time.time() - start_time
        
        # Batch should be faster (or at least not significantly slower)
        assert batch_time <= individual_time * 1.5  # Allow 50% tolerance
        
        # Results should be similar
        assert len(individual_embeddings) == len(batch_embeddings)
        for i, (ind, batch) in enumerate(zip(individual_embeddings, batch_embeddings)):
            similarity = local_service.cosine_similarity(ind, batch)
            assert similarity > 0.99, f"Embedding {i} differs significantly: {similarity}"
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self, local_service):
        """Test that same text produces consistent embeddings"""
        text = "Consistent embedding test"
        
        embedding1 = await local_service.generate_embedding(text)
        embedding2 = await local_service.generate_embedding(text)
        
        similarity = local_service.cosine_similarity(embedding1, embedding2)
        assert similarity > 0.99, f"Embeddings are not consistent: {similarity}"
    
    @pytest.mark.benchmark
    def test_embedding_generation_benchmark(self, benchmark, local_service):
        """Benchmark embedding generation speed"""
        import asyncio
        
        def generate_embedding():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    local_service.generate_embedding("Benchmark test sentence")
                )
            finally:
                loop.close()
        
        result = benchmark(generate_embedding)
        
        assert isinstance(result, list)
        assert len(result) == local_service.dimension