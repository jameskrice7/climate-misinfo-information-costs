#!/usr/bin/env bash
# Launch the local vLLM OpenAI-compatible server for Qwen3.6-35B-A3B-FP8.
set -euo pipefail
cd "$(dirname "$0")"

MODEL_DIR="models/Qwen3.6-35B-A3B-FP8"
PORT="${PORT:-8000}"

# flashinfer JITs sampling kernels for GB10 (sm_121); needs ninja + nvcc on PATH.
export PATH="$PWD/.venv_vllm/bin:/usr/local/cuda/bin:$PATH"
export VLLM_FLASHINFER_FORCE_TENSOR_CORES=1

exec .venv_vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_DIR" \
  --served-model-name qwen \
  --port "$PORT" \
  --host 127.0.0.1 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.80 \
  --max-num-seqs 256 \
  --max-num-batched-tokens 32768 \
  --moe-backend triton \
  --enable-prefix-caching \
  --structured-outputs-config '{"backend":"xgrammar"}' \
  --no-enable-log-requests
