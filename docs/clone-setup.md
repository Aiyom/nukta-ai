# Clone Setup

After cloning on macOS Apple Silicon:

```bash
cd new_ai_version
bash scripts/setup_after_clone.sh
```

This installs:

- Electron dependencies;
- MLX text backend;
- Diffusers image worker dependencies;
- configured local models:
  - `mlx-community/Qwen3-8B-4bit`;
  - `runwayml/stable-diffusion-v1-5`.

Run:

```bash
npm run app
```

Build Mac app:

```bash
bash scripts/build_for_platform.sh
```

Generated sites are written to:

```text
generated_sites/
```

Generated images are written to:

```text
image_worker/outputs/
```

## Other Platforms

The current local profile is macOS Apple Silicon because it uses MLX and Apple
MPS/Metal. On Linux or Windows, point `.env.docker` to server GPU model
endpoints, then add the matching Electron Builder target.
