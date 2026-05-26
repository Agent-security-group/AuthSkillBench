from __future__ import annotations

import json
from typing import Any, Callable


class ToolCallingAgentRunner:
    """Scenario-agnostic OpenAI-style tool-calling runner."""

    def __init__(
        self,
        *,
        client: Any,
        tools: list[dict[str, Any]],
        invoke_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
        max_turns: int = 8,
    ) -> None:
        self.client = client
        self.tools = tools
        self.invoke_tool = invoke_tool
        self.max_turns = max_turns

    def run(
        self,
        messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
        return run_tool_calling_agent(
            client=self.client,
            messages=messages,
            tools=self.tools,
            invoke_tool=self.invoke_tool,
            max_turns=self.max_turns,
        )


def openai_tools_from_specs(tool_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for spec in tool_specs:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": spec["agent_name"],
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            }
        )
    return tools


def _message_from_choice(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not choices:
        raise RuntimeError(f"OpenAI response did not include choices: {response}")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError(f"OpenAI response did not include a message: {response}")
    return message


def _parse_tool_arguments(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("tool arguments must decode to a JSON object")
    return parsed


def run_tool_calling_agent(
    *,
    client: Any,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    invoke_tool: Callable[[str, dict[str, Any]], dict[str, Any]],
    max_turns: int = 8,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
    """Run an OpenAI-style tool-calling loop against a scenario API adapter."""

    conversation = list(messages)
    steps: list[dict[str, Any]] = []
    final_message: dict[str, Any] | None = None

    for turn_index in range(max_turns):
        response = client.create(messages=conversation, tools=tools)
        assistant_message = _message_from_choice(response)
        final_message = assistant_message
        conversation.append(assistant_message)
        steps.append(
            {
                "phase": "assistant_message",
                "turn_index": turn_index,
                "content": assistant_message.get("content"),
                "tool_call_count": len(assistant_message.get("tool_calls") or []),
            }
        )

        tool_calls = assistant_message.get("tool_calls") or []
        if not tool_calls:
            break

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            tool_name = str(function.get("name") or "")
            arguments = _parse_tool_arguments(function.get("arguments"))
            result = invoke_tool(tool_name, arguments)
            native_tool = result.get("tool", tool_name)
            steps.append(
                {
                    "phase": "agent_tool_call",
                    "turn_index": turn_index,
                    "tool_call_id": tool_call.get("id"),
                    "tool": native_tool,
                    "agent_tool_name": tool_name,
                    "arguments": arguments,
                    "result": result,
                }
            )
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": json.dumps(result, sort_keys=True),
                }
            )

    return steps, final_message, conversation
