import json
import sys

from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from src.console_ui import console, err_console
from src.health_check import run_health_check
from src.input_validation import InputValidationError, validate_pipeline_inputs
from src.pipeline import PipelineError, create_pipeline_clients, run_pipeline

USAGE = "Usage: python -m src.main <original_image> <amendment_image>"


def _exit_with_error(stage: str, message: str) -> None:
    err_console.print(f"Error at stage '{stage}': {message}")
    sys.exit(1)


def _print_welcome(original_image_path: str, amendment_image_path: str) -> None:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="info", min_width=12)
    table.add_column(style="path")
    table.add_row("📄 Original", original_image_path)
    table.add_row("📄 Amendment", amendment_image_path)

    console.print()
    console.print(
        Panel(
            table,
            title="[title]Contract Amendment Analysis[/]",
            subtitle="[info]Comparing contract images[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def main() -> None:
    if len(sys.argv) == 1:
        run_health_check()
        console.print("[success]✅ Health check passed.[/]")
        return

    if len(sys.argv) != 3:
        err_console.print(USAGE)
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
        with console.status("[step]🤖 Analyzing contracts...[/]", spinner="dots"):
            result = run_pipeline(original_image_path, amendment_image_path, clients)
    except PipelineError as exc:
        _exit_with_error(exc.stage, exc.message)
    except Exception as exc:
        _exit_with_error("pipeline", f"An unexpected error occurred: {exc}")

    json_output = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    console.print(
        Panel(
            Syntax(json_output, "json", word_wrap=True, background_color="default"),
            title="[title]📄 Result[/]",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )


if __name__ == "__main__":
    main()
