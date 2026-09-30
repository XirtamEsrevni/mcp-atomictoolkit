# Hosting Atomic Toolkit MCP

A public MCP server needs a process that stays up and speaks Streamable HTTP. That rules out most "sleeps after 15 minutes" free web dynos unless you accept cold starts.

## What actually works on a free tier

**Best current option: Hugging Face Spaces (Docker).**

- Free CPU Space, public URL, port `7860` (this repo already uses that).
- Cold starts exist, but the Space stays associated with a stable URL clients can bookmark.
- Use the default `Dockerfile` in this repo (ASE + EMT + pymatgen only).

Create a Space → SDK **Docker** → point it at this repository. Health check: `GET /healthz`. MCP endpoint: `POST /`. Server card: `GET /.well-known/mcp/server-card.json`.

**Render / Railway / Fly.io**

- Render no longer offers a useful always-on free Docker web service. `render.yaml` is kept for paid starter instances.
- Fly.io and Railway can host the lite image cheaply, but the true zero-dollar allowance is small and sleeps.
- Do not install `[full]` or `[mlip]` on a free VM. Orb/Nequix pull PyTorch and will OOM or time out the build.

## Image flavors

| File | What you get | Use when |
| --- | --- | --- |
| `Dockerfile` | ASE, pymatgen, FastMCP, EMT | Public free host |
| `Dockerfile.full` | + OpenKIM + Orb + Nequix | Paid box with ≥8 GB RAM |

```bash
# lite, what users should hit
docker build -t mcp-atomictoolkit:lite .

# full MLIP stack
docker build -f Dockerfile.full -t mcp-atomictoolkit:full .
```

On the lite image, `calculator_name='auto'` falls through to EMT for Al/Cu/Ag/Au/Ni/Pd/Pt. Other chemistries need `[mlip]` or `[kim]`.

## Client config

```json
{
  "mcpServers": {
    "atomictoolkit": {
      "url": "https://YOUR-SPACE.hf.space/"
    }
  }
}
```

Keep MD `steps` and supercells small on free CPU. Prefer `relax_and_md_workflow` with `steps<=50` and EMT.
