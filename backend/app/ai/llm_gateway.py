from langchain_openai import ChatOpenAI

from app.config import get_settings


def get_llm():
    settings = get_settings()

    if settings.llm_provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model,
            temperature=0,
            api_key=settings.openai_api_key or None,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
