import asyncio

import pytest

fastmcp = pytest.importorskip("fastmcp")

from fastmcp import FastMCP
from fastmcp.server.context import Context
from fastmcp.server.tasks import TaskConfig
from mcp.server.experimental.request_context import Experimental
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError

from mcp_atomictoolkit.task_support import (
    apply_task_support_patches,
    handle_tool_as_task,
    tasks_cancel_handler,
    tasks_get_handler,
    tasks_list_handler,
    tasks_result_handler,
)


class _DummySession:
    def __init__(self, session_id: str) -> None:
        self._fastmcp_id = session_id
        self.notifications: list[object] = []

    async def send_notification(self, notification) -> None:
        self.notifications.append(notification)


def _build_request_context(session_id: str) -> tuple[RequestContext, _DummySession]:
    session = _DummySession(session_id)
    context = RequestContext(
        request_id="req-1",
        meta=None,
        session=session,
        lifespan_context=None,
        experimental=Experimental(),
        request=None,
    )
    return context, session


def test_task_flow_end_to_end() -> None:
    async def _run() -> None:
        apply_task_support_patches()
        server = FastMCP("test", tasks=True)

        @server.tool(task=TaskConfig(mode="required"))
        async def long_tool(value: int) -> dict:
            return {"value": value * 2}

        request_context, _session = _build_request_context("session-1")
        token = request_ctx.set(request_context)
        try:
            async with server._docket_lifespan():
                async with Context(fastmcp=server):
                    create_result = await handle_tool_as_task(
                        server,
                        "long_tool",
                        {"value": 3},
                        {"ttl": 60_000},
                    )
                    task_meta = create_result.meta["modelcontextprotocol.io/task"]
                    task_id = task_meta["taskId"]

                    status = await tasks_get_handler(server, {"taskId": task_id})
                    assert status.taskId == task_id
                    assert status.ttl == 60_000

                    list_result = await tasks_list_handler(server, {"limit": 5})
                    assert any(task.taskId == task_id for task in list_result.tasks)

                    result = await tasks_result_handler(server, {"taskId": task_id})
                    assert result.structuredContent == {"value": 6}
                    assert result.meta["modelcontextprotocol.io/related-task"]["taskId"] == task_id

                    with pytest.raises(McpError) as exc:
                        await tasks_cancel_handler(server, {"taskId": task_id})
                    assert exc.value.error.code == -32602
        finally:
            request_ctx.reset(token)

    asyncio.run(_run())


def test_tasks_list_rejects_invalid_pagination() -> None:
    async def _run() -> None:
        apply_task_support_patches()
        server = FastMCP("test", tasks=True)

        request_context, _session = _build_request_context("session-2")
        token = request_ctx.set(request_context)
        try:
            async with server._docket_lifespan():
                async with Context(fastmcp=server):
                    with pytest.raises(McpError) as exc:
                        await tasks_list_handler(server, {"limit": "bad"})
                    assert exc.value.error.code == -32602

                    with pytest.raises(McpError) as exc:
                        await tasks_list_handler(server, {"cursor": "-1"})
                    assert exc.value.error.code == -32602
        finally:
            request_ctx.reset(token)

    asyncio.run(_run())
