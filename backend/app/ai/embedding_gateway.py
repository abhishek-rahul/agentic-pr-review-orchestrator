from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


def get_embeddings():
    settings = get_settings()

    if settings.embedding_provider == "openai":
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key or None,
        )

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
