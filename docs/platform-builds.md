# Platform Builds

## Supported Local Profile

The current local inference profile is macOS Apple Silicon:

- text: MLX on Apple Metal;
- images: Diffusers on Apple MPS/Metal;
- UI/API: Docker + Electron shell.

## Build Commands

macOS:

```bash
npm run app:build:mac
```

Linux:

```bash
npm run app:build:linux
```

Windows:

```bash
npm run app:build:win
```

## Important

Linux and Windows builds can package the Electron UI, but the bundled local
model runtime is not equivalent to the Mac profile. For Linux/Windows, configure
`.env.docker` to point to GPU model servers:

```env
TEXT_BACKEND=vllm
TEXT_BACKEND_URL=http://your-gpu-host:8000/v1
IMAGE_BACKEND=local_http
IMAGE_BACKEND_URL=http://your-image-worker:8188
```

Then run the same UI against those endpoints.
