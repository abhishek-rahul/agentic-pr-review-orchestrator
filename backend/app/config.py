import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Agentic PR Review")
    app_env: str = os.getenv("APP_ENV", "local")
    cors_origins: str = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:5173")

    github_token: str = os.getenv("GITHUB_TOKEN", "")

    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://pr_user:pr_password@localhost:5432/pr_review",
    )
    elasticsearch_url: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")

    max_agent_retries: int = int(os.getenv("MAX_AGENT_RETRIES", "3"))


def get_settings() -> Settings:
    return Settings()
