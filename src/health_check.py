import sys

from src.config import (
    PROJECT_ROOT,
    Settings,
    create_langfuse_client,
    load_settings,
)

_TOTAL_STEPS = 5


def run_health_check() -> None:
    print("Running health check...")
    _check_env_file()
    settings = _check_required_settings()
    _check_openai_api_key(settings)
    _check_langfuse_configuration(settings)
    print("All health checks completed successfully.")


def _step_start(step: int, description: str) -> None:
    print(f"[{step}/{_TOTAL_STEPS}] {description}...", end=" ", flush=True)


def _step_ok(detail: str | None = None) -> None:
    if detail:
        print(f"OK ({detail})")
    else:
        print("OK")


def _step_fail(step: int, description: str, message: str) -> None:
    print("FAILED")
    print(
        f"Health check failed at step [{step}/{_TOTAL_STEPS}] {description}: {message}",
        file=sys.stderr,
    )
    sys.exit(1)


def _check_env_file() -> None:
    step = 1
    description = "Checking .env file"
    _step_start(step, description)

    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        _step_fail(
            step,
            description,
            f".env file not found at '{env_path}'. "
            "Copy .env.example to .env and fill in your credentials.",
        )

    _step_ok(str(env_path))


def _check_required_settings() -> Settings:
    step = 2
    description = "Loading required environment variables"
    _step_start(step, description)

    try:
        settings = load_settings()
    except ValueError as exc:
        _step_fail(step, description, str(exc))

    _step_ok("OPENAI_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST")
    return settings


def _check_openai_api_key(settings: Settings) -> None:
    step = 3
    description = "Validating OpenAI API key"
    _step_start(step, description)

    api_key = settings.openai_api_key.strip()
    if not api_key:
        _step_fail(step, description, "OPENAI_API_KEY is empty.")
    if api_key == "your-openai-api-key":
        _step_fail(
            step,
            description,
            "OPENAI_API_KEY still contains the placeholder value from .env.example.",
        )

    _step_ok()


def _check_langfuse_configuration(settings: Settings) -> None:
    step = 4
    description = "Validating Langfuse credentials"
    _step_start(step, description)

    public_key = settings.langfuse_public_key.strip()
    secret_key = settings.langfuse_secret_key.strip()
    host = settings.langfuse_host.strip()

    if not public_key or public_key == "your-langfuse-public-key":
        _step_fail(
            step,
            description,
            "LANGFUSE_PUBLIC_KEY is missing or still contains the placeholder value.",
        )
    if not secret_key or secret_key == "your-langfuse-secret-key":
        _step_fail(
            step,
            description,
            "LANGFUSE_SECRET_KEY is missing or still contains the placeholder value.",
        )
    if not host:
        _step_fail(step, description, "LANGFUSE_HOST is empty.")

    _step_ok(f"host={host}")

    step = 5
    description = "Checking Langfuse connectivity"
    _step_start(step, description)

    langfuse_client = create_langfuse_client(settings)
    try:
        if not langfuse_client.auth_check():
            _step_fail(
                step,
                description,
                f"Unable to authenticate with Langfuse at '{host}'. "
                "Verify LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and LANGFUSE_HOST.",
            )
    except Exception as exc:
        _step_fail(
            step,
            description,
            f"Unable to reach Langfuse at '{host}': {exc}. "
            "Verify LANGFUSE_HOST and network connectivity.",
        )

    _step_ok(f"authenticated against {host}")
