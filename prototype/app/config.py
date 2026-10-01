from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8")

    app_name: str = Field(default="Nukta AI")
    environment: str = Field(default="local")
    cors_origins: str = Field(default="http://127.0.0.1:8080,http://localhost:8080")
    text_backend: str = Field(default="mock")
    text_backend_url: str = Field(default="http://127.0.0.1:8000/v1")
    text_backend_api_key: str = Field(default="")
    text_model: str = Field(default="mlx-community/Qwen3-8B-4bit")
    image_backend: str = Field(default="mock")
    image_backend_url: str = Field(default="http://127.0.0.1:8188")
    image_model: str = Field(default="runwayml/stable-diffusion-v1-5")
    video_backend: str = Field(default="mock")
    video_backend_url: str = Field(default="http://127.0.0.1:8189")
    request_timeout_seconds: float = Field(default=180.0)
    max_prompt_chars: int = Field(default=120000)
    generated_sites_dir: str = Field(default="../generated_sites")
    model_catalog_json: str = Field(default="")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
