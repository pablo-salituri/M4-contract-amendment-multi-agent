import json
import sys

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
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

    if len(sys.argv) == 2:
        image_path = sys.argv[1]
        print(f"\nParsing contract image: {image_path}")
        extracted_text = parse_contract_image(image_path, openai_client=openai_client)
        print("\n--- Extracted text ---\n")
        print(extracted_text)

    elif len(sys.argv) == 3:
        original_path, amendment_path = sys.argv[1], sys.argv[2]
        print(f"\nParsing original contract: {original_path}")
        original_text = parse_contract_image(original_path, openai_client=openai_client)
        print(f"Parsing amendment contract: {amendment_path}")
        amendment_text = parse_contract_image(amendment_path, openai_client=openai_client)

        print("\nBuilding contextual map...")
        context_agent = ContextualizationAgent()
        context_map = context_agent.analyze(original_text, amendment_text)
        print("\n--- Contextual map ---\n")
        print(context_map)

        print("\nExtracting contract changes...")
        extraction_agent = ExtractionAgent()
        result = extraction_agent.analyze(original_text, amendment_text, context_map)
        print("\n--- Validated output ---\n")
        print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
