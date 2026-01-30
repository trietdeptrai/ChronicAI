"""
Unit tests for LLM (Translation Sandwich) Pipeline.
"""
import pytest


class TestTranslationSandwich:
    """Tests for translation sandwich pipeline - requires Ollama running."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama with qwen2.5:1.5b")
    async def test_vi_to_en_translation(self):
        """Vietnamese to English translation works."""
        from app.services.llm import translate_vi_to_en
        
        result = await translate_vi_to_en("Xin chào, tôi đau đầu.")
        
        # Should contain some English
        assert any(word in result.lower() for word in ["hello", "headache", "head", "pain"])
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama with qwen2.5:1.5b")
    async def test_en_to_vi_translation(self):
        """English to Vietnamese translation works."""
        from app.services.llm import translate_en_to_vi
        
        result = await translate_en_to_vi("Hello, I have a headache.")
        
        # Should contain Vietnamese characters
        assert any(char in result for char in "àáâãèéêìíòóôõùúýăđĩũơưạ")
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama with all models")
    async def test_full_pipeline_yields_stages(self):
        """Process medical query yields progress stages."""
        from app.services.llm import process_medical_query
        from uuid import uuid4
        
        stages = []
        async for update in process_medical_query(
            user_input_vi="Tôi bị đau đầu",
            patient_id=uuid4(),
            image_path=None
        ):
            stages.append(update.get("stage"))
        
        # Should have all pipeline stages
        assert "translating_input" in stages
        assert "medical_reasoning" in stages
        assert "translating_output" in stages
        assert "complete" in stages


class TestSystemHealth:
    """Tests for system health check."""
    
    @pytest.mark.asyncio
    async def test_health_check_format(self):
        """Health check returns expected format."""
        from app.services.llm import check_system_health
        
        result = await check_system_health()
        
        assert "status" in result
        assert "ollama" in result
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
