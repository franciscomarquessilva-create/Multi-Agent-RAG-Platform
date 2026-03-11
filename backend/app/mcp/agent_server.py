"""
MCP-inspired agent server.
Each agent exposes: search_memory, add_memory, generate_response.
"""
from typing import List, Dict, Any, AsyncIterator
from app.services.vector_store import search_memory, add_memory
from app.services.llm_service import complete, stream_completion


class AgentMCPServer:
    """Represents an MCP server for a single agent."""

    def __init__(self, agent_id: str, agent_name: str, model: str, api_key: str):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.model = model
        self.api_key = api_key

    def search_memory(self, query: str, n_results: int = 5) -> List[str]:
        """Retrieve relevant past interactions."""
        return search_memory(self.agent_id, query, n_results)

    def add_memory(self, text: str, metadata: dict = None):
        """Store text in the agent's vector database."""
        add_memory(self.agent_id, text, metadata)

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """Generate a non-streaming response."""
        return await complete(self.model, self.api_key, messages)

    async def stream_response(self, messages: List[Dict[str, str]]) -> AsyncIterator[str]:
        """Generate a streaming response."""
        async for chunk in stream_completion(self.model, self.api_key, messages):
            yield chunk

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
