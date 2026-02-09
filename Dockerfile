FROM python:3.13-slim

WORKDIR /app
COPY . .

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        gfortran \
        git \
        pkg-config \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch v2.4.0 https://github.com/openkim/kim-api.git /tmp/kim-api \
    && cmake -S /tmp/kim-api -B /tmp/kim-api/build -DCMAKE_INSTALL_PREFIX=/usr/local \
    && cmake --build /tmp/kim-api/build --target install \
    && rm -rf /tmp/kim-api

ENV LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH}"
ENV PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:${PKG_CONFIG_PATH}"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

EXPOSE 7860
ENV HOST=0.0.0.0
ENV PORT=7860

CMD ["sh", "-c", "uvicorn mcp_atomictoolkit.http_app:app --host 0.0.0.0 --port ${PORT:-7860}"]
