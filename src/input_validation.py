from pathlib import Path

from src.config import VisionSettings, load_vision_settings
from src.image_parser import ImageParserError, validate_contract_image_file

INPUT_VALIDATION_STAGE = "input_validation"


class InputValidationError(Exception):
    def __init__(self, message: str) -> None:
        self.stage = INPUT_VALIDATION_STAGE
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


def validate_pipeline_inputs(
    original_image_path: str,
    amendment_image_path: str,
) -> None:
    
    if not original_image_path.strip():
        raise InputValidationError("Original contract image path is empty.")
    if not amendment_image_path.strip():
        raise InputValidationError("Amendment contract image path is empty.")

    original = Path(original_image_path)
    amendment = Path(amendment_image_path)
    vision_settings = load_vision_settings()

    _validate_image("Original contract", original, vision_settings)
    _validate_image("Amendment contract", amendment, vision_settings)

    if original.resolve() == amendment.resolve():
        raise InputValidationError(
            "Original and amendment images must be different files. "
            f"Both arguments point to: {original.resolve()}"
        )


def _validate_image(label: str, path: Path, vision_settings: VisionSettings) -> None:
    try:
        validate_contract_image_file(path, vision_settings)
    except ImageParserError as exc:
        raise InputValidationError(f"{label} image: {exc}") from exc
