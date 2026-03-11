from typing import AsyncIterator, List, Dict, Any
import litellm


async def stream_completion(
    model: str,
    api_key: str,
    messages: List[Dict[str, str]],
) -> AsyncIterator[str]:
    """Stream LLM completion, yielding text chunks."""
    response = await litellm.acompletion(
        model=model,
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
    response = await litellm.acompletion(
        model=model,
        api_key=api_key,
        messages=messages,
        stream=False,
    )
    return response.choices[0].message.content or ""
