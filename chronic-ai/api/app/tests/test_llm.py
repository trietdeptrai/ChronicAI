"""
Unit tests for LLM (Translation Sandwich) Pipeline.
"""
import pytest


class TestTranslationSandwich:
    """Tests for translation sandwich pipeline - requires Ollama running."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires translation models")
    async def test_vi_to_en_translation(self):
        """Vietnamese to English translation works."""
        from app.services.llm import translate_vi_to_en
        
        result = await translate_vi_to_en("Xin chào, tôi đau đầu.")
        
        # Should contain some English
        assert any(word in result.lower() for word in ["hello", "headache", "head", "pain"])
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires translation models")
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


class TestPatientSummaryFormatting:
    """Regression tests for patient summary markdown normalization."""

    def test_normalize_patient_summary_sections_and_numbered_lists(self):
        from app.services.llm import _normalize_patient_summary_markdown

        raw = (
            "**Danh sách vấn đề (Problem List)**1.[I10] Tăng huyết áp — Giai đoạn 2, đang điều trị."
            "2.[E78.5] Rối loạn lipid máu — LDL cao, đang điều trị."
            "**Thuốc đang dùng (Current Medications)**1.Losartan 50mg, uống 1 lần/ngày vào buổi sáng."
            "2.Atorvastatin 20mg, uống 1 lần/ngày vào buổi tối."
            "**Dị ứng (Allergies)**NSAIDs"
        )

        formatted = _normalize_patient_summary_markdown(raw)

        assert "## Danh sách vấn đề (Problem List)" in formatted
        assert "## Thuốc đang dùng (Current Medications)" in formatted
        assert "## Dị ứng (Allergies)" in formatted
        assert "\n1. [I10]" in formatted
        assert "\n2. [E78.5]" in formatted
        assert "\n1. Losartan 50mg" in formatted
        assert "\n2. Atorvastatin 20mg" in formatted

    def test_normalize_patient_summary_removes_unbalanced_bold(self):
        from app.services.llm import _normalize_patient_summary_markdown

        raw = (
            "**Diễn tiến bệnh (Disease Progress)Bệnh nhân có tiền sử tăng huyết áp và rối loạn lipid máu."
            "Huyết áp gần nhất 120/80 mmHg."
        )

        formatted = _normalize_patient_summary_markdown(raw)

        assert "**" not in formatted
        assert "## Diễn tiến bệnh (Disease Progress)" in formatted

    def test_normalize_patient_summary_does_not_promote_inline_allergy_phrase(self):
        from app.services.llm import _normalize_patient_summary_markdown

        raw = (
            "## Dị ứng (Allergies)\n"
            "NSAIDs.\n\n"
            "## Đánh giá lâm sàng (Clinical Assessment)\n"
            "Lưu ý tương tác thuốc giảm đau (tránh NSAIDs do Dị ứng (Allergies))."
        )

        formatted = _normalize_patient_summary_markdown(raw)

        assert formatted.count("## Dị ứng (Allergies)") == 1


class TestUploadAnalysisCacheKey:
    """Regression tests for upload analysis cache key stability."""

    def test_upload_analysis_cache_key_normalizes_type_and_title_spacing(self):
        from app.services.llm import _build_upload_analysis_cache_key

        key_one = _build_upload_analysis_cache_key(
            record_type=" ECG ",
            title="  Kết  quả   Điện tâm đồ ",
            extracted_text="Nhịp xoang đều.",
            image_base64="abc123",
        )
        key_two = _build_upload_analysis_cache_key(
            record_type="ecg",
            title="kết quả điện tâm đồ",
            extracted_text="Nhịp xoang đều.",
            image_base64="abc123",
        )

        assert key_one == key_two

    def test_upload_analysis_cache_key_changes_when_payload_changes(self):
        from app.services.llm import _build_upload_analysis_cache_key

        base = _build_upload_analysis_cache_key(
            record_type="ct",
            title="CT ngực",
            extracted_text="Không thấy tổn thương cấp tính.",
            image_base64=None,
        )
        changed_text = _build_upload_analysis_cache_key(
            record_type="ct",
            title="CT ngực",
            extracted_text="Có nốt mờ nhỏ thùy trên phải.",
            image_base64=None,
        )
        changed_image = _build_upload_analysis_cache_key(
            record_type="ct",
            title="CT ngực",
            extracted_text="Không thấy tổn thương cấp tính.",
            image_base64="different-image",
        )

        assert changed_text != base
        assert changed_image != base
