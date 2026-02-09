from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import mcp.types
from docket.execution import ExecutionState
from fastmcp import FastMCP
from fastmcp.server.dependencies import _current_docket, get_context
from fastmcp.server.tasks.converters import (
    convert_prompt_result,
    convert_resource_result,
    convert_tool_result,
)
from fastmcp.server.tasks.handlers import TASK_MAPPING_TTL_BUFFER_SECONDS
from fastmcp.server.tasks.keys import build_task_key, parse_task_key
from fastmcp.server.tasks.protocol import DOCKET_TO_MCP_STATE
from mcp.shared.exceptions import McpError
from mcp.types import CancelTaskResult, ErrorData, GetTaskResult, ListTasksResult, Task

DEFAULT_POLL_INTERVAL_MS = 1000


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    task_key: str
    created_at: datetime
    ttl_ms: Optional[int]


def apply_task_support_patches() -> None:
    """Patch FastMCP task handlers with MCP-compliant implementations."""
    import fastmcp.server.server as fastmcp_server
    import fastmcp.server.tasks.handlers as task_handlers
    import fastmcp.server.tasks.protocol as task_protocol

    task_handlers.handle_tool_as_task = handle_tool_as_task
    fastmcp_server.handle_tool_as_task = handle_tool_as_task
    task_protocol.tasks_get_handler = tasks_get_handler
    task_protocol.tasks_result_handler = tasks_result_handler
    task_protocol.tasks_list_handler = tasks_list_handler
    task_protocol.tasks_cancel_handler = tasks_cancel_handler


async def handle_tool_as_task(
    server: FastMCP,
    tool_name: str,
    arguments: dict[str, Any],
    task_meta: dict[str, Any],
) -> mcp.types.CallToolResult:
    """Handle tool execution as a background task with durable metadata."""
    from uuid import uuid4

    server_task_id = str(uuid4())
    created_at = datetime.now(timezone.utc)

    ctx = get_context()
    session_id = ctx.session_id

    docket = _current_docket.get()
    if docket is None:
        raise McpError(
            ErrorData(
                code=-32603,
                message="Background tasks require a running FastMCP server context",
            )
        )

    task_key = build_task_key(session_id, server_task_id, "tool", tool_name)
    tool = await server.get_tool(tool_name)

    ttl_seconds = None
    if docket.execution_ttl:
        ttl_seconds = int(
            docket.execution_ttl.total_seconds() + TASK_MAPPING_TTL_BUFFER_SECONDS
        )

    task_ttl_ms = task_meta.get("ttl") if task_meta else None

    await _store_task_metadata(
        docket,
        session_id=session_id,
        task_id=server_task_id,
        task_key=task_key,
        created_at=created_at,
        ttl_seconds=ttl_seconds,
        ttl_ms=task_ttl_ms,
    )

    notification = mcp.types.JSONRPCNotification(
        jsonrpc="2.0",
        method="notifications/tasks/created",
        params={},
        _meta={
            "modelcontextprotocol.io/related-task": {
                "taskId": server_task_id,
            }
        },
    )
    with suppress(Exception):
        await ctx.session.send_notification(notification)  # type: ignore[arg-type]

    await docket.add(
        tool.key,
        key=task_key,
    )(**arguments)

    return mcp.types.CallToolResult(
        content=[],
        _meta={
            "modelcontextprotocol.io/task": {
                "taskId": server_task_id,
                "status": "working",
            }
        },
    )


async def tasks_get_handler(server: FastMCP, params: dict[str, Any]) -> GetTaskResult:
    task_id = params.get("taskId")
    if not task_id:
        raise McpError(ErrorData(code=-32602, message="Missing required parameter: taskId"))

    ctx = get_context()
    docket = _current_docket.get()
    if docket is None:
        raise McpError(
            ErrorData(
                code=-32603,
                message="Background tasks require a running FastMCP server context",
            )
        )

    task_record = await _load_task_record(docket, ctx.session_id, task_id)
    execution = await docket.get_execution(task_record.task_key)
    if execution is None:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Task {task_id} execution not found",
            )
        )

    await execution.sync()
    status = DOCKET_TO_MCP_STATE.get(execution.state, "failed")
    status_message = _status_message_for_execution(execution)

    return GetTaskResult(
        taskId=task_id,
        status=status,  # type: ignore[arg-type]
        createdAt=task_record.created_at,
        lastUpdatedAt=datetime.now(timezone.utc),
        ttl=task_record.ttl_ms,
        pollInterval=DEFAULT_POLL_INTERVAL_MS,
        statusMessage=status_message,
    )


