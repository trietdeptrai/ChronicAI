"""
Unit tests for TransformersClient (VinAI Translate).

Tests translation functionality, chunking, caching, and performance features.
"""
import pytest
import warnings
from app.services.transformers_client import transformers_client


class TestTransformersClient:
    """Tests for VinAI translation client."""

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
        # Trigger loading
        await transformers_client.translate_vi_to_en("test")

        # Vi->En should now be loaded
        assert transformers_client.is_vi2en_loaded() is True
        assert transformers_client.is_loaded() is True

    @pytest.mark.asyncio
    async def test_both_models_load(self):
        """Test that both translation models load correctly."""
        # Trigger Vi->En model
        await transformers_client.translate_vi_to_en("xin chào")
        assert transformers_client.is_vi2en_loaded() is True

        # Trigger En->Vi model
        await transformers_client.translate_en_to_vi("hello")
        assert transformers_client.is_en2vi_loaded() is True

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
    async def test_translation_cache(self):
        """Test that translation caching works."""
        # Clear cache first
        transformers_client.clear_cache()

        test_text = "Tôi bị đau đầu"

        # First call - should be cache miss
        result1 = await transformers_client.translate_vi_to_en(test_text)

        # Second call with same text - should be cache hit
        result2 = await transformers_client.translate_vi_to_en(test_text)

        # Results should be identical
        assert result1 == result2

        # Check cache stats
        stats = transformers_client.get_cache_stats()
        if stats:  # Only if caching is enabled
            assert stats["hits"] >= 1

    @pytest.mark.asyncio
    async def test_cache_stats(self):
        """Test cache statistics."""
        transformers_client.clear_cache()

        # Do some translations
        await transformers_client.translate_vi_to_en("xin chào")
        await transformers_client.translate_vi_to_en("xin chào")  # Cache hit
        await transformers_client.translate_vi_to_en("tạm biệt")

        stats = transformers_client.get_cache_stats()
        if stats:
            assert stats["size"] >= 2
            assert stats["hits"] >= 1
            assert "hit_rate" in stats

    @pytest.mark.asyncio
    async def test_model_unload_deprecated(self):
        """Test that unload_model() is deprecated but still works."""
        # Load model first
        await transformers_client.translate_vi_to_en("test")
        assert transformers_client.is_loaded() is True

        # Unload should emit deprecation warning but return True
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            success = await transformers_client.unload_model()

            # Should have raised a deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        assert success is True
        # Models are now kept persistent, so is_loaded should still be True
        assert transformers_client.is_loaded() is True

    @pytest.mark.asyncio
    async def test_clear_cache(self):
        """Test cache clearing."""
        # Do a translation to populate cache
        await transformers_client.translate_vi_to_en("test text")

        # Clear cache
        transformers_client.clear_cache()

        # Cache should be empty
        stats = transformers_client.get_cache_stats()
        if stats:
            assert stats["size"] == 0
            assert stats["hits"] == 0
            assert stats["misses"] == 0

    @pytest.mark.asyncio
    async def test_structured_text_preservation(self):
        """Test that En->Vi preserves text structure."""
        structured_text = """## Summary
- Point one about the patient
- Point two about treatment

1. First recommendation
2. Second recommendation"""

        result = await transformers_client.translate_en_to_vi(structured_text)

        # Check that structure is preserved (bullets converted to Vietnamese format)
        assert "•" in result or "1." in result or "2." in result
        # Should contain Vietnamese characters
        assert any(c in result for c in ["á", "à", "ả", "ã", "ạ", "ă", "ế", "ệ", "ị", "ờ"])

    @pytest.mark.asyncio
    async def test_batch_direction_validation(self):
        """Test that invalid batch direction raises error."""
        with pytest.raises(ValueError) as exc_info:
            await transformers_client.translate_batch(
                ["text"],
                direction="invalid"
            )

        assert "Invalid direction" in str(exc_info.value)
