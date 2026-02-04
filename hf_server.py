import os

import uvicorn

from mcp_atomictoolkit.http_app import app


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host=host, port=port, log_level="info")
