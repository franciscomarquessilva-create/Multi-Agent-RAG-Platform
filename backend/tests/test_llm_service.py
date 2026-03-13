from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_service import complete, normalize_model_name


def test_normalize_model_name_for_common_providers():
    assert normalize_model_name("GPT-5.2") == "openai/gpt-5.2"
    assert normalize_model_name("gpt-4o") == "openai/gpt-4o"
    assert normalize_model_name("Claude-3-5-Sonnet") == "anthropic/claude-3-5-sonnet"
    assert normalize_model_name("gemini-1.5-pro") == "gemini/gemini-1.5-pro"
    assert normalize_model_name("openai/GPT-5.2") == "openai/gpt-5.2"


@pytest.mark.asyncio
async def test_complete_uses_normalized_model_name():
    mock_response = AsyncMock()
    mock_response.choices = [type("Choice", (), {"message": type("Message", (), {"content": "ok"})()})()]

    with patch("app.services.llm_service.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mocked:
        result = await complete("GPT-5.2", "sk-test", [{"role": "user", "content": "hello"}])

    assert result == "ok"
    mocked.assert_awaited_once()
    assert mocked.await_args.kwargs["model"] == "openai/gpt-5.2"
