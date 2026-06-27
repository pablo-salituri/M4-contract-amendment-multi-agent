import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langfuse import Langfuse
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Single entry point for environment variables across the project.
load_dotenv(PROJECT_ROOT / ".env")

SUPPORTED_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

EXTENSION_TO_MIME_TYPE = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

CONTRACT_EXTRACTION_PROMPT = """You are a document transcription assistant.

Extract the complete text from the contract image provided.

Requirements:
- Transcribe every visible word faithfully.
- Preserve the document structure: titles, numbering, sections, and paragraphs.
- Keep line breaks and spacing where they reflect the original layout.
- Do not summarize, interpret, paraphrase, or omit any content.
- Do not add commentary or analysis.

Return only the transcribed text of the document."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str


@dataclass(frozen=True)
class VisionSettings:
    model: str
    temperature: float
    max_tokens: int
    supported_extensions: frozenset[str]
    extension_to_mime_type: dict[str, str]
    extraction_prompt: str


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


def load_vision_settings() -> VisionSettings:
    """Load vision model configuration for contract image parsing."""
    return VisionSettings(
        model=os.getenv("OPENAI_VISION_MODEL", "gpt-4o"),
        temperature=float(os.getenv("OPENAI_VISION_TEMPERATURE", "0")),
        max_tokens=int(os.getenv("OPENAI_VISION_MAX_TOKENS", "4096")),
        supported_extensions=SUPPORTED_IMAGE_EXTENSIONS,
        extension_to_mime_type=EXTENSION_TO_MIME_TYPE,
        extraction_prompt=CONTRACT_EXTRACTION_PROMPT,
    )
