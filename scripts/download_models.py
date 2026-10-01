import os
from pathlib import Path

from huggingface_hub import snapshot_download


TEXT_MODEL = os.getenv("TEXT_MODEL", "mlx-community/Qwen3-8B-4bit")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "runwayml/stable-diffusion-v1-5")


def download_model(repo_id: str) -> None:
    print(f"Downloading {repo_id}...")
    path = snapshot_download(repo_id=repo_id)
    print(f"Ready: {repo_id} -> {path}")


def main() -> None:
    Path("generated_sites").mkdir(exist_ok=True)
    Path("image_worker/outputs").mkdir(parents=True, exist_ok=True)
    download_model(TEXT_MODEL)
    download_model(IMAGE_MODEL)
    print("All configured local models are downloaded.")


if __name__ == "__main__":
    main()
