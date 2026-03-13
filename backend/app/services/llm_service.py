from typing import AsyncIterator, List, Dict, Any
import litellm


def normalize_model_name(model: str) -> str:
    cleaned = model.strip()
    if not cleaned:
        return cleaned

    if "/" in cleaned:
        provider, remainder = cleaned.split("/", 1)
        return f"{provider.strip().lower()}/{remainder.strip().lower()}"

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
    resolved_model = normalize_model_name(model)
    response = await litellm.acompletion(
        model=resolved_model,
        api_key=api_key,
        messages=messages,
        stream=True,
    )
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
    resolved_model = normalize_model_name(model)
    response = await litellm.acompletion(
        model=resolved_model,
        api_key=api_key,
        messages=messages,
        stream=False,
    )
    return response.choices[0].message.content or ""
