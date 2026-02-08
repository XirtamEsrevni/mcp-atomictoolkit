# MCP server design review (Atomic Toolkit)

This document checks the current MCP server implementation against common MCP server design
expectations (tool surface, transports, metadata, and operational safety), and records any
follow‑up recommendations.

## ✅ What already aligns well

- **Clear tool-first surface**: `mcp_server.py` exposes a cohesive set of MCP tools with
  descriptive docstrings and stable names (e.g., `build_structure_workflow`,
  `optimize_structure_workflow`, `run_md_workflow`).【F:src/mcp_atomictoolkit/mcp_server.py†L184-L507】
- **HTTP/Streamable transport**: The ASGI app mounts a Streamable HTTP transport at `/` and
  a compatibility alias at `/sse/`, which matches common MCP registry expectations.【F:src/mcp_atomictoolkit/http_app.py†L97-L208】
- **Server card metadata**: The server card includes name, version, transport URLs, and
  artifact download info, which helps registries and discovery tools understand the server
  surface area.【F:src/mcp_atomictoolkit/http_app.py†L126-L162】
- **Artifact delivery**: Tool results are wrapped with `with_downloadable_artifacts`, and
  a dedicated `/artifacts/{artifact_id}/{filename}` handler serves generated files with
  safe `Content-Disposition` behavior.【F:src/mcp_atomictoolkit/mcp_server.py†L110-L181】【F:src/mcp_atomictoolkit/http_app.py†L165-L178】
- **Error reporting + operator hints**: The tool execution wrapper logs failures, returns
  structured error payloads, and stores an error report file for debugging workflows.【F:src/mcp_atomictoolkit/mcp_server.py†L46-L182】

## ✅ Recommendations implemented

- **Capabilities flags**: The server card now sets `listChanged` to `false` for tools, prompts,
  and resources to reflect the static tool surface.【F:src/mcp_atomictoolkit/http_app.py†L136-L142】【F:src/mcp_atomictoolkit/mcp_server.py†L184-L507】
- **Documentation URL**: The server card now points `documentationUrl` to a lightweight `/docs`
  endpoint that serves the README for human-readable docs.【F:src/mcp_atomictoolkit/http_app.py†L126-L189】
- **Transport clarity**: The README now documents STDIO mode and highlights the stdout logging
  constraint for STDIO transports.【F:README.md†L59-L79】

## ✅ Outcome

The current implementation is already a **solid MCP server design** with a clean tool surface,
Streamable HTTP transport, registry metadata, and explicit artifact handling. The items above
are incremental metadata/operational improvements rather than blockers.
