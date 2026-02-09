FROM ubuntu:22.04

WORKDIR /app
COPY . .

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        software-properties-common \
        build-essential \
        pkg-config \
        git \
        gnupg \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-dev \
        python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:openkim/latest \
    && apt-get update \
    && apt-get install -y --no-install-recommends libkim-api-dev \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH="/usr/lib:/usr/local/lib"
ENV PKG_CONFIG_PATH="/usr/lib/pkgconfig:/usr/local/lib/pkgconfig"

RUN python3.12 -m ensurepip --upgrade \
    && python3.12 -m pip install --no-cache-dir --upgrade pip \
    && python3.12 -m pip install --no-cache-dir -r requirements.txt

EXPOSE 7860
ENV HOST=0.0.0.0
ENV PORT=7860

CMD ["sh", "-c", "uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port ${PORT:-7860}"]
