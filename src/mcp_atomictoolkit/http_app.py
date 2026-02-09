from __future__ import annotations

import os

os.environ.setdefault("JAX_PLUGINS", "")
os.environ.setdefault("JAX_SKIP_JAXLIB_PJRT_CUDA_PLUGIN", "1")
os.environ.setdefault("JAX_SKIP_JAXLIB_PJRT_ROCM_PLUGIN", "1")
os.environ.setdefault("JAX_PLATFORMS", "cpu")
os.environ.setdefault("JAX_PLATFORM_NAME", "cpu")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
os.environ.setdefault("JAX_CUDA_VISIBLE_DEVICES", "")

from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route

from mcp_atomictoolkit.artifact_store import artifact_store, reset_request_base_url, set_request_base_url
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


class _ArtifactBaseUrlContextApp:
    """ASGI adapter that sets request-scoped artifact base URLs."""

    def __init__(self, app) -> None:
        self.app = app
        self.lifespan = getattr(app, "lifespan", None)

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        forwarded_proto = headers.get("x-forwarded-proto")
        forwarded_host = headers.get("x-forwarded-host")

        if forwarded_proto and forwarded_host:
            base_url = f"{forwarded_proto}://{forwarded_host}"
        else:
            host = headers.get("host", "localhost")
            scheme = scope.get("scheme", "http")
            base_url = f"{scheme}://{host}"

        token = set_request_base_url(base_url)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_base_url(token)


class _AcceptHeaderCompatApp:
    """ASGI adapter that tolerates MCP scanners with missing Accept headers.

    Some directory scanners POST JSON-RPC requests without an explicit
    ``Accept`` header. FastMCP's Streamable HTTP transport rejects those
    requests with ``406 Not Acceptable``. To improve interoperability, we
    synthesize an MCP-compatible Accept value when it is absent.
    """

    _required_accept = b"application/json, text/event-stream"

    def __init__(self, app) -> None:
        self.app = app
        self.lifespan = getattr(app, "lifespan", None)

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http":
            raw_headers = list(scope.get("headers", []))
            accept_idx = next(
                (idx for idx, (name, _) in enumerate(raw_headers) if name.lower() == b"accept"),
                None,
            )
            should_rewrite = accept_idx is None
            if accept_idx is not None:
                accept_value = raw_headers[accept_idx][1].decode("latin-1").lower()
                should_rewrite = "application/json" not in accept_value

            if should_rewrite:
                if accept_idx is None:
                    raw_headers.append((b"accept", self._required_accept))
                else:
                    raw_headers[accept_idx] = (b"accept", self._required_accept)

                rewritten_scope = dict(scope)
                rewritten_scope["headers"] = raw_headers
                scope = rewritten_scope
        await self.app(scope, receive, send)


class _RootInfoApp:
    """ASGI adapter that serves a fast GET/HEAD response on the MCP root."""

    def __init__(self, app) -> None:
        self.app = app
        self.lifespan = getattr(app, "lifespan", None)

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") == "http" and scope.get("path") == "/":
            method = scope.get("method", "GET").upper()
            if method in {"GET", "HEAD"}:
                response = JSONResponse(
                    {
                        "status": "ok",
                        "service": "atomictoolkit",
                        "mcp": "streamable-http",
                    }
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# Primary MCP endpoint expected by Smithery and most registries.
_mcp_root_app = _ArtifactBaseUrlContextApp(
    _AcceptHeaderCompatApp(
        _RootInfoApp(
            mcp.http_app(
                path="/",
                transport="streamable-http",
                json_response=True,
                stateless_http=True,
            )
        )
    )
)


README_PATH = Path(__file__).resolve().parents[2] / "README.md"
TOOL_NAMES = [
    "build_structure_workflow",
    "analyze_structure_workflow",
    "write_structure_workflow",
    "optimize_structure_workflow",
    "single_point_workflow",
    "run_md_workflow",
    "analyze_trajectory_workflow",
    "autocorrelation_workflow",
    "read_structure_file",
    "create_download_artifact",
]


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
            "displayName": "Atomistic Toolkit MCP",
            "description": "MCP server for atomistic structure generation, analysis, optimization, and molecular dynamics using ASE, pymatgen, Nequix, and Orb.",
            "version": "0.1.0",
            "homepage": base_url,
            "documentationUrl": f"{base_url}/docs",
            "defaultTransport": {"type": "streamable-http", "url": f"{base_url}/"},
            "capabilities": {
                "tools": {"listChanged": False},
                "prompts": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
            },
            "tooling": {
                "domains": ["materials-science", "atomistic-simulation"],
                "tools": [{"name": tool} for tool in TOOL_NAMES],
                "artifactDownloadPath": f"{base_url}/artifacts/{{artifact_id}}/{{filename}}",
                "artifactFormats": [
                    "xyz", "extxyz", "traj", "cif", "vasp", "poscar",
                    "png", "svg", "eps", "pdf", "csv", "dat", "txt", "json", "log"
                ],
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


async def handle_artifact_download(request: Request):
    """Serve generated artifacts with disposition based on media type."""
    artifact_id = request.path_params["artifact_id"]
    record = artifact_store.get(artifact_id)
    if record is None or not record.filepath.exists():
        return JSONResponse({"error": "artifact_not_found", "artifact_id": artifact_id}, status_code=404)

    is_html_preview = record.filepath.suffix.lower() == ".html"
    return FileResponse(
        path=record.filepath,
        filename=record.filepath.name,
        content_disposition_type="inline" if is_html_preview else "attachment",
        media_type="text/html; charset=utf-8" if is_html_preview else None,
    )


async def handle_docs(request: Request) -> Response:
    """Serve a lightweight documentation page for the server card link."""
    if not README_PATH.exists():
        return JSONResponse({"error": "documentation_not_found"}, status_code=404)
    return FileResponse(
        README_PATH,
        media_type="text/markdown; charset=utf-8",
        filename="README.md",
    )


async def handle_sse_no_slash(request: Request):
    """Normalize /sse -> /sse/ so the mounted compatibility app handles it."""
    return RedirectResponse(url="/sse/", status_code=307)


app = Starlette(
    routes=[
        Route("/docs", handle_docs),
        Route("/healthz", handle_healthz),
        Route("/.well-known/mcp/server-card.json", handle_server_card),
        Route("/artifacts/{artifact_id:str}/{filename:str}", handle_artifact_download),
        Route("/sse", handle_sse_no_slash, methods=["GET", "HEAD", "POST", "DELETE"]),
        Mount("/sse", app=_PathRewriteApp(_mcp_root_app, target_path="/")),
        Mount("/", app=_mcp_root_app),
    ],
    lifespan=_mcp_root_app.lifespan,
)
