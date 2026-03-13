"""
Orchestrator service.

Two orchestrator modes:
- broadcast: sends user message to all slaves only when explicitly requested; otherwise replies directly.
- orchestrate: discovers agent specialities, plans a sequential execution, runs agents in order,
  then synthesises the final answer. Ignores agents with no relevant specialisation.

All system-prompt strings are loaded from the configurable PromptConfig store.
"""
import json
import re
from typing import AsyncIterator, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.agent_service import get_agent, decrypt_api_key, get_orchestrator_by_id
from app.services.settings_service import get_all_prompt_values, PROMPT_DEFAULTS
from app.mcp.agent_server import AgentMCPServer


logger = logging.getLogger(__name__)

SPECIALTY_MEMORY_PREFIX = "Agent specialty profile"
NO_ORCHESTRATOR_INSTRUCTIONS = "No explicit orchestrator instructions were provided. Acknowledge completion without adding extra interpretation."


def _make_server(agent, conversation_id: str | None = None) -> AgentMCPServer:
    return AgentMCPServer(
        agent_id=agent.id,
        agent_name=agent.name,
        model=agent.model,
        api_key=decrypt_api_key(agent.api_key_encrypted),
        session_id=conversation_id,
    )


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _sse_chunk(
    agent: str,
    content: str,
    *,
    message_type: str = "chat",
    group_key: str | None = None,
    processing_target: str | None = None,
    is_streaming: bool = False,
) -> str:
    payload: dict = {
        "agent": agent,
        "content": content,
        "done": False,
        "message_type": message_type,
    }
    if group_key:
        payload["group_key"] = group_key
    if processing_target:
        payload["processing_target"] = processing_target
    if is_streaming:
        payload["is_streaming"] = True
    return f"data: {json.dumps(payload)}\n\n"


def _specialty_memory_text(agent_name: str, specialty: str) -> str:
    return f"{SPECIALTY_MEMORY_PREFIX}: {agent_name}\nSpecialty: {specialty}"


def _extract_specialty_from_docs(agent_name: str, docs: list[str]) -> str | None:
    for doc in docs:
        if SPECIALTY_MEMORY_PREFIX not in doc or agent_name not in doc:
            continue
        match = re.search(r"Specialty:\s*(.+)", doc, re.DOTALL)
        if match:
            specialty = match.group(1).strip()
            if specialty:
                return specialty
    return None


