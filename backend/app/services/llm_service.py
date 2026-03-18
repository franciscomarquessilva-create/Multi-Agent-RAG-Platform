import os
import json
from typing import AsyncIterator, List, Dict, Any
import litellm
import httpx


ANTHROPIC_MODEL_ALIASES: dict[str, str] = {}


def _resolve_model_and_provider(model: str) -> tuple[str, str]:
    normalized = normalize_model_name(model)
    if "/" in normalized:
        provider, model_name = normalized.split("/", 1)
    else:
        provider, model_name = "", normalized

    if provider == "anthropic":
        model_name = ANTHROPIC_MODEL_ALIASES.get(model_name, model_name)

    return provider, model_name


def _format_messages_for_anthropic(messages: List[Dict[str, str]]) -> tuple[str | None, List[Dict[str, str]]]:
    system_parts: list[str] = []
    anthropic_messages: list[Dict[str, str]] = []

    for message in messages:
        role = str(message.get("role", "")).strip().lower()
        content = str(message.get("content", ""))

        if role == "system":
            if content.strip():
                system_parts.append(content)
            continue

        if role not in {"user", "assistant"}:
            role = "user"

        anthropic_messages.append({
            "role": role,
            "content": [{"type": "text", "text": content}],
        })

    if not anthropic_messages:
        anthropic_messages = [{"role": "user", "content": [{"type": "text", "text": ""}]}]

    system_text = "\n\n".join(system_parts).strip() or None
    return system_text, anthropic_messages


def _build_completion_kwargs(model: str, api_key: str, messages: List[Dict[str, str]], stream: bool) -> dict:
    provider, model_name = _resolve_model_and_provider(model)

    # Compatibility path for older LiteLLM versions where xAI provider parsing may
    # fail; xAI exposes an OpenAI-compatible API.
    if provider == "xai":
        return {
            "model": model_name,
            "api_key": api_key,
            "messages": messages,
            "stream": stream,
            "custom_llm_provider": "openai",
            "api_base": os.getenv("XAI_API_BASE", "https://api.x.ai/v1"),
        }

    if provider == "anthropic":
        system_text, anthropic_messages = _format_messages_for_anthropic(messages)
        kwargs = {
            "model": model_name,
            "messages": anthropic_messages,
            "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "1024")),
        }
        if system_text is not None:
            kwargs["system"] = system_text
        if stream:
            kwargs["stream"] = True
        return kwargs

    if provider == "gemini":
        return {
            "model": model_name,
            "api_key": api_key,
            "messages": messages,
            "stream": stream,
            "custom_llm_provider": "gemini",
        }

    resolved_model = f"{provider}/{model_name}" if provider else model_name
    return {
        "model": resolved_model,
        "api_key": api_key,
        "messages": messages,
        "stream": stream,
    }


def build_request_payload_preview(model: str, messages: List[Dict[str, str]]) -> dict:
    kwargs = _build_completion_kwargs(model, "__redacted__", messages, stream=False)
    payload: dict = {}
    for key in ("model", "max_tokens", "messages", "system"):
        if key in kwargs:
            payload[key] = kwargs[key]
    return payload


def normalize_model_name(model: str) -> str:
    cleaned = model.strip()
    if not cleaned:
        return cleaned

    if "/" in cleaned:
        provider, remainder = cleaned.split("/", 1)
        normalized_provider = provider.strip().lower()
        if normalized_provider in {"google", "google_ai_studio"}:
            normalized_provider = "gemini"
        return f"{normalized_provider}/{remainder.strip().lower()}"

    lowered = cleaned.lower()

    if lowered.startswith(("gpt-", "chatgpt-", "o1", "o3", "o4")):
        return f"openai/{lowered}"
    if lowered.startswith("claude-"):
        return f"anthropic/{lowered}"
    if lowered.startswith("gemini-"):
        return f"gemini/{lowered}"
    if lowered.startswith("grok-"):
        return f"xai/{lowered}"

    return lowered


async def stream_completion(
    model: str,
    api_key: str,
    messages: List[Dict[str, str]],
) -> AsyncIterator[str]:
    """Stream LLM completion, yielding text chunks."""
    provider, _ = _resolve_model_and_provider(model)
    if provider == "anthropic":
        payload = _build_completion_kwargs(model, api_key, messages, stream=True)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "content-type": "application/json",
        }
        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com").rstrip("/")
        url = f"{api_base}/v1/messages"

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code >= 400:
                    detail = await response.aread()
                    raise RuntimeError(
                        f"Anthropic API error {response.status_code}: {detail.decode('utf-8', errors='replace')[:1000]}"
                    )
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line[6:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        event = json.loads(raw)
                    except Exception:
                        continue
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            text = delta.get("text") or ""
                            if text:
                                yield text
        return

    kwargs = _build_completion_kwargs(model, api_key, messages, stream=True)
    response = await litellm.acompletion(**kwargs)
    async for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


async def complete(
    model: str,
    api_key: str,
    messages: List[Dict[str, str]],
) -> str:
    """Non-streaming LLM completion."""
    provider, _ = _resolve_model_and_provider(model)
    if provider == "anthropic":
        payload = _build_completion_kwargs(model, api_key, messages, stream=False)
        headers = {
            "x-api-key": api_key,
            "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01"),
            "content-type": "application/json",
        }
        api_base = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com").rstrip("/")
        url = f"{api_base}/v1/messages"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(
                    f"Anthropic API error {response.status_code}: {response.text[:1000]}"
                )
            data = response.json()

        content = data.get("content") or []
        text_parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text") or ""))
        return "".join(text_parts)

    kwargs = _build_completion_kwargs(model, api_key, messages, stream=False)
    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content or ""