async def tasks_result_handler(server: FastMCP, params: dict[str, Any]) -> Any:
    task_id = params.get("taskId")
    if not task_id:
        raise McpError(ErrorData(code=-32602, message="Missing required parameter: taskId"))

    ctx = get_context()
    docket = _current_docket.get()
    if docket is None:
        raise McpError(
            ErrorData(
                code=-32603,
                message="Background tasks require a running FastMCP server context",
            )
        )

    task_record = await _load_task_record(docket, ctx.session_id, task_id)
    execution = await docket.get_execution(task_record.task_key)
    if execution is None:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Invalid taskId: {task_id} not found",
            )
        )

    await execution.sync()

    raw_value = None
    try:
        raw_value = await execution.get_result()
    except Exception as error:
        return mcp.types.CallToolResult(
            content=[mcp.types.TextContent(type="text", text=str(error))],
            isError=True,
            _meta={
                "modelcontextprotocol.io/related-task": {
                    "taskId": task_id,
                }
            },
        )

    key_parts = parse_task_key(task_record.task_key)
    task_type = key_parts["task_type"]

    if task_type == "tool":
        return await convert_tool_result(
            server, raw_value, key_parts["component_identifier"], task_id
        )
    if task_type == "prompt":
        return await convert_prompt_result(
            server, raw_value, key_parts["component_identifier"], task_id
        )
    if task_type == "resource":
        return await convert_resource_result(
            server, raw_value, key_parts["component_identifier"], task_id
        )

    raise McpError(
        ErrorData(
            code=-32603,
            message=f"Internal error: Unknown task type: {task_type}",
        )
    )


async def tasks_list_handler(server: FastMCP, params: dict[str, Any]) -> ListTasksResult:
    ctx = get_context()
    docket = _current_docket.get()
    if docket is None:
        raise McpError(
            ErrorData(
                code=-32603,
                message="Background tasks require a running FastMCP server context",
            )
        )

    try:
        limit = int(params.get("limit") or 50)
        cursor = params.get("cursor")
        offset = int(cursor) if cursor else 0
    except (TypeError, ValueError) as exc:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Invalid cursor or limit",
            )
        ) from exc

    if limit <= 0 or offset < 0:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Limit must be positive and cursor must be non-negative",
            )
        )

    tasks: list[Task] = []
    next_cursor = None

    async with docket.redis() as redis:
        index_key = docket.key(_task_index_key(ctx.session_id))
        total = await redis.zcard(index_key)
        if total:
            task_ids = await redis.zrange(index_key, offset, offset + limit - 1)
        else:
            task_ids = []

    if task_ids:
        for task_id_bytes in task_ids:
            task_id = _decode(task_id_bytes)
            try:
                task_record = await _load_task_record(docket, ctx.session_id, task_id)
            except McpError:
                continue

            execution = await docket.get_execution(task_record.task_key)
            if execution is None:
                continue

            await execution.sync()
            status = DOCKET_TO_MCP_STATE.get(execution.state, "failed")
            tasks.append(
                Task(
                    taskId=task_id,
                    status=status,  # type: ignore[arg-type]
                    createdAt=task_record.created_at,
                    lastUpdatedAt=datetime.now(timezone.utc),
                    ttl=task_record.ttl_ms,
                    pollInterval=DEFAULT_POLL_INTERVAL_MS,
                    statusMessage=_status_message_for_execution(execution),
                )
            )

    if total and offset + limit < total:
        next_cursor = str(offset + limit)

    return ListTasksResult(tasks=tasks, nextCursor=next_cursor)


