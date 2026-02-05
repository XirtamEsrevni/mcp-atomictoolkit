from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_atomictoolkit.mcp_server import mcp


app = mcp.http_app(path="/sse", transport="sse")


def _public_base_url(request: Request) -> str:
    """Compute public base URL, honoring reverse-proxy headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


async def handle_root(request: Request) -> JSONResponse:
    base_url = _public_base_url(request)
    return JSONResponse(
        {
            "name": "atomictoolkit",
            "status": "ok",
            "mcp_sse_url": f"{base_url}/sse",
            "server_card_url": f"{base_url}/.well-known/mcp/server-card.json",
        }
    )


async def handle_healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


async def handle_server_card(request: Request) -> JSONResponse:
    """Serve MCP server-card for directory scanners (e.g., Smithery)."""
    base_url = _public_base_url(request)
    return JSONResponse(
        {
            "name": "atomictoolkit",
            "description": "Atomistic simulation MCP server powered by ASE and MLIPs.",
            "version": "0.1.0",
            "transports": [
                {
                    "type": "sse",
                    "url": f"{base_url}/sse",
                }
            ],
        }
    )


app.add_route("/", handle_root)
app.add_route("/healthz", handle_healthz)
app.add_route("/.well-known/mcp/server-card.json", handle_server_card)
