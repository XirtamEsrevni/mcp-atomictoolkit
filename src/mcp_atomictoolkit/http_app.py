from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from fastmcp.server import SseServerTransport

from mcp_atomictoolkit.mcp_server import mcp


sse = SseServerTransport("/messages")


async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp._mcp_server.run(
            streams[0],
            streams[1],
            mcp._mcp_server.create_initialization_options(),
        )


async def handle_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)


async def handle_healthz(request):
    return JSONResponse({"status": "ok"})


app = Starlette(
    debug=mcp.settings.debug,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
        Route("/healthz", endpoint=handle_healthz),
    ],
)
