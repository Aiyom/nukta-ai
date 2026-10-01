from abc import ABC, abstractmethod
import re
from time import perf_counter

import httpx

from app.config import settings
from app.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    ImageGenerationRequest,
    ImageGenerationResponse,
    VideoGenerationRequest,
    VideoGenerationResponse,
)


class TextProvider(ABC):
    @abstractmethod
    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise NotImplementedError


class MockTextProvider(TextProvider):
    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        user_text = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        started = perf_counter()
        content = (
            "Это локальный mock-ответ. Для реальной скорости и качества установи "
            "TEXT_BACKEND=vllm и TEXT_BACKEND_URL на свой self-hosted vLLM endpoint. "
            f"Последнее сообщение пользователя: {user_text[:500]}"
        )
        estimated_tokens = max(1, len(content) // 4)
        latency = perf_counter() - started
        return ChatCompletionResponse(
            model=request.model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=content))],
            usage={"completion_tokens": estimated_tokens},
            metrics={
                "latency_seconds": latency,
                "estimated_tokens_per_second": estimated_tokens / max(latency, 0.001),
            },
        )


class VllmTextProvider(TextProvider):
    async def complete(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        payload = request.model_dump()
        if payload["model"] in {"router-default", "local-default", ""}:
            payload["model"] = settings.text_model
        if settings.text_backend == "mlx" and payload["messages"]:
            payload["messages"][-1]["content"] = f"{payload['messages'][-1]['content']}\n/no_think"
        headers = {}
        if settings.text_backend_api_key:
            headers["authorization"] = f"Bearer {settings.text_backend_api_key}"
        started = perf_counter()
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{settings.text_backend_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            raw = response.json()
        parsed = ChatCompletionResponse.model_validate(raw)
        latency = perf_counter() - started
        for choice in parsed.choices:
            if not choice.message.content and choice.message.reasoning:
                choice.message.content = choice.message.reasoning
        content = parsed.choices[0].message.content if parsed.choices else ""
        output_tokens = parsed.usage.get("completion_tokens") or max(1, len(content) // 4)
        parsed.metrics.update(
            {
                "latency_seconds": latency,
                "estimated_tokens_per_second": output_tokens / max(latency, 0.001),
            }
        )
        return parsed


class ImageProvider(ABC):
    @abstractmethod
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        raise NotImplementedError


class MockImageProvider(ImageProvider):
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        return ImageGenerationResponse(
            status="completed",
            data=[{"error": "Image backend is not configured. Set IMAGE_BACKEND=local_http."}],
        )


class LocalHttpImageProvider(ImageProvider):
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        payload = request.model_dump()
        if payload["model"] in {"image-default", ""}:
            payload["model"] = settings.image_model
        payload["prompt"] = build_image_prompt(payload["prompt"])
        payload["negative_prompt"] = build_negative_prompt(payload.get("negative_prompt", ""))
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds * 4) as client:
            response = await client.post(
                f"{settings.image_backend_url}/v1/images/generations",
                json=payload,
            )
            response.raise_for_status()
            return ImageGenerationResponse.model_validate(response.json())


def has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[а-яА-ЯёЁ]", text))


def build_image_prompt(prompt: str) -> str:
    normalized = prompt.strip()
    lower = normalized.lower()
    if not has_cyrillic(normalized):
        return normalized

    parts: list[str] = []
    if "дерев" in lower:
        parts.append("a large lonely acacia tree centered in the foreground")
    if "пустын" in lower or "пес" in lower:
        parts.append("in a vast empty golden sand desert with dunes")
    if "солн" in lower:
        parts.append("warm sunlight")
    if "реал" in lower or not parts:
        parts.append("realistic photo")

    if not parts:
        parts.append(normalized)

    style = (
        "wide landscape composition, natural colors, clear subject, "
        "high detail, no city, no buildings"
    )
    return ", ".join(parts + [style])


def build_negative_prompt(extra: str) -> str:
    base = (
        "city, buildings, church, cathedral, road, cars, people, skyline, "
        "urban landscape, empty landscape, no tree, blurry, distorted, low quality, text, watermark"
    )
    return f"{base}, {extra}" if extra else base


class VideoProvider(ABC):
    @abstractmethod
    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        raise NotImplementedError


class MockVideoProvider(VideoProvider):
    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        return VideoGenerationResponse(
            status="queued",
            data=[{"note": "Route to a self-hosted approved video worker after license validation."}],
        )


def get_text_provider() -> TextProvider:
    if settings.text_backend in {"vllm", "mlx", "llama_cpp"}:
        return VllmTextProvider()
    return MockTextProvider()


def get_image_provider() -> ImageProvider:
    if settings.image_backend == "local_http":
        return LocalHttpImageProvider()
    return MockImageProvider()


def get_video_provider() -> VideoProvider:
    return MockVideoProvider()
