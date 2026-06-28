"""Entry point for the contract amendment analysis pipeline."""

import json
import sys
import threading

from src.health_check import run_health_check
from src.input_validation import InputValidationError, validate_pipeline_inputs
from src.pipeline import PipelineError, create_pipeline_clients, run_pipeline

USAGE = "Usage: python -m src.main <original_image> <amendment_image>"
_SPINNER_FRAMES = ("|", "/", "-", "\\")


def _exit_with_error(stage: str, message: str) -> None:
    print(f"Error at stage '{stage}': {message}", file=sys.stderr)
    sys.exit(1)


def _print_welcome(original_image_path: str, amendment_image_path: str) -> None:
    print()
    print()
    print("Contract Amendment Analysis")
    print("=" * 29)
    print("Comparing contract images:")
    print(f"  Original:  {original_image_path}")
    print(f"  Amendment: {amendment_image_path}")
    print()


class _AsciiSpinner:
    """Simple ASCII spinner shown on stderr while the pipeline runs."""

    def __init__(self, message: str = "Analyzing contracts") -> None:
        self._message = message
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "_AsciiSpinner":
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
        sys.stderr.write("\r" + " " * (len(self._message) + 6) + "\r")
        sys.stderr.flush()

    def _animate(self) -> None:
        frame_index = 0
        while not self._stop_event.is_set():
            frame = _SPINNER_FRAMES[frame_index % len(_SPINNER_FRAMES)]
            sys.stderr.write(f"\r{frame} {self._message}...")
            sys.stderr.flush()
            frame_index += 1
            self._stop_event.wait(0.15)


def main() -> None:
    if len(sys.argv) == 1:
        run_health_check()
        print("Health check passed.")
        return

    if len(sys.argv) != 3:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    original_image_path = sys.argv[1]
    amendment_image_path = sys.argv[2]

    run_health_check()

    try:
        validate_pipeline_inputs(original_image_path, amendment_image_path)
    except InputValidationError as exc:
        _exit_with_error(exc.stage, exc.message)

    _print_welcome(original_image_path, amendment_image_path)

    clients = create_pipeline_clients()

    try:
        with _AsciiSpinner("Analyzing contracts"):
            result = run_pipeline(original_image_path, amendment_image_path, clients)
    except PipelineError as exc:
        _exit_with_error(exc.stage, exc.message)
    except Exception as exc:
        _exit_with_error("pipeline", f"An unexpected error occurred: {exc}")

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
