from src.config import (
    create_langfuse_client,
    create_openai_client,
    load_settings,
)


def main() -> None:
    settings = load_settings()
    openai_client = create_openai_client(settings)
    langfuse_client = create_langfuse_client(settings)

    print("Project initialized successfully.")
    print(f"  OpenAI client: {type(openai_client).__name__}")
    print(f"  Langfuse client: {type(langfuse_client).__name__}")
    print(f"  Langfuse host: {settings.langfuse_host}")


if __name__ == "__main__":
    main()
