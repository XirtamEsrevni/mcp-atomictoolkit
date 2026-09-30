# Default image for free-tier hosts (Hugging Face Spaces, small VMs).
# EMT + ASE + pymatgen only. No OpenKIM compile, no Orb/Nequix/PyTorch.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    JAX_PLATFORMS=cpu \
    JAX_PLATFORM_NAME=cpu \
    CUDA_VISIBLE_DEVICES=

WORKDIR /app
COPY pyproject.toml README.md ./ 
COPY src ./src
COPY main.py ./

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e . \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 7860
ENV HOST=0.0.0.0
ENV PORT=7860

CMD ["sh", "-c", "uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port ${PORT:-7860}"]
