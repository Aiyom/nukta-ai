# Technical Plan

Date: 2026-09-30

## Goal

Build a public AI service with:

- open-weight models;
- no external model APIs for production inference;
- user data and model weights hosted on infrastructure we control;
- strong Russian language support;
- high-quality coding, document, search/RAG, image generation, and video
  generation;
- later supervised fine-tuning on vetted data.

We will not claim parity with ChatGPT until measured on our own evaluation
suite and user workloads.

## Recommended Model Stack

## Initial Decision Matrix

| Area | First candidate | Backup | Do not use in production yet | Gate |
| --- | --- | --- | --- | --- |
| Text/chat/code | Qwen3 large MoE | DeepSeek V3.x | Small local-only models if quality drops | quality, latency, license |
| Documents/RAG | Qwen/BGE embeddings + reranker | domain-tuned retriever | answer without citations | faithfulness |
| Images | Qwen-Image | SD 3.5 with revenue/license review | FLUX.1 dev without commercial license | license, text rendering |
| Video | Wan 2.x after license review | later vendor-neutral pipeline | any unclear-license checkpoint | license, cost |

The first paid benchmark should compare Qwen large MoE and DeepSeek V3.x on the
same tasks, not rely on leaderboard claims.

### Text, Russian, coding, agents

Primary candidate: `Qwen3-235B-A22B-Instruct` or the current Qwen3 2507 MoE
variant available at test time.

Why:

- strong multilingual coverage, including Russian;
- strong code and tool-use orientation;
- MoE serving cost is materially better than dense models at similar total
  parameter scale;
- Qwen3 documentation states support for hybrid thinking, tool calling, and long
  context variants;
- Qwen models are commonly released under Apache-2.0, but each exact checkpoint
  must be verified before use.

Fallback candidate: `DeepSeek-V3.1` / current DeepSeek V3.x instruct model.

Why:

- MIT license on DeepSeek-V3.1;
- strong coding and reasoning reputation;
- large MoE model, so serving requires serious multi-GPU infrastructure.

Avoid as default foundation: Llama 4.

Why:

- capable models, but license/use policy has additional restrictions. The Llama
  4 license has a 700M MAU commercial threshold, and the use policy has special
  restrictions for multimodal models in the EU. This is manageable, but less
  clean than Apache/MIT for a new public service.

### Embeddings and retrieval

Primary: Qwen embedding/reranker family or BGE-M3-class multilingual embeddings,
depending on current license and benchmark results.

Serving:

- vector store: Qdrant or pgvector;
- document parsing: marker/olmOCR-style OCR pipeline for PDFs, LibreOffice for
  Office conversion, Tika-like metadata extraction only as a helper;
- retrieval: hybrid BM25 + dense vectors + reranker.

### Image generation

Primary candidate: `Qwen-Image`.

Why:

- Apache-2.0 listed on Hugging Face;
- strong text rendering and multilingual prompt handling are relevant to Russian
  product use cases;
- avoids FLUX.1 dev non-commercial restriction.

Secondary candidate: Stable Diffusion 3.5 Medium/Large only if revenue/license
constraints are acceptable. Stability's public license page says Core Models are
free below USD 1M annual revenue, with enterprise licensing above that.

Avoid for production without a paid commercial license: `FLUX.1 [dev]`.

Why:

- official license is non-commercial/non-production for model use, even though
  outputs have separate terms.

### Video generation

Primary candidate: current Wan 2.x open video model after license verification.

Why:

- open video generation ecosystem is strongest around Wan-style pipelines;
- can be served separately as an asynchronous job queue because latency will be
  minutes, not seconds, for high quality.

Video remains the highest-risk module for cost, safety moderation, storage, and
copyright review. It should ship later than chat/search/code.

## System Architecture

### Public API

- FastAPI service with OpenAI-compatible endpoints where practical:
  - `/v1/chat/completions`
  - `/v1/embeddings`
  - `/v1/images/generations`
  - `/v1/videos/generations`
- service-side auth, rate limits, abuse controls, per-user quotas;
- all prompts, files, generations, and audit logs stored in our databases/object
  storage.

### Model Serving

- text: vLLM on multi-GPU nodes;
- image/video: ComfyUI or custom Diffusers workers behind an internal queue;
- embeddings/reranking: smaller dedicated GPU or CPU/GPU mixed service;
- routing: model router selects text/search/code/document/image/video worker.

### Data Plane

- Postgres: users, projects, billing, metadata, eval runs;
- object storage: uploaded documents, generated files, model artifacts;
- vector DB: Qdrant/pgvector;
- event queue: Redis/NATS for async image/video/document jobs;
- observability: Prometheus/Grafana, structured logs, tracing.

### Safety and Compliance

- retain model and dataset license records per checkpoint;
- disclose AI-generated outputs where required;
- block or review unsafe image/video/document requests;
- isolate user data by account/project;
- encrypted storage and restricted admin access;
- delete/export flow for user data.

## Infrastructure Proposal

No rental or purchase should happen without explicit approval.

### Phase 1: Benchmarking

Rent short-lived GPU instances only for tests:

- text candidate: 8x H100/H200 class node for Qwen/DeepSeek large MoE;
- image candidate: 1x H100/H200 or high-memory L40S/A100 if performance is
  acceptable;
- embedding/reranker: 1x L40S/A100 or CPU if latency is acceptable.

Run each candidate against `eval/tasks.jsonl` and record:

- quality score;
- tokens/sec;
- time-to-first-token;
- VRAM/RAM usage;
- cost per 1K input/output tokens or per generated asset;
- failure modes.

### Phase 2: Private Alpha

- one always-on text node if usage justifies it;
- image/video workers scale to zero or scheduled capacity;
- separate staging and production networks;
- backups and disaster recovery.

### Phase 3: Fine-Tuning

- collect vetted, licensed, task-specific data;
- start with LoRA/QLoRA/SFT on focused skills;
- run regression eval before deployment;
- keep base model and fine-tuned adapters versioned and reversible.

## Decision Gates

1. License gate: exact checkpoint license and acceptable-use terms verified.
2. Quality gate: passes minimum eval score on Russian, code, docs, search.
3. Latency gate: meets product target for interactive chat.
4. Cost gate: forecasted unit economics are acceptable.
5. Safety gate: moderation, logging, disclosure, and abuse controls are in place.

## Initial Product Scope

First usable alpha:

- chat in Russian and English;
- code assistant;
- document upload and Q&A;
- web/search-backed answers using our own crawler/index or approved data sources;
- image generation as async jobs;
- admin panel for evals, model versions, and costs.

Later:

- video generation;
- user fine-tuned workspaces;
- hosted private deployments for customers.
