import os
import logging

import uvicorn

from mcp_atomictoolkit.http_app import app


if __name__ == "__main__":
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())
