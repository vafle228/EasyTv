# Reuse the installed CUDA 12.8 / PyTorch 2.10 stack; no RelayVSR process is launched.
FROM easytv-relayvsr:latest
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 g++ \
    && rm -rf /var/lib/apt/lists/*
RUN uv pip install --python /opt/relay/.venv/bin/python --no-deps torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
WORKDIR /opt/seedvr2
COPY . .
RUN printf 'torch==2.10.0+cu128\ntorchvision==0.25.0+cu128\n' > /tmp/torch-constraints.txt \
    && uv pip install --python /opt/relay/.venv/bin/python -c /tmp/torch-constraints.txt -r requirements.txt
ENV PYTHONPATH=/opt/seedvr2 HF_HOME=/benchmark/hf-cache PYTHONUNBUFFERED=1
CMD ["sleep", "infinity"]
