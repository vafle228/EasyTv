FROM python:3.12-slim AS system
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir uv

FROM system AS inference
WORKDIR /opt/relay
ARG RELAYVSR_REVISION=e856773350f53036d825404c9ea9228e6dffadca
RUN git init && git remote add origin https://github.com/kopperx/RelayVSR.git \
    && git fetch --depth 1 origin "$RELAYVSR_REVISION" && git checkout --detach FETCH_HEAD \
    && uv sync --locked --extra cu128 \
    && uv pip install 'fastapi>=0.110' 'uvicorn>=0.29'

FROM system AS app
# Triton builds its CUDA driver launcher as a small C extension on first inference.
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=inference /opt/relay /opt/relay
# Upstream .python-version selects a uv-managed interpreter; the venv links to it.
COPY --from=inference /root/.local/share/uv/python /root/.local/share/uv/python
ENV PATH="/opt/relay/.venv/bin:$PATH" PYTHONPATH=/opt/relay:/service
WORKDIR /service
COPY relayvsr/worker ./worker
EXPOSE 8090
CMD ["python", "-m", "uvicorn", "worker.app:app", "--host", "0.0.0.0", "--port", "8090"]
