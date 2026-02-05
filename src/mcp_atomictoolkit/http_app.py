from __future__ import annotations

from starlette.responses import JSONResponse

from mcp_atomictoolkit.mcp_server import mcp


app = mcp.http_app(path="/sse", transport="sse")


async def handle_healthz(request):
    return JSONResponse({"status": "ok"})


app.add_route("/healthz", handle_healthz)
