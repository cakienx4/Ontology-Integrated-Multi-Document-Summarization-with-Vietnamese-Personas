from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str | None = None
    runai_endpoint: str = "https://text-sum-gpt-oss-120b-runai-text-sum.runai-inference.cyberspace.vn"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

settings = Settings()