from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    reasoning: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="router-default")
    messages: list[ChatMessage]
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=32768)
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl_{uuid4().hex}")
    object: str = "chat.completion"
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)


class ImageGenerationRequest(BaseModel):
    model: str = Field(default="image-default")
    prompt: str
    negative_prompt: str = ""
    size: str = "512x512"
    steps: int = Field(default=25, ge=1, le=80)
    guidance_scale: float = Field(default=7.5, ge=0.0, le=20.0)


class ImageGenerationResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"img_{uuid4().hex}")
    status: Literal["queued", "completed"]
    data: list[dict[str, str]]


class VideoGenerationRequest(BaseModel):
    model: str = Field(default="wan-video")
    prompt: str
    duration_seconds: int = Field(default=6, ge=1, le=30)


class VideoGenerationResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"vid_{uuid4().hex}")
    status: Literal["queued", "completed"]
    data: list[dict[str, str]]


class BenchmarkRequest(BaseModel):
    model: str = Field(default="router-default")
    prompt: str = "Напиши краткий план запуска ИИ-сервиса на открытых весах."
    runs: int = Field(default=3, ge=1, le=20)
    max_tokens: int = Field(default=512, ge=1, le=8192)


class BenchmarkRun(BaseModel):
    run: int
    latency_seconds: float
    output_chars: int
    estimated_output_tokens: int
    estimated_tokens_per_second: float


class BenchmarkResponse(BaseModel):
    model: str
    backend: str
    runs: list[BenchmarkRun]
    average_latency_seconds: float
    average_estimated_tokens_per_second: float


class AgentRunRequest(BaseModel):
    input: str
    mode: Literal["auto", "chat", "image", "benchmark"] = "auto"


class AgentStep(BaseModel):
    title: str
    detail: str
    status: Literal["queued", "running", "completed", "failed"] = "completed"


class AgentRunResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"run_{uuid4().hex}")
    mode: Literal["chat", "image", "benchmark"]
    status: Literal["completed", "failed"]
    steps: list[AgentStep]
    message: str = ""
    artifacts: list[dict[str, str]] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class SiteGenerationRequest(BaseModel):
    name: str = Field(default="local-site")
    prompt: str


class SiteGenerationResponse(BaseModel):
    id: str
    path: str
    url: str
    files: list[str]
