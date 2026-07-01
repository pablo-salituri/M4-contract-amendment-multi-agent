import base64
import binascii
from pathlib import Path

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from src.config import (
    VisionSettings,
    create_openai_client,
    load_settings,
    load_vision_settings,
)

_IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
)


class ImageParserError(Exception):
    """Base error for contract image parsing failures."""


class ImageNotFoundError(ImageParserError):
    """Raised when the image path does not exist."""


class InvalidImagePathError(ImageParserError):
    """Raised when the path does not point to a file."""


class InvalidImageExtensionError(ImageParserError):
    """Raised when the image extension is not supported."""


class ImageReadError(ImageParserError):
    """Raised when the image file cannot be read or opened."""


class OpenAIVisionError(ImageParserError):
    """Raised when the OpenAI Vision API call fails."""


class EmptyModelResponseError(ImageParserError):
    """Raised when the model returns an empty or invalid response."""


class ModelRefusalError(ImageParserError):
    """Raised when the model refuses to transcribe the image."""


_REFUSAL_PATTERNS = (
    "i'm sorry",
    "i am sorry",
    "i can't assist",
    "i cannot assist",
    "i can't help",
    "i cannot help",
    "unable to assist",
    "unable to help",
)


def _validate_image_path(image_path: Path, vision_settings: VisionSettings) -> None:
    if not image_path.exists():
        raise ImageNotFoundError(f"Image file not found: {image_path}")

    if not image_path.is_file():
        raise InvalidImagePathError(f"Path is not a file: {image_path}")

    extension = image_path.suffix.lower()
    if extension not in vision_settings.supported_extensions:
        supported = ", ".join(sorted(vision_settings.supported_extensions))
        raise InvalidImageExtensionError(
            f"Unsupported image extension '{extension}'. "
            f"Supported extensions: {supported}"
        )


def _validate_image_size(image_path: Path) -> None:
    try:
        file_size = image_path.stat().st_size
    except OSError as exc:
        raise ImageReadError(
            f"Unable to read file size for '{image_path}': {exc}"
        ) from exc

    if file_size == 0:
        raise ImageReadError(f"Image file is empty (0 bytes): {image_path}")


def validate_contract_image_file(
    image_path: Path | str,
    vision_settings: VisionSettings | None = None,
) -> Path:
    """Validate an image path before sending data to OpenAI."""
    path = Path(image_path)
    resolved_settings = vision_settings or load_vision_settings()
    _validate_image_path(path, resolved_settings)
    _validate_image_size(path)
    return path


def _detect_image_format(image_bytes: bytes) -> str | None:
    for signature, extension in _IMAGE_SIGNATURES:
        if image_bytes.startswith(signature):
            return extension
    return None


def _read_and_encode_image(
    image_path: Path,
    vision_settings: VisionSettings,
) -> tuple[str, str]:
    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        raise ImageReadError(
            f"Failed to read image file '{image_path}': {exc}"
        ) from exc

    if not image_bytes:
        raise ImageReadError(f"Image file is empty: {image_path}")

    detected_extension = _detect_image_format(image_bytes)
    if detected_extension is None:
        raise ImageReadError(
            f"Image file cannot be opened or has an invalid format: {image_path}"
        )

    extension = image_path.suffix.lower()
    if extension == ".jpeg" and detected_extension == ".jpg":
        detected_extension = ".jpeg"

    if extension != detected_extension:
        raise ImageReadError(
            f"Image content does not match extension '{extension}' "
            f"for file: {image_path}"
        )

    mime_type = vision_settings.extension_to_mime_type[extension]

    try:
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
    except (binascii.Error, ValueError) as exc:
        raise ImageReadError(
            f"Failed to encode image as Base64 for file '{image_path}': {exc}"
        ) from exc

    return encoded_image, mime_type


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _detect_model_refusal(text: str) -> None:
    normalized = text.strip().lower()
    if any(pattern in normalized for pattern in _REFUSAL_PATTERNS):
        raise ModelRefusalError(
            "Vision model refused to transcribe the image. "
            f"Response preview: {text[:120]}"
        )


def _extract_response_text(response_content: object) -> str:
    if isinstance(response_content, str):
        text = response_content.strip()
        if text:
            return text
        raise EmptyModelResponseError("Model returned an empty text response.")

    if isinstance(response_content, list):
        text_parts: list[str] = []
        for part in response_content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = str(part.get("text", "")).strip()
                if text:
                    text_parts.append(text)

        if text_parts:
            return "\n".join(text_parts)

    raise EmptyModelResponseError("Model returned an invalid or empty response.")


def _call_vision_model(
    client: OpenAI,
    encoded_image: str,
    mime_type: str,
    vision_settings: VisionSettings,
) -> str:
    try:
        response = client.chat.completions.create(
            model=vision_settings.model,
            temperature=vision_settings.temperature,
            max_tokens=vision_settings.max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": vision_settings.extraction_system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_settings.extraction_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        )
    except RateLimitError as exc:
        raise OpenAIVisionError(f"OpenAI rate limit exceeded: {exc}") from exc
    except AuthenticationError as exc:
        raise OpenAIVisionError(f"OpenAI authentication failed: {exc}") from exc
    except APITimeoutError as exc:
        raise OpenAIVisionError(f"OpenAI request timed out: {exc}") from exc
    except APIConnectionError as exc:
        raise OpenAIVisionError(f"OpenAI connection error: {exc}") from exc
    except APIError as exc:
        raise OpenAIVisionError(f"OpenAI API error: {exc}") from exc

    if not response.choices:
        raise EmptyModelResponseError("OpenAI returned no completion choices.")

    message = response.choices[0].message
    if message is None or message.content is None:
        raise EmptyModelResponseError("OpenAI returned a completion without content.")

    text = _strip_markdown_fences(_extract_response_text(message.content))
    _detect_model_refusal(text)
    return text


def parse_contract_image(
    image_path: str,
    openai_client: OpenAI | None = None,
    vision_settings: VisionSettings | None = None,
) -> str:
    
    resolved_vision_settings = vision_settings or load_vision_settings()
    path = validate_contract_image_file(image_path, resolved_vision_settings)
    encoded_image, mime_type = _read_and_encode_image(path, resolved_vision_settings)

    client = openai_client or create_openai_client(load_settings())

    return _call_vision_model(
        client, encoded_image, mime_type, resolved_vision_settings
    )
