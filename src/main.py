import sys

from src.config import (
    create_langfuse_client,
    create_openai_client,
    load_settings,
)
from src.image_parser import parse_contract_image


def main() -> None:
    settings = load_settings()
    openai_client = create_openai_client(settings)
    langfuse_client = create_langfuse_client(settings)

    print("Project initialized successfully.")
    print(f"  OpenAI client: {type(openai_client).__name__}")
    print(f"  Langfuse client: {type(langfuse_client).__name__}")
    print(f"  Langfuse host: {settings.langfuse_host}")

    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        print(f"\nParsing contract image: {image_path}")
        extracted_text = parse_contract_image(image_path)
        print("\n--- Extracted text ---\n")
        print(extracted_text)


if __name__ == "__main__":
    main()
