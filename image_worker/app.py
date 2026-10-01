from pathlib import Path
from time import perf_counter
from uuid import uuid4

import torch
from diffusers import StableDiffusionPipeline
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Local Image Worker", version="0.1.0")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

_pipeline: StableDiffusionPipeline | None = None
_pipeline_model: str | None = None


class ImageGenerationRequest(BaseModel):
    model: str = Field(default="runwayml/stable-diffusion-v1-5")
    prompt: str
    negative_prompt: str = ""
    size: str = "512x512"
    steps: int = Field(default=25, ge=1, le=80)
    guidance_scale: float = Field(default=7.5, ge=0.0, le=20.0)


def parse_size(size: str) -> tuple[int, int]:
    try:
        width_raw, height_raw = size.lower().split("x", 1)
        width = int(width_raw)
        height = int(height_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Size must look like 512x512") from exc
    if width < 256 or height < 256 or width > 1024 or height > 1024:
        raise HTTPException(status_code=400, detail="Size must be between 256 and 1024")
    if width % 8 or height % 8:
        raise HTTPException(status_code=400, detail="Width and height must be divisible by 8")
    return width, height


def get_pipeline(model: str) -> StableDiffusionPipeline:
    global _pipeline, _pipeline_model
    if _pipeline is not None and _pipeline_model == model:
        return _pipeline

    # Stable Diffusion 1.5 on Apple MPS is more stable in float32. float16 can
    # produce repeated tiled artifacts on some macOS/PyTorch combinations.
    dtype = torch.float32
    pipe = StableDiffusionPipeline.from_pretrained(
        model,
        torch_dtype=dtype,
        safety_checker=None,
        requires_safety_checker=False,
    )
    if torch.backends.mps.is_available():
        pipe = pipe.to("mps")
    else:
        pipe = pipe.to("cpu")
    pipe.enable_attention_slicing()
    _pipeline = pipe
    _pipeline_model = model
    return pipe


@app.get("/health")
async def health() -> dict[str, str]:
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    return {"status": "ok", "device": device, "model": _pipeline_model or ""}


@app.post("/v1/images/generations")
async def generate_image(request: ImageGenerationRequest) -> dict:
    width, height = parse_size(request.size)
    started = perf_counter()
    pipe = get_pipeline(request.model)
    with torch.inference_mode():
        result = pipe(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or None,
            width=width,
            height=height,
            num_inference_steps=request.steps,
            guidance_scale=request.guidance_scale,
        )
    image = result.images[0]
    image_id = f"img_{uuid4().hex}"
    filename = f"{image_id}.png"
    image.save(OUTPUT_DIR / filename)
    latency = perf_counter() - started
    return {
        "id": image_id,
        "status": "completed",
        "data": [
            {
                "url": f"http://127.0.0.1:8188/outputs/{filename}",
                "latency_seconds": f"{latency:.2f}",
                "model": request.model,
            }
        ],
    }