def _parse_planned_names(plan_text: str, available_names: list[str]) -> list[str]:
    try:
        json_match = re.search(r"\[.*?\]", plan_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                return [str(name) for name in parsed if str(name) in available_names]
    except Exception:
        logger.warning("Failed to parse orchestrator plan JSON", exc_info=True)

    lowered = plan_text.lower()
    matched = [name for name in available_names if name.lower() in lowered]
    return matched


def _format_llm_messages(messages: list[dict[str, str]]) -> str:
    parts: list[str] = []
    for index, message in enumerate(messages, start=1):
        role = str(message.get("role", "unknown")).upper()
        content = str(message.get("content", "")).strip()
        parts.append(f"[{index}] {role}\n{content}")
    return "\n\n".join(parts)


def _prompt_sent_chunk(
    agent: str,
    messages: list[dict[str, str]],
    *,
    group_key: str,
    processing_target: str,
    model: str,
) -> str:
    return _sse_chunk(
        agent,
        f"Prompt sent to model {model}:\n\n{_format_llm_messages(messages)}",
        message_type="internal",
        group_key=group_key,
        processing_target=processing_target,
    )


# ---------------------------------------------------------------------------
# Slave-mode broadcast (triggered explicitly from the UI via mode='slave')
# ---------------------------------------------------------------------------

async def handle_slave_broadcast(
    db: AsyncSession,
    orchestrator_id: str,
    conversation_id: str,
    user_message: str,
    slave_agent_ids: List[str],
) -> AsyncIterator[str]:
    """
    Explicit slave-mode broadcast: called when the user selects mode='slave'.
    Sends the user message directly to each selected slave agent.
    """
    try:
        orchestrator = await get_orchestrator_by_id(db, orchestrator_id)
    except Exception as exc:
        logger.exception("Failed to load orchestrator %s in slave broadcast", orchestrator_id)
        yield _sse_chunk("system", f"Orchestrator error: {exc}")
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    orch_server = _make_server(orchestrator, conversation_id)
    prompt_values = await get_all_prompt_values(db)

    def _p(key: str) -> str:
        return prompt_values.get(key, PROMPT_DEFAULTS.get(key, {}).get("value", ""))

    slave_prompt_template = _p("broadcast_slave_system_prompt")
    responses: dict[str, str] = {}

    for agent_id in slave_agent_ids:
        try:
            agent = await get_agent(db, agent_id)
        except Exception:
            logger.warning("Skipping unavailable slave agent %s", agent_id)
            continue

        server = _make_server(agent, conversation_id)
        slave_system = slave_prompt_template.format(
            agent_name=agent.name,
            purpose=agent.purpose or "Not provided",
            instructions=agent.instructions or "None provided.",
        )
        messages = server.build_messages_with_context(user_message, system_prompt=slave_system)
        yield _prompt_sent_chunk(
            f"{orchestrator.name} -> {agent.name}",
            messages,
            group_key=f"broadcast:{agent.id}:prompt",
            processing_target=agent.name,
            model=agent.model,
        )

        try:
            response_text = ""
            async for chunk in server.stream_response(messages):
                response_text += chunk
                yield _sse_chunk(
                    agent.name,
                    chunk,
                    message_type="internal",
                    group_key=f"broadcast:{agent.id}",
                    processing_target=agent.name,
                    is_streaming=True,
                )
        except Exception:
            logger.exception("Slave agent generation failed for %s (%s)", agent.name, agent.id)
            yield _sse_chunk("system", f"{agent.name} failed to respond.")
            continue

        responses[agent.name] = response_text
        server.add_memory(
            f"User: {user_message}\nAssistant: {response_text}",
            metadata={"role": "exchange"},
        )

    agg = "\n\n".join(f"[{name}]: {resp}" for name, resp in responses.items())
    orch_server.add_memory(
        f"User broadcast: {user_message}\nAgents responses:\n{agg}",
        metadata={"role": "broadcast_summary"},
    )
    yield f"data: {json.dumps({'done': True})}\n\n"


# ---------------------------------------------------------------------------
# Broadcast orchestrator (orchestrator_mode='broadcast', mode='orchestrator')
# ---------------------------------------------------------------------------

async def _handle_broadcast_orchestrator(
    db: AsyncSession,
    orchestrator,
    orch_server: AgentMCPServer,
    user_message: str,
    slave_agent_ids: List[str],
    prompt_fn,
    *,
    conversation_id: str,
    broadcast_instructions: str | None = None,
    orchestrator_instructions: str | None = None,
) -> AsyncIterator[str]:
    """
    Broadcast orchestrator:
    - Broadcasts whenever Broadcast instructions are provided.
    - If not: replies directly using the orchestrator own capabilities.
    - If yes: sends the broadcast instructions to all slaves, then synthesises the responses.
    """
    shared_broadcast_instructions = _strip_or_none(broadcast_instructions)
    private_orchestrator_instructions = _strip_or_none(orchestrator_instructions)

    wants_broadcast = bool(slave_agent_ids) and bool(shared_broadcast_instructions)

    orchestrator_request = private_orchestrator_instructions or user_message
    if wants_broadcast and not private_orchestrator_instructions:
        orchestrator_request = NO_ORCHESTRATOR_INSTRUCTIONS

    slave_user_message = shared_broadcast_instructions or user_message

    if not wants_broadcast:
        direct_system = (
            f"You are {orchestrator.name}. "
            f"Purpose: {orchestrator.purpose or 'Not provided'}. "
            f"Behaviour instructions: {orchestrator.instructions or 'None provided.'} "
            "No Broadcast instructions were provided, so answer directly."
        )
        messages = [
            {"role": "system", "content": direct_system},
            {"role": "user", "content": orchestrator_request},
        ]
        yield _prompt_sent_chunk(
            f"{orchestrator.name} · Final Prompt",
            messages,
            group_key=f"final:{orchestrator.id}:prompt",
            processing_target=orchestrator.name,
            model=orchestrator.model,
        )
        full_response = ""
        try:
            async for chunk in orch_server.stream_response(messages):
                full_response += chunk
                yield _sse_chunk(
                    orchestrator.name,
                    chunk,
                    group_key=f"final:{orchestrator.id}",
                    processing_target=orchestrator.name,
                    is_streaming=True,
                )
        except Exception:
            logger.exception("Broadcast orchestrator direct response failed for %s", orchestrator.id)
            yield _sse_chunk("system", "The orchestrator failed while generating a response.")

        orch_server.add_memory(
            f"User: {orchestrator_request}\nOrchestrator: {full_response}",
            metadata={"role": "orchestrator_exchange"},
        )
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    # --- broadcast to all slaves ---
    slave_prompt_template = prompt_fn("broadcast_slave_system_prompt")
    responses: dict[str, str] = {}

    for agent_id in slave_agent_ids:
        try:
            agent = await get_agent(db, agent_id)
        except Exception:
            logger.warning("Skipping unavailable slave agent %s", agent_id)
            continue

        server = _make_server(agent, conversation_id)
        slave_system = slave_prompt_template.format(
            agent_name=agent.name,
            purpose=agent.purpose or "Not provided",
            instructions=agent.instructions or "None provided.",
        )
        messages = server.build_messages_with_context(slave_user_message, system_prompt=slave_system)

        yield _prompt_sent_chunk(
            f"{orchestrator.name} -> {agent.name}",
            messages,
            group_key=f"broadcast:{agent.id}:prompt",
            processing_target=agent.name,
            model=agent.model,
        )

        try:
            response_text = ""
            async for chunk in server.stream_response(messages):
                response_text += chunk
                yield _sse_chunk(
                    agent.name,
                    chunk,
                    message_type="internal",
                    group_key=f"broadcast:{agent.id}",
                    processing_target=agent.name,
                    is_streaming=True,
                )
        except Exception:
            logger.exception("Slave agent generation failed for %s (%s)", agent.name, agent.id)
            yield _sse_chunk("system", f"{agent.name} failed to respond.")
            continue

        responses[agent.name] = response_text
        server.add_memory(
            f"Broadcast instructions: {slave_user_message}\nAssistant: {response_text}",
            metadata={"role": "exchange"},
        )

    if not responses:
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    # --- orchestrator aggregates ---
    agg = "\n\n".join(f"[{name}]:\n{resp}" for name, resp in responses.items())
    aggregation_system = prompt_fn("broadcast_aggregation_system_prompt").format(
        orchestrator_name=orchestrator.name,
        purpose=orchestrator.purpose or "Not provided",
        instructions=orchestrator.instructions or "None provided.",
    )
    aggregation_messages = [
        {"role": "system", "content": aggregation_system},
        {
            "role": "user",
            "content": (
                f"Orchestrator instructions: {orchestrator_request}\n\n"
                f"Broadcast instructions sent to slaves: {slave_user_message}\n\n"
                f"Agent responses:\n{agg}\n\n"
                "You are aware of the broadcast instructions sent to the slaves, but your reply must address only the orchestrator instructions."
            ),
        },
    ]
    yield _prompt_sent_chunk(
        f"{orchestrator.name} · Aggregation Prompt",
        aggregation_messages,
        group_key=f"final:{orchestrator.id}:prompt",
        processing_target=orchestrator.name,
        model=orchestrator.model,
    )
    full_response = ""
    try:
        async for chunk in orch_server.stream_response(aggregation_messages):
            full_response += chunk
            yield _sse_chunk(
                orchestrator.name,
                chunk,
                group_key=f"final:{orchestrator.id}",
                processing_target=orchestrator.name,
                is_streaming=True,
            )
    except Exception:
        logger.exception("Broadcast orchestrator aggregation failed for %s", orchestrator.id)
        yield _sse_chunk("system", "Aggregation step failed.")

    orch_server.add_memory(
        (
            f"Broadcast instructions: {slave_user_message}\n"
            f"Orchestrator instructions: {orchestrator_request}\n"
            f"Agents responses:\n{agg}\nFinal: {full_response}"
        ),
        metadata={"role": "broadcast_summary"},
    )
    yield f"data: {json.dumps({'done': True})}\n\n"


# ---------------------------------------------------------------------------
# Orchestrate orchestrator (orchestrator_mode='orchestrate', mode='orchestrator')
# ---------------------------------------------------------------------------

async def _handle_orchestrate_orchestrator(
    db: AsyncSession,
    orchestrator,
    orch_server: AgentMCPServer,
    user_message: str,
    slave_agent_ids: List[str],
    prompt_fn,
    *,
    conversation_id: str,
) -> AsyncIterator[str]:
    """
    Orchestrate orchestrator:
    1. Discovery - asks each slave their specialisation.
    2. Planning - orchestrator decides which agents to use and in what order (JSON array).
    3. Sequential execution - calls agents in plan order; each output feeds into the next.
    4. Final synthesis - orchestrator produces the definitive answer.
    Agents that report no relevant specialisation are excluded from the plan.
    """
    orchestrator_system = prompt_fn("orchestrate_orchestrator_system_prompt").format(
        orchestrator_name=orchestrator.name,
        purpose=orchestrator.purpose or "Coordinate specialists to solve user tasks",
        instructions=orchestrator.instructions or "None provided.",
    )

    # ---- Phase 1: Discovery ----
    specialities: dict[str, str] = {}
    name_to_id: dict[str, str] = {}

    if slave_agent_ids:
        speciality_query = prompt_fn("orchestrate_speciality_query")

        for agent_id in slave_agent_ids:
            try:
                agent = await get_agent(db, agent_id)
            except Exception:
                logger.warning("Skipping unavailable agent %s in discovery", agent_id)
                continue
            if agent.agent_type != "slave":
                continue

            name_to_id[agent.name] = agent_id

            cached_specialty = _extract_specialty_from_docs(
                agent.name,
                orch_server.search_memory(f"{SPECIALTY_MEMORY_PREFIX} {agent.name}", n_results=5),
            )
            if cached_specialty:
                specialities[agent.name] = cached_specialty
                yield _sse_chunk(
                    orchestrator.name,
                    f"Using cached specialty for {agent.name}: {cached_specialty}",
                    message_type="internal",
                    group_key=f"discovery:{agent_id}:cached",
                    processing_target=orchestrator.name,
                )
                continue

            server = _make_server(agent, conversation_id)
            spec_messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are {agent.name}. "
                        f"Purpose: {agent.purpose or 'Not provided'}. "
                        f"Instructions: {agent.instructions or 'None provided.'}"
                    ),
                },
                {"role": "user", "content": speciality_query},
            ]

            yield _prompt_sent_chunk(
                f"{orchestrator.name} -> {agent.name}",
                spec_messages,
                group_key=f"discovery:{agent_id}:prompt",
                processing_target=agent.name,
                model=agent.model,
            )
            spec_text = ""
            try:
                async for chunk in server.stream_response(spec_messages):
                    spec_text += chunk
                    yield _sse_chunk(
                        f"{agent.name} -> {orchestrator.name}",
                        chunk,
                        message_type="internal",
                        group_key=f"discovery:{agent_id}:response",
                        processing_target=agent.name,
                        is_streaming=True,
                    )
            except Exception:
                logger.exception("Speciality query failed for %s (%s)", agent.name, agent_id)
                continue

            specialities[agent.name] = spec_text
            orch_server.add_memory(
                _specialty_memory_text(agent.name, spec_text),
                metadata={"role": "agent_specialty", "agent_name": agent.name},
            )

    # ---- Phase 2: Planning ----
    plan_ids: list[str] = []

    if specialities:
        spec_summary = "\n".join(f"- {name}: {spec}" for name, spec in specialities.items())
        plan_request = prompt_fn("orchestrate_plan_request")
        plan_messages = [
            {"role": "system", "content": orchestrator_system},
            {
                "role": "user",
                "content": (
                    f"User request: {user_message}\n\n"
                    f"Agent specialisations:\n{spec_summary}\n\n"
                    f"{plan_request}"
                ),
            },
        ]
        yield _prompt_sent_chunk(
            f"{orchestrator.name} · Planning",
            plan_messages,
            group_key=f"plan:{orchestrator.id}:prompt",
            processing_target=orchestrator.name,
            model=orchestrator.model,
        )
        plan_text = ""
        try:
            async for chunk in orch_server.stream_response(plan_messages):
                plan_text += chunk
                yield _sse_chunk(
                    f"{orchestrator.name} · Planning",
                    chunk,
                    message_type="internal",
                    group_key=f"plan:{orchestrator.id}:stream",
                    processing_target=orchestrator.name,
                    is_streaming=True,
                )
        except Exception:
            logger.exception("Planning step failed for orchestrator %s", orchestrator.id)

        planned_names = _parse_planned_names(plan_text, list(specialities.keys()))

        plan_display = ", ".join(planned_names) if planned_names else "No relevant agents"
        yield _sse_chunk(
            orchestrator.name,
            f"Execution plan: {plan_display}",
            message_type="internal",
            group_key=f"plan:{orchestrator.id}",
            processing_target=orchestrator.name,
        )

        plan_ids = [name_to_id[n] for n in planned_names if n in name_to_id]

    if not plan_ids and specialities:
        yield _sse_chunk(
            orchestrator.name,
            "No slave specialties were needed for this request. Responding directly.",
            message_type="internal",
            group_key=f"plan:{orchestrator.id}:none-needed",
            processing_target=orchestrator.name,
        )

    # ---- Phase 3: Sequential execution ----
    running_output = ""
    slave_task_template = prompt_fn("orchestrate_slave_task_system_prompt")

    for agent_id in plan_ids:
        try:
            agent = await get_agent(db, agent_id)
        except Exception:
            logger.warning("Skipping unavailable agent %s in execution", agent_id)
            continue

        server = _make_server(agent, conversation_id)
        slave_system = slave_task_template.format(
            agent_name=agent.name,
            purpose=agent.purpose or "Not provided",
            instructions=agent.instructions or "None provided.",
        )
        task_message = user_message
        if running_output:
            task_message += f"\n\nPrevious agent outputs:\n{running_output}"

        task_msgs = [
            {"role": "system", "content": slave_system},
            {"role": "user", "content": task_message},
        ]

        yield _prompt_sent_chunk(
            f"{orchestrator.name} -> {agent.name}",
            task_msgs,
            group_key=f"task:{agent_id}:prompt",
            processing_target=agent.name,
            model=agent.model,
        )
        resp = ""
        try:
            async for chunk in server.stream_response(task_msgs):
                resp += chunk
                yield _sse_chunk(
                    f"{agent.name} -> {orchestrator.name}",
                    chunk,
                    message_type="internal",
                    group_key=f"task:{agent_id}:response",
                    processing_target=agent.name,
                    is_streaming=True,
                )
        except Exception:
            logger.exception("Task execution failed for %s (%s)", agent.name, agent_id)
            continue

        running_output += f"\n[{agent.name}]: {resp}"
        server.add_memory(
            f"User request: {user_message}\nOutput: {resp}",
            metadata={"role": "orchestrator_delegation"},
        )

    # ---- Phase 4: Final synthesis ----
    if running_output:
        orchestrator_system += f"\n\nAgent execution outputs:{running_output}"

    final_synthesis = prompt_fn("orchestrate_final_synthesis_prompt")
    final_user_content = (
        f"{user_message}\n\n{final_synthesis}" if plan_ids else user_message
    )
    final_messages = [
        {"role": "system", "content": orchestrator_system},
        {"role": "user", "content": final_user_content},
    ]

    yield _prompt_sent_chunk(
        f"{orchestrator.name} · Final Prompt",
        final_messages,
        group_key=f"final:{orchestrator.id}:prompt",
        processing_target=orchestrator.name,
        model=orchestrator.model,
    )

    full_response = ""
    agent_label = f"{orchestrator.name} · Final" if plan_ids else orchestrator.name
    try:
        async for chunk in orch_server.stream_response(final_messages):
            full_response += chunk
            yield _sse_chunk(
                agent_label,
                chunk,
                group_key=f"final:{orchestrator.id}",
                processing_target=orchestrator.name,
                is_streaming=True,
            )
    except Exception:
        logger.exception("Final synthesis failed for orchestrator %s", orchestrator.id)
        yield _sse_chunk("system", "The orchestrator failed while generating a final response.")
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    orch_server.add_memory(
        f"User: {user_message}\nOrchestrator: {full_response}",
        metadata={"role": "orchestrator_exchange"},
    )
    yield f"data: {json.dumps({'done': True})}\n\n"


