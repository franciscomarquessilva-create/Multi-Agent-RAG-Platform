"""
Orchestrator service.
Handles routing between orchestrator mode and slave broadcast mode.
"""
import json
from typing import AsyncIterator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent_service import get_orchestrator, get_agent, decrypt_api_key
from app.mcp.agent_server import AgentMCPServer


def _make_server(agent) -> AgentMCPServer:
    return AgentMCPServer(
        agent_id=agent.id,
        agent_name=agent.name,
        model=agent.model,
        api_key=decrypt_api_key(agent.api_key_encrypted),
    )


async def handle_slave_broadcast(
    db: AsyncSession,
    user_message: str,
    slave_agent_ids: List[str],
) -> AsyncIterator[str]:
    """
    Broadcast the user message to each slave agent.
    Yields SSE-formatted chunks.
    For each slave agent: retrieve context -> call LLM -> store memory.
    Then store aggregated result in orchestrator memory.
    """
    orchestrator = await get_orchestrator(db)
    orch_server = _make_server(orchestrator)

    responses: dict[str, str] = {}

    for agent_id in slave_agent_ids:
        try:
            agent = await get_agent(db, agent_id)
        except Exception:
            continue

        server = _make_server(agent)
        messages = server.build_messages_with_context(user_message)

        response_text = await server.generate_response(messages)
        responses[agent.name] = response_text

        # Store in slave agent memory
        server.add_memory(
            f"User: {user_message}\nAssistant: {response_text}",
            metadata={"role": "exchange"},
        )

        # Yield per-agent response as SSE event
        payload = json.dumps({"agent": agent.name, "content": response_text, "done": False})
        yield f"data: {payload}\n\n"

    # Store aggregated in orchestrator memory
    agg = "\n\n".join(f"[{name}]: {resp}" for name, resp in responses.items())
    orch_server.add_memory(
        f"User broadcast: {user_message}\nAgents responses:\n{agg}",
        metadata={"role": "broadcast_summary"},
    )

    # Final done event
    yield f"data: {json.dumps({'done': True})}\n\n"


async def handle_orchestrator_mode(
    db: AsyncSession,
    user_message: str,
    slave_agent_ids: Optional[List[str]] = None,
) -> AsyncIterator[str]:
    """
    Orchestrator resolves the request.
    May internally query slave agents for sub-tasks.
    Yields SSE-formatted chunks.
    """
    orchestrator = await get_orchestrator(db)
    orch_server = _make_server(orchestrator)

    # Build context for orchestrator
    past = orch_server.search_memory(user_message)
    system_prompt = (
        f"You are {orchestrator.name}, the main orchestrator AI assistant. "
        "You coordinate multiple AI agents to help users with complex tasks. "
        "Answer the user's question directly or delegate to agents as needed."
    )
    if past:
        system_prompt += f"\n\nYour past context:\n" + "\n\n".join(past)

    # If slave agents are available, gather their input first
    slave_context = ""
    if slave_agent_ids:
        for agent_id in slave_agent_ids:
            try:
                agent = await get_agent(db, agent_id)
            except Exception:
                continue
            server = _make_server(agent)
            msgs = server.build_messages_with_context(
                user_message,
                system_prompt=f"You are {agent.name}. Provide a concise analysis.",
            )
            resp = await server.generate_response(msgs)
            slave_context += f"\n[{agent.name} analysis]: {resp}"
            server.add_memory(
                f"User (via orchestrator): {user_message}\nMy analysis: {resp}",
                metadata={"role": "orchestrator_delegation"},
            )

    if slave_context:
        system_prompt += f"\n\nInput from your agents:{slave_context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    full_response = ""
    async for chunk in orch_server.stream_response(messages):
        full_response += chunk
        payload = json.dumps({"agent": orchestrator.name, "content": chunk, "done": False})
        yield f"data: {payload}\n\n"

    # Store in orchestrator memory
    orch_server.add_memory(
        f"User: {user_message}\nOrchestrator: {full_response}",
        metadata={"role": "orchestrator_exchange"},
    )

    yield f"data: {json.dumps({'done': True})}\n\n"
