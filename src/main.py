"""Entry point for the contract amendment analysis pipeline."""

import json
import sys

from src.health_check import run_health_check
from src.pipeline import PipelineError, create_pipeline_clients, run_pipeline

USAGE = "Usage: python -m src.main <original_image> <amendment_image>"


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
    clients = create_pipeline_clients()

    try:
        result = run_pipeline(original_image_path, amendment_image_path, clients)
    except PipelineError as exc:
        print(f"Pipeline failed at stage '{exc.stage}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
