import json
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./pitchit.db"
    jwt_secret: str = ""
    jwt_expire_minutes: int = 720
    cors_origins: str = "http://localhost:5173"
    llm_provider: str = "groq"
    groq_api_key: str = ""
    llm_model_cheap: str = "llama-3.1-8b-instant"
    llm_model_strong: str = "llama-3.3-70b-versatile"
    llm_pricing_json: str = "{}"

    @property
    def pricing(self) -> dict[str, tuple[float, float]]:
        return {k: tuple(v) for k, v in json.loads(self.llm_pricing_json).items()}

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret:
        raise RuntimeError("JWT_SECRET must be set (see .env.example)")
    return s
