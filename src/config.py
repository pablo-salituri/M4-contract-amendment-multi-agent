import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Single entry point for environment variables across the project.
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str


def load_settings() -> Settings:
    """Load and validate required environment variables."""
    missing = [
        name
        for name in (
            "OPENAI_API_KEY",
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_HOST",
        )
        if not os.getenv(name)
    ]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    return Settings(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        langfuse_public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        langfuse_secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        langfuse_host=os.environ["LANGFUSE_HOST"],
    )


def create_openai_client(settings: Settings) -> OpenAI:
    """Create an OpenAI client ready for use by later pipeline stages."""
    return OpenAI(api_key=settings.openai_api_key)


def create_langfuse_client(settings: Settings) -> Langfuse:
    """Create a Langfuse client ready for pipeline instrumentation."""
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_host,
    )
