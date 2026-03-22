"""
MCP-inspired agent server.
Each agent exposes: search_memory, add_memory, generate_response.
"""
from typing import List, Dict, Any, AsyncIterator
import logging
from app.services.vector_store import search_memory, add_memory
from app.services.llm_service import complete, stream_completion, build_request_payload_preview
from app.database import AsyncSessionLocal
from app.services.llm_log_service import create_llm_log


logger = logging.getLogger(__name__)


class AgentMCPServer:
    """Represents an MCP server for a single agent."""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        model: str,
        api_key: str,
        session_id: str | None = None,
        owner_id: str | None = None,
        use_default_key: bool = False,
        credits_per_process: int = 1,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.model = model
        self.api_key = api_key
        self.session_id = session_id
        self.owner_id = owner_id
        self.use_default_key = use_default_key
        self.credits_per_process = credits_per_process

    def search_memory(self, query: str, n_results: int = 5) -> List[str]:
        """Retrieve relevant past interactions."""
        return search_memory(self.agent_id, query, n_results, session_id=self.session_id)

    def add_memory(self, text: str, metadata: dict = None):
        """Store text in the agent's vector database."""
        add_memory(self.agent_id, text, metadata, session_id=self.session_id)

    async def _log_llm_call(
        self,
        *,
        messages: List[Dict[str, str]],
        response_text: str | None = None,
        error: str | None = None,
    ):
        try:
            request_payload = build_request_payload_preview(self.model, messages)

            async with AsyncSessionLocal() as session:
                await create_llm_log(
                    session,
                    agent_id=self.agent_id,
                    agent_name=self.agent_name,
                    model=self.model,
                    request_payload=request_payload,
                    response_payload={"content": response_text} if response_text is not None else None,
                    error=error,
                )
        except Exception:
            logger.exception("Failed to persist LLM log for agent %s", self.agent_id)

    async def _deduct_credits(self) -> None:
        """Deduct credits for this LLM call if the agent uses the default key."""
        if not self.owner_id or not self.use_default_key or self.credits_per_process <= 0:
            return
        try:
            from app.services.user_service import deduct_credits_soft
            async with AsyncSessionLocal() as session:
                await deduct_credits_soft(session, self.owner_id, self.credits_per_process)
        except Exception:
            logger.exception("Failed to deduct credits for user %s", self.owner_id)

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a non-streaming response."""
        try:
            response_text = await complete(self.model, self.api_key, messages)
            await self._log_llm_call(messages=messages, response_text=response_text)
            await self._deduct_credits()
            return response_text
        except Exception as exc:
            await self._log_llm_call(messages=messages, error=str(exc))
            raise

    async def stream_response(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Generate a streaming response."""
        full_response = ""
        try:
            async for chunk in stream_completion(self.model, self.api_key, messages):
                full_response += chunk
                yield chunk
            await self._log_llm_call(messages=messages, response_text=full_response)
            await self._deduct_credits()
        except Exception as exc:
            await self._log_llm_call(messages=messages, response_text=full_response or None, error=str(exc))
            raise

    def build_messages_with_context(self, user_message: str, system_prompt: str = None) -> List[Dict[str, str]]:
        """Build messages list with RAG context injected."""
        past = self.search_memory(user_message, n_results=5)
        messages = []

        system_content = system_prompt or f"You are {self.agent_name}, an AI assistant."
        if past:
            context_str = "\n\n".join(past)
            system_content += f"\n\nRelevant past context:\n{context_str}"
        messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": user_message})
        return messages
