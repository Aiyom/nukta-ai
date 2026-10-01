# Local Apple GPU Runbook

Your detected machine:

- MacBook Pro `MacBookPro18,1`
- Apple M1 Pro
- 10 CPU cores
- 16 GPU cores
- 32 GB unified memory
- Metal supported

This is suitable for local product work and speed checks with quantized
7B/14B-class models. It is not the right production target for Qwen/DeepSeek
200B+ MoE models.

## Recommended Local Backends

### Option A: MLX

Best native Apple Silicon path.

Use this for local Russian/code prototypes:

- `mlx-community/Qwen3-8B-4bit`
- `mlx-community/Qwen3-14B-4bit`
- possibly `mlx-community/Qwen3-32B-4bit`, if memory pressure is acceptable.

The exact model name should be verified before download.

Typical command:

```bash
python3 -m venv .venv-mlx
. .venv-mlx/bin/activate
pip install -U mlx-lm
python -m mlx_lm.server --model mlx-community/Qwen3-14B-4bit --host 127.0.0.1 --port 8000
```

Then configure this app:

```bash
cp .env.example .env
perl -0pi -e 's/TEXT_BACKEND=mock/TEXT_BACKEND=mlx/' .env
perl -0pi -e 's#TEXT_BACKEND_URL=http://127.0.0.1:8000/v1#TEXT_BACKEND_URL=http://127.0.0.1:8000/v1#' .env
```

### Option B: llama.cpp with Metal

Use this if a good GGUF quant exists for the chosen model.

Typical command after installing llama.cpp:

```bash
llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8000 -c 8192 -ngl 999
```

Then set:

```bash
TEXT_BACKEND=llama_cpp
TEXT_BACKEND_URL=http://127.0.0.1:8000/v1
```

## Local Image Generation

The local stack now includes a Diffusers image worker:

- endpoint: `http://127.0.0.1:8188`;
- default model: `runwayml/stable-diffusion-v1-5`;
- device: Apple MPS when available, CPU fallback otherwise;
- API route through main app: `/v1/images/generations`.

Install dependencies once:

```bash
bash scripts/install_image_worker.sh
```

The managed stack starts it automatically:

```bash
bash scripts/run_stack.sh
```

Measured proof-of-workflow:

- prompt: lonely green tree in golden desert;
- size: 256x256;
- steps: 5;
- latency after model download/load path: 9.15 seconds end-to-end through API;
- quality: poor at 5 steps/256px, useful only as a fast smoke test.

The UI default uses 512x512 and 25 steps, which should look better but will be
slower on this laptop. For production-quality images, plan a separate GPU image
worker after license and cost review.

## Expected Local Reality

Rough expectation before measurement:

- 7B 4-bit: interactive.
- 14B 4-bit: usable for chat and coding drafts.
- 32B 4-bit: possible but slower and memory-sensitive.
- 70B+ or 200B+ MoE: not practical on this laptop for a public service.

The app's `/v1/bench/chat` endpoint reports latency and estimated tokens/sec for
the backend you connect.

## Measured Result On This Machine

Measured on 2026-10-01 with:

- backend: MLX
- model: `mlx-community/Qwen3-8B-4bit`
- prompt: Russian production-plan prompt
- output cap: 256 tokens
- runs: 3

Result:

- average latency: 9.53 seconds;
- average estimated generation speed: 26.93 tokens/second;
- individual runs: 25.80, 26.23, 28.76 tokens/second.

This is good enough for local development and private use. It is not enough for
a public high-concurrency service without GPU servers.
