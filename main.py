import os

from mcp_atomictoolkit.mcp_server import mcp


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "10000"))
    mcp.run(transport="sse", host=host, port=port)
