"""Contract amendment analysis pipeline with Langfuse instrumentation."""

from dataclasses import dataclass

from langfuse import Langfuse
from openai import OpenAI

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.image_parser import ImageParserError, parse_contract_image
from src.models import ContractChangeOutput

TRACE_NAME = "contract-analysis"
TEXT_PREVIEW_LENGTH = 500


@dataclass(frozen=True)
class PipelineClients:
    openai_client: OpenAI
    langfuse_client: Langfuse


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"[{stage}] {message}")


def _text_preview(text: str) -> str:
    if len(text) <= TEXT_PREVIEW_LENGTH:
        return text
    return f"{text[:TEXT_PREVIEW_LENGTH]}..."


def _record_stage_error(span: object, exc: Exception) -> None:
    span.update(
        level="ERROR",
        status_message=str(exc),
        output={"error_type": type(exc).__name__},
    )


def run_pipeline(
    original_image_path: str,
    amendment_image_path: str,
    clients: PipelineClients,
) -> ContractChangeOutput:
    """Run the full contract analysis pipeline and return validated output."""
    langfuse = clients.langfuse_client

    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name=TRACE_NAME,
            input={
                "original_image_path": original_image_path,
                "amendment_image_path": amendment_image_path,
            },
        ) as root_span:
            original_text = _parse_original_contract(
                langfuse, clients.openai_client, original_image_path
            )
            amendment_text = _parse_amendment_contract(
                langfuse, clients.openai_client, amendment_image_path
            )
            context_map = _run_contextualization(
                langfuse, original_text, amendment_text
            )
            result = _run_extraction(
                langfuse, original_text, amendment_text, context_map
            )

            root_span.update(output=result.model_dump())
            return result
    finally:
        langfuse.flush()


def _parse_original_contract(
    langfuse: Langfuse,
    openai_client: OpenAI,
    image_path: str,
) -> str:
    with langfuse.start_as_current_observation(
        as_type="span",
        name="parse_original_contract",
        input={"image_path": image_path},
    ) as span:
        try:
            text = parse_contract_image(image_path, openai_client=openai_client)
        except ImageParserError as exc:
            _record_stage_error(span, exc)
            raise PipelineError("parse_original_contract", str(exc)) from exc

        span.update(
            output={
                "text_length": len(text),
                "text_preview": _text_preview(text),
            }
        )
        return text


def _parse_amendment_contract(
    langfuse: Langfuse,
    openai_client: OpenAI,
    image_path: str,
) -> str:
    with langfuse.start_as_current_observation(
        as_type="span",
        name="parse_amendment_contract",
        input={"image_path": image_path},
    ) as span:
        try:
            text = parse_contract_image(image_path, openai_client=openai_client)
        except ImageParserError as exc:
            _record_stage_error(span, exc)
            raise PipelineError("parse_amendment_contract", str(exc)) from exc

        span.update(
            output={
                "text_length": len(text),
                "text_preview": _text_preview(text),
            }
        )
        return text


def _run_contextualization(
    langfuse: Langfuse,
    original_text: str,
    amendment_text: str,
) -> str:
    with langfuse.start_as_current_observation(
        as_type="span",
        name="contextualization_agent",
        input={
            "original_text_length": len(original_text),
            "amendment_text_length": len(amendment_text),
        },
    ) as span:
        agent = ContextualizationAgent()
        try:
            context_map = agent.analyze(original_text, amendment_text)
        except Exception as exc:
            _record_stage_error(span, exc)
            raise PipelineError("contextualization_agent", str(exc)) from exc

        span.update(
            output={
                "context_map_length": len(context_map),
                "context_map_preview": _text_preview(context_map),
            }
        )
        return context_map


def _run_extraction(
    langfuse: Langfuse,
    original_text: str,
    amendment_text: str,
    context_map: str,
) -> ContractChangeOutput:
    with langfuse.start_as_current_observation(
        as_type="span",
        name="extraction_agent",
        input={
            "original_text_length": len(original_text),
            "amendment_text_length": len(amendment_text),
            "context_map_length": len(context_map),
        },
    ) as span:
        agent = ExtractionAgent()
        try:
            result = agent.analyze(original_text, amendment_text, context_map)
        except Exception as exc:
            _record_stage_error(span, exc)
            raise PipelineError("extraction_agent", str(exc)) from exc

        span.update(output=result.model_dump())
        return result
