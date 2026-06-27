"""Entry point for the contract amendment analysis pipeline."""

import json
import sys

from src.config import create_langfuse_client, create_openai_client, load_settings
from src.pipeline import PipelineClients, PipelineError, run_pipeline

USAGE = "Usage: python -m src.main <original_image> <amendment_image>"


def main() -> None:
    if len(sys.argv) != 3:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    original_image_path = sys.argv[1]
    amendment_image_path = sys.argv[2]

    settings = load_settings()
    clients = PipelineClients(
        openai_client=create_openai_client(settings),
        langfuse_client=create_langfuse_client(settings),
    )

    try:
        result = run_pipeline(original_image_path, amendment_image_path, clients)
    except PipelineError as exc:
        print(f"Pipeline failed at stage '{exc.stage}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
