from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Mount, Route

from mcp_atomictoolkit.mcp_server import mcp


class _PathRewriteApp:
    """ASGI adapter that rewrites incoming path before delegating."""

    def __init__(self, app, target_path: str = "/") -> None:
        self.app = app
        self.target_path = target_path

    async def __call__(self, scope, receive, send) -> None:
        rewritten_scope = dict(scope)
        rewritten_scope["path"] = self.target_path
        rewritten_scope["raw_path"] = self.target_path.encode("utf-8")
        await self.app(rewritten_scope, receive, send)


# Primary MCP endpoint expected by Smithery and most registries.
_mcp_root_app = mcp.http_app(
    path="/",
    transport="streamable-http",
    json_response=True,
    stateless_http=True,
)


def _public_base_url(request: Request) -> str:
    """Compute public base URL, honoring reverse-proxy headers."""
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}"
    return str(request.base_url).rstrip("/")


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
            "capabilities": {
                "tools": {"listChanged": True},
                "prompts": {"listChanged": True},
                "resources": {"listChanged": True, "subscribe": False},
            },
            "transports": [
                {
                    "type": "streamable-http",
                    "url": f"{base_url}/",
                },
                {
                    "type": "streamable-http",
                    "url": f"{base_url}/sse/",
                },
            ],
        }
    )


async def handle_sse_no_slash(request: Request):
    """Normalize /sse -> /sse/ so the mounted compatibility app handles it."""
    return RedirectResponse(url="/sse/", status_code=307)


app = Starlette(
    routes=[
        Route("/healthz", handle_healthz),
        Route("/.well-known/mcp/server-card.json", handle_server_card),
        Route("/sse", handle_sse_no_slash, methods=["GET", "HEAD", "POST", "DELETE"]),
        Mount("/sse", app=_PathRewriteApp(_mcp_root_app, target_path="/")),
        Mount("/", app=_mcp_root_app),
    ],
    lifespan=_mcp_root_app.lifespan,
)