# ---------------------------------------------------------------------------
# Public entry point for mode='orchestrator'
# ---------------------------------------------------------------------------

async def handle_orchestrator_mode(
    db: AsyncSession,
    orchestrator_id: str,
    conversation_id: str,
    user_message: str,
    slave_agent_ids: Optional[List[str]] = None,
    iterations: int = 1,
    broadcast_instructions: str | None = None,
    orchestrator_instructions: str | None = None,
) -> AsyncIterator[str]:
    """
    Entry point for orchestrator mode.
    Dispatches to broadcast or orchestrate handler based on orchestrator.orchestrator_mode.
    The iterations parameter is kept for API compatibility but is not used in the new flow.
    """
    try:
        orchestrator = await get_orchestrator_by_id(db, orchestrator_id)
    except Exception as exc:
        logger.exception("Failed to load orchestrator %s", orchestrator_id)
        yield _sse_chunk("system", f"Orchestrator error: {exc}")
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    orch_server = _make_server(orchestrator, conversation_id)

    prompt_values = await get_all_prompt_values(db)

    def _p(key: str) -> str:
        return prompt_values.get(key, PROMPT_DEFAULTS.get(key, {}).get("value", ""))

    candidate_ids = (
        slave_agent_ids if slave_agent_ids is not None else orchestrator.allowed_slave_ids
    )

    if orchestrator.orchestrator_mode == "broadcast":
        async for chunk in _handle_broadcast_orchestrator(
            db,
            orchestrator,
            orch_server,
            user_message,
            candidate_ids,
            _p,
            conversation_id=conversation_id,
            broadcast_instructions=broadcast_instructions,
            orchestrator_instructions=orchestrator_instructions,
        ):
            yield chunk
    else:
        async for chunk in _handle_orchestrate_orchestrator(
            db,
            orchestrator,
            orch_server,
            user_message,
            candidate_ids,
            _p,
            conversation_id=conversation_id,
        ):
            yield chunk
