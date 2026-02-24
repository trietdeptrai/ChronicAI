"""
Unit tests for ECGClassifierService auth dispatcher.

Tests verify that _get_auth_headers produces correct headers for each
ECG_CLASSIFIER_AUTH_TYPE without touching the network or gcloud CLI.
"""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out heavy dependencies that app.services.__init__ eagerly imports.
# This lets us test ecg_classifier_service in isolation.
# ---------------------------------------------------------------------------
_STUBS = [
    "langchain_core", "langchain_core.runnables",
    "langgraph", "langgraph.graph", "langgraph.graph.state",
    "langgraph.types", "langgraph.checkpoint", "langgraph.checkpoint.memory",
]
for mod_name in _STUBS:
    sys.modules.setdefault(mod_name, MagicMock())

# Now it's safe to import
from app.services.ecg_classifier_service import ECGClassifierService  # noqa: E402


@pytest.fixture
def service():
    """Create a fresh ECGClassifierService instance."""
    return ECGClassifierService()


class TestAuthHeaders:
    """Test _get_auth_headers for each auth type."""

    @pytest.mark.asyncio
    async def test_auth_type_none(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "none"
            headers = await service._get_auth_headers()

        assert headers == {"Content-Type": "application/json"}
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_auth_type_bearer(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "bearer"
            ms.ecg_classifier_bearer_token = "my-secret-token"
            headers = await service._get_auth_headers()

        assert headers["Authorization"] == "Bearer my-secret-token"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_auth_type_bearer_missing_token(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "bearer"
            ms.ecg_classifier_bearer_token = ""
            with pytest.raises(RuntimeError, match="ECG_CLASSIFIER_BEARER_TOKEN"):
                await service._get_auth_headers()

    @pytest.mark.asyncio
    async def test_auth_type_api_key_default_header(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "api_key"
            ms.ecg_classifier_api_key = "key-12345"
            ms.ecg_classifier_api_key_header = "X-API-Key"
            headers = await service._get_auth_headers()

        assert headers["X-API-Key"] == "key-12345"
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_auth_type_api_key_custom_header(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "api_key"
            ms.ecg_classifier_api_key = "key-12345"
            ms.ecg_classifier_api_key_header = "X-Custom-Auth"
            headers = await service._get_auth_headers()

        assert headers["X-Custom-Auth"] == "key-12345"

    @pytest.mark.asyncio
    async def test_auth_type_api_key_missing_key(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "api_key"
            ms.ecg_classifier_api_key = ""
            ms.ecg_classifier_api_key_header = "X-API-Key"
            with pytest.raises(RuntimeError, match="ECG_CLASSIFIER_API_KEY"):
                await service._get_auth_headers()

    @pytest.mark.asyncio
    async def test_auth_type_vertex_gcloud(self, service):
        mock_llm_client = AsyncMock()
        mock_llm_client._get_vertex_access_token = AsyncMock(
            return_value="gcloud-token-xyz"
        )

        # app.services.__init__ re-exports `llm_client` (the instance)
        # as the module-level `app.services.llm_client`, overriding the module.
        # We need to temporarily put a mock module with the expected attribute.
        mock_module = MagicMock()
        mock_module.llm_client = mock_llm_client

        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "vertex_gcloud"
            with patch.dict(sys.modules, {"app.services.llm_client": mock_module}):
                headers = await service._get_auth_headers()

        assert headers["Authorization"] == "Bearer gcloud-token-xyz"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_auth_type_unsupported(self, service):
        with patch("app.services.ecg_classifier_service.settings") as ms:
            ms.ecg_classifier_auth_type = "oauth2"
            with pytest.raises(RuntimeError, match="Unsupported"):
                await service._get_auth_headers()
