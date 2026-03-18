from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm_service import (
    complete,
    normalize_model_name,
    _resolve_model_and_provider,
    _build_completion_kwargs,
    build_request_payload_preview,
)


def test_normalize_model_name_for_common_providers():
    assert normalize_model_name("GPT-5.2") == "openai/gpt-5.2"
    assert normalize_model_name("gpt-4o") == "openai/gpt-4o"
    assert normalize_model_name("Claude-3-5-Sonnet") == "anthropic/claude-3-5-sonnet"
    assert normalize_model_name("gemini-1.5-pro") == "gemini/gemini-1.5-pro"
    assert normalize_model_name("openai/GPT-5.2") == "openai/gpt-5.2"
    assert normalize_model_name("google/gemini-2.5-pro") == "gemini/gemini-2.5-pro"


def test_resolve_anthropic_aliases_to_latest():
    provider, model_name = _resolve_model_and_provider("anthropic/claude-3-7-sonnet")
    assert provider == "anthropic"
    assert model_name == "claude-3-7-sonnet"


def test_build_completion_kwargs_sets_anthropic_max_tokens():
    kwargs = _build_completion_kwargs(
        "anthropic/claude-3-5-sonnet",
        "sk-test",
        [
            {"role": "system", "content": "system instructions"},
            {"role": "user", "content": "hello"},
        ],
        stream=False,
    )
    assert kwargs["model"] == "claude-3-5-sonnet"
    assert kwargs["custom_llm_provider"] == "anthropic"
    assert kwargs["max_tokens"] == 1024
    assert kwargs["extra_headers"]["anthropic-version"] == "2023-06-01"
    assert kwargs["system"] == "system instructions"
    assert kwargs["messages"] == [{"role": "user", "content": [{"type": "text", "text": "hello"}]}]


def test_build_completion_kwargs_sets_gemini_provider_mode():
    kwargs = _build_completion_kwargs(
        "gemini/gemini-2.5-pro",
        "sk-test",
        [{"role": "user", "content": "hello"}],
        stream=False,
    )
    assert kwargs["model"] == "gemini-2.5-pro"
    assert kwargs["custom_llm_provider"] == "gemini"


def test_build_request_payload_preview_matches_anthropic_body_shape():
    payload = build_request_payload_preview(
        "anthropic/claude-3-5-sonnet",
        [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "teste"},
        ],
    )
    assert payload["model"] == "claude-3-5-sonnet"
    assert payload["max_tokens"] == 1024
    assert payload["system"] == "system prompt"
    assert payload["messages"] == [{"role": "user", "content": [{"type": "text", "text": "teste"}]}]


def test_build_completion_kwargs_sets_anthropic_stream_flag_when_streaming():
    kwargs = _build_completion_kwargs(
        "anthropic/claude-3-5-sonnet",
        "sk-test",
        [{"role": "user", "content": "stream me"}],
        stream=True,
    )
    assert kwargs["model"].startswith("claude-3-5-sonnet")
    assert kwargs["stream"] is True
    assert kwargs["messages"] == [{"role": "user", "content": [{"type": "text", "text": "stream me"}]}]


@pytest.mark.asyncio
async def test_complete_uses_normalized_model_name():
    mock_response = AsyncMock()
    mock_response.choices = [type("Choice", (), {"message": type("Message", (), {"content": "ok"})()})()]

    with patch("app.services.llm_service.litellm.acompletion", new_callable=AsyncMock, return_value=mock_response) as mocked:
        result = await complete("GPT-5.2", "sk-test", [{"role": "user", "content": "hello"}])

    assert result == "ok"
    mocked.assert_awaited_once()
    assert mocked.await_args.kwargs["model"] == "openai/gpt-5.2"
