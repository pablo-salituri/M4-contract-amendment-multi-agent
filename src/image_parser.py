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
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_settings.extraction_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}",
                            },
                        },
                    ],
                }
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

    return _extract_response_text(message.content)


def parse_contract_image(
    image_path: str,
    openai_client: OpenAI | None = None,
) -> str:
    """Extract plain text from a contract image using GPT-4o Vision."""
    path = Path(image_path)
    vision_settings = load_vision_settings()

    _validate_image_path(path, vision_settings)
    encoded_image, mime_type = _read_and_encode_image(path, vision_settings)

    client = openai_client or create_openai_client(load_settings())

    return _call_vision_model(client, encoded_image, mime_type, vision_settings)
