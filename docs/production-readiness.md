# Production Readiness Checklist

This repository is now runnable locally, but production means more than a
working endpoint.

## Local Production-Like Mode

One-command managed mode:

```bash
bash scripts/docker_start.sh
```

Stop API/UI and the managed MLX model process:

```bash
bash scripts/docker_stop.sh
```

In this mode Docker runs the API/UI, while local model workers run on the Mac
host with Apple Metal/MPS access. The Docker container reaches them through
`host.docker.internal`.

Workers:

- text MLX: `127.0.0.1:8000`;
- image Diffusers: `127.0.0.1:8188`.

1. Start a local model backend:

```bash
MODEL=mlx-community/Qwen3-14B-4bit bash scripts/start_mlx_qwen.sh
```

For this Mac, the first verified model is:

```bash
MODEL=mlx-community/Qwen3-8B-4bit bash scripts/start_mlx_qwen.sh
```

2. Configure the API:

```bash
cp .env.example .env
perl -0pi -e 's/TEXT_BACKEND=mock/TEXT_BACKEND=mlx/' .env
```

3. Start the app:

```bash
bash scripts/start_api.sh
```

4. Open:

```text
http://127.0.0.1:8080
```

5. Measure speed:

```bash
curl -sS http://127.0.0.1:8080/v1/bench/chat \
  -H 'content-type: application/json' \
  -d '{"runs":3,"max_tokens":512}'
```

## Before Public Users

- Put API behind TLS and a reverse proxy.
- Add login, API keys, user quotas, and rate limits.
- Persist conversations and files in Postgres/object storage.
- Replace local SD 1.5 image baseline with a licensed production image model or
  dedicated image GPU worker.
- Add prompt/file abuse moderation.
- Add structured logs, metrics, tracing, and alerting.
- Add backups and deletion/export flows.
- Run evals on every model/config change.
- Use GPU servers for production text/image/video models.

## Local Mac Role

The Mac is a control/development node and a small-model benchmark node. It is
not the final serving box for high-quality public traffic.

Verified local speed on 2026-10-01:

- `mlx-community/Qwen3-8B-4bit`
- 3 runs, 256 max output tokens
- average latency 9.53 seconds
- average estimated speed 26.93 tokens/second
