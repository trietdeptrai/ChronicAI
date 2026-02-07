"""
Unit tests for RAG Pipeline.
"""
import pytest
from app.services.rag import chunk_text


class TestChunkText:
    """Tests for text chunking function."""
    
    def test_empty_text(self):
        """Empty text returns empty list."""
        result = chunk_text("")
        assert result == []
    
    def test_short_text(self):
        """Short text returns single chunk."""
        text = "This is a short text."
        result = chunk_text(text, chunk_size=500)
        assert len(result) == 1
        assert result[0] == text
    
    def test_long_text_multiple_chunks(self):
        """Long text is split into multiple chunks."""
        text = "Lorem ipsum dolor sit amet. " * 50  # ~1400 characters
        result = chunk_text(text, chunk_size=300, overlap=50)
        assert len(result) > 1
    
    def test_overlap_maintains_context(self):
        """Chunks have specified overlap."""
        text = "A" * 100 + "B" * 100 + "C" * 100 + "D" * 100
        result = chunk_text(text, chunk_size=120, overlap=20)
        
        # Verify we get multiple chunks
        assert len(result) >= 3
    
    def test_sentence_boundary_breaking(self):
        """Chunks prefer breaking at sentence boundaries."""
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        result = chunk_text(text, chunk_size=50, overlap=10)
        
        # Each chunk should ideally end with a period
        for chunk in result[:-1]:  # Exclude last chunk
            assert "." in chunk
    
    def test_vietnamese_text(self):
        """Vietnamese text is handled correctly."""
        text = "Bệnh nhân đến khám với triệu chứng đau đầu. Huyết áp cao 160/100. Cần theo dõi thêm."
        result = chunk_text(text, chunk_size=50, overlap=10)
        
        assert len(result) >= 1
        # Verify Vietnamese characters are preserved
        assert "Bệnh nhân" in result[0]


class TestGenerateEmbedding:
    """Tests for embedding generation - requires Ollama running."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama with nomic-embed-text")
    async def test_embedding_dimensions(self):
        """Embedding has 768 dimensions."""
        from app.services.rag import generate_embedding
        
        embedding = await generate_embedding("Test text")
        assert len(embedding) == 768
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama with nomic-embed-text")
    async def test_similar_texts_similar_embeddings(self):
        """Similar texts produce similar embeddings."""
        from app.services.rag import generate_embedding
        import numpy as np
        
        text1 = "The patient has high blood pressure."
        text2 = "The patient has hypertension."
        text3 = "I like pizza."
        
        emb1 = np.array(await generate_embedding(text1))
        emb2 = np.array(await generate_embedding(text2))
        emb3 = np.array(await generate_embedding(text3))
        
        # Cosine similarity
        sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
        
        # Similar medical texts should have higher similarity
        assert sim_12 > sim_13
