import json
from dataclasses import dataclass

from app.config import settings


@dataclass
class ModelRecord:
    id: str
    name: str
    kind: str
    backend: str
    source_url: str = ""
    license: str = ""
    notes: str = ""
    installed: bool = False

    def to_dict(self, active_id: str) -> dict[str, str | bool]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "backend": self.backend,
            "source_url": self.source_url,
            "license": self.license,
            "notes": self.notes,
            "installed": self.installed,
            "active": self.id == active_id,
            "download_command": f"bash scripts/download_model.sh {self.id}",
        }


_catalog: dict[str, dict[str, ModelRecord]] = {"text": {}, "image": {}, "video": {}}
_active_models = {
    "text": settings.text_model,
    "image": settings.image_model,
    "video": "wan-video",
}


def _add(record: ModelRecord) -> None:
    _catalog.setdefault(record.kind, {})[record.id] = record


def _load_defaults() -> None:
    _add(
        ModelRecord(
            id=settings.text_model,
            name="Qwen3 8B 4-bit",
            kind="text",
            backend=settings.text_backend,
            source_url=f"https://huggingface.co/{settings.text_model}",
            license="Check upstream model card before production use",
            notes="Current Apple Silicon local baseline through MLX.",
            installed=True,
        )
    )
    _add(
        ModelRecord(
            id="mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
            name="Qwen2.5 Coder 7B 4-bit",
            kind="text",
            backend="mlx",
            source_url="https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
            license="Check upstream model card before production use",
            notes="Good candidate for local coding tasks on Apple Silicon.",
        )
    )
    _add(
        ModelRecord(
            id="mlx-community/Mistral-7B-Instruct-v0.3-4bit",
            name="Mistral 7B Instruct 4-bit",
            kind="text",
            backend="mlx",
            source_url="https://huggingface.co/mlx-community/Mistral-7B-Instruct-v0.3-4bit",
            license="Apache-2.0, verify upstream card",
            notes="Alternative compact local instruct model.",
        )
    )
    _add(
        ModelRecord(
            id=settings.image_model,
            name="Stable Diffusion v1.5",
            kind="image",
            backend=settings.image_backend,
            source_url=f"https://huggingface.co/{settings.image_model}",
            license="CreativeML Open RAIL-M, verify upstream card",
            notes="Local image workflow baseline, not final quality target.",
            installed=True,
        )
    )
    _add(
        ModelRecord(
            id="stabilityai/stable-diffusion-xl-base-1.0",
            name="Stable Diffusion XL Base 1.0",
            kind="image",
            backend="local_http",
            source_url="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
            license="Open RAIL++, verify upstream card",
            notes="Better image quality candidate, heavier than SD 1.5.",
        )
    )


def _load_custom_catalog() -> None:
    if not settings.model_catalog_json:
        return
    for raw in json.loads(settings.model_catalog_json):
        _add(ModelRecord(**raw))


_load_defaults()
_load_custom_catalog()


def list_models(kind: str | None = None) -> dict[str, list[dict[str, str | bool]]]:
    kinds = [kind] if kind else sorted(_catalog)
    return {
        item_kind: [
            record.to_dict(_active_models.get(item_kind, ""))
            for record in _catalog.get(item_kind, {}).values()
        ]
        for item_kind in kinds
    }


def get_active_model(kind: str) -> str:
    return _active_models.get(kind, "")


def set_active_model(kind: str, model_id: str) -> ModelRecord:
    if kind not in _catalog or model_id not in _catalog[kind]:
        raise KeyError(model_id)
    _active_models[kind] = model_id
    return _catalog[kind][model_id]


def add_model(record: ModelRecord) -> ModelRecord:
    _add(record)
    return record