async def tasks_cancel_handler(server: FastMCP, params: dict[str, Any]) -> CancelTaskResult:
    task_id = params.get("taskId")
    if not task_id:
        raise McpError(ErrorData(code=-32602, message="Missing required parameter: taskId"))

    ctx = get_context()
    docket = _current_docket.get()
    if docket is None:
        raise McpError(
            ErrorData(
                code=-32603,
                message="Background tasks require a running FastMCP server context",
            )
        )

    task_record = await _load_task_record(docket, ctx.session_id, task_id)
    execution = await docket.get_execution(task_record.task_key)
    if execution is None:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Invalid taskId: {task_id} not found",
            )
        )

    await execution.sync()
    if execution.state in {
        ExecutionState.COMPLETED,
        ExecutionState.FAILED,
        ExecutionState.CANCELLED,
    }:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Task {task_id} is already terminal",
            )
        )

    await docket.cancel(task_record.task_key)

    return CancelTaskResult(
        taskId=task_id,
        status="cancelled",
        createdAt=task_record.created_at,
        lastUpdatedAt=datetime.now(timezone.utc),
        ttl=task_record.ttl_ms,
        pollInterval=DEFAULT_POLL_INTERVAL_MS,
        statusMessage="Task cancelled",
    )


def _task_mapping_key(session_id: str, task_id: str) -> str:
    return f"fastmcp:task:{session_id}:{task_id}"


def _task_created_key(session_id: str, task_id: str) -> str:
    return f"fastmcp:task:{session_id}:{task_id}:created_at"


def _task_meta_key(session_id: str, task_id: str) -> str:
    return f"fastmcp:task:{session_id}:{task_id}:meta"


def _task_index_key(session_id: str) -> str:
    return f"fastmcp:tasks:{session_id}"


async def _store_task_metadata(
    docket,
    *,
    session_id: str,
    task_id: str,
    task_key: str,
    created_at: datetime,
    ttl_seconds: Optional[int],
    ttl_ms: Optional[int],
) -> None:
    async with docket.redis() as redis:
        await redis.set(
            docket.key(_task_mapping_key(session_id, task_id)),
            task_key,
            ex=ttl_seconds,
        )
        await redis.set(
            docket.key(_task_created_key(session_id, task_id)),
            created_at.isoformat(),
            ex=ttl_seconds,
        )
        if ttl_ms is not None:
            await redis.hset(
                docket.key(_task_meta_key(session_id, task_id)),
                mapping={"ttl_ms": ttl_ms},
            )
            if ttl_seconds:
                await redis.expire(
                    docket.key(_task_meta_key(session_id, task_id)),
                    ttl_seconds,
                )
        await redis.zadd(
            docket.key(_task_index_key(session_id)),
            {task_id: created_at.timestamp()},
        )
        if ttl_seconds:
            await redis.expire(docket.key(_task_index_key(session_id)), ttl_seconds)


async def _load_task_record(
    docket,
    session_id: str,
    task_id: str,
) -> TaskRecord:
    async with docket.redis() as redis:
        task_key_bytes = await redis.get(
            docket.key(_task_mapping_key(session_id, task_id))
        )
        created_at_bytes = await redis.get(
            docket.key(_task_created_key(session_id, task_id))
        )
        meta = await redis.hgetall(docket.key(_task_meta_key(session_id, task_id)))

    if task_key_bytes is None or created_at_bytes is None:
        raise McpError(
            ErrorData(
                code=-32602,
                message=f"Task {task_id} not found",
            )
        )

    created_at = datetime.fromisoformat(_decode(created_at_bytes))
    ttl_ms = None
    if meta:
        ttl_ms_raw = meta.get(b"ttl_ms") or meta.get("ttl_ms")
        if ttl_ms_raw is not None:
            ttl_ms = int(_decode(ttl_ms_raw))

    return TaskRecord(
        task_id=task_id,
        task_key=_decode(task_key_bytes),
        created_at=created_at,
        ttl_ms=ttl_ms,
    )


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _status_message_for_execution(execution) -> Optional[str]:
    if execution.state == ExecutionState.FAILED:
        return "Task failed"
    if execution.state == ExecutionState.CANCELLED:
        return "Task cancelled"
    if execution.progress and execution.progress.message:
        return execution.progress.message
    return None
