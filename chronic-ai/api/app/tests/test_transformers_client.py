"""
Unit tests for TransformersClient (VietAI EnviT5).

Tests translation functionality, chunking, and memory management.
"""
import pytest
from app.services.transformers_client import transformers_client


class TestTransformersClient:
    """Tests for EnviT5 translation client."""
    
    @pytest.mark.asyncio
    async def test_vi_to_en_translation(self):
        """Test basic Vietnamese to English translation."""
        result = await transformers_client.translate_vi_to_en(
            "Tôi bị đau đầu và sốt cao."
        )
        
        # Check that translation contains expected medical terms
        result_lower = result.lower()
        assert len(result) > 0, "Translation should not be empty"
        assert "headache" in result_lower or "head" in result_lower
        assert "fever" in result_lower or "temperature" in result_lower
    
    @pytest.mark.asyncio
    async def test_en_to_vi_translation(self):
        """Test basic English to Vietnamese translation."""
        result = await transformers_client.translate_en_to_vi(
            "The patient has diabetes and high blood pressure."
        )
        
        # Check that translation contains Vietnamese
        assert len(result) > 0, "Translation should not be empty"
        # Should contain Vietnamese characters or common medical terms
        assert any(c in result for c in ["á", "à", "ả", "ã", "ạ", "ă", "ế", "ệ"])
    
    @pytest.mark.asyncio
    async def test_empty_text(self):
        """Test translation of empty text."""
        result_vi = await transformers_client.translate_vi_to_en("")
        result_en = await transformers_client.translate_en_to_vi("")
        
        assert result_vi == ""
        assert result_en == ""
    
    @pytest.mark.asyncio
    async def test_long_text_chunking(self):
        """Test automatic chunking for texts exceeding 512 tokens."""
        # Create a long text by repeating a sentence
        base_text = "Bệnh nhân có tiền sử đái tháo đường type 2, tăng huyết áp, và cholesterol cao. "
        long_text = base_text * 30  # Likely exceeds 400 tokens
        
        result = await transformers_client.translate_vi_to_en(long_text)
        
        # Verify translation succeeded
        assert len(result) > 0, "Long text translation should not be empty"
        assert "diabetes" in result.lower()
        assert "blood pressure" in result.lower() or "hypertension" in result.lower()
    
    @pytest.mark.asyncio
    async def test_medical_terminology_vi_to_en(self):
        """Test translation of Vietnamese medical terminology."""
        test_cases = [
            ("vùng mờ ở phổi", ["opacity", "lung", "opacities", "blurry", "shadow"]),
            # "tim to" literally means "big heart" - accept medical or literal terms
            ("Bệnh nhân có tim to", ["cardiomegaly", "enlarged", "heart", "big"]),
            ("tràn dịch màng phổi", ["pleural", "effusion", "fluid"]),
        ]
        
        for vietnamese, expected_terms in test_cases:
            result = await transformers_client.translate_vi_to_en(vietnamese)
            result_lower = result.lower()
            
            # At least one expected term should be present
            assert any(term in result_lower for term in expected_terms), \
                f"Translation '{result}' should contain one of {expected_terms}"
    
    @pytest.mark.asyncio
    async def test_model_loaded_status(self):
        """Test model loading status check."""
        # Initially might not be loaded
        initial_status = transformers_client.is_loaded()
        
        # Trigger loading
        await transformers_client.translate_vi_to_en("test")
        
        # Should now be loaded
        assert transformers_client.is_loaded() is True
    
    @pytest.mark.asyncio
    async def test_batch_translation(self):
        """Test batch translation."""
        texts = [
            "Tôi bị đau bụng",
            "Tôi bị sốt",
            "Tôi bị ho"
        ]
        
        results = await transformers_client.translate_batch(texts, direction="vi_to_en")
        
        assert len(results) == 3
        assert all(len(r) > 0 for r in results)
        
        # Check some expected terms
        results_combined = " ".join(results).lower()
        assert "stomach" in results_combined or "abdominal" in results_combined
        assert "fever" in results_combined
        assert "cough" in results_combined
    
    @pytest.mark.asyncio
    async def test_model_unload(self):
        """Test model unloading."""
        # Load model first
        await transformers_client.translate_vi_to_en("test")
        assert transformers_client.is_loaded() is True
        
        # Unload
        success = await transformers_client.unload_model()
        assert success is True
        assert transformers_client.is_loaded() is False
        
        # Should be able to reload on next use
        await transformers_client.translate_vi_to_en("test again")
        assert transformers_client.is_loaded() is True
