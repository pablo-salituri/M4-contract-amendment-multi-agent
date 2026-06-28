"""Contract amendment analysis pipeline with Langfuse instrumentation."""

from dataclasses import dataclass

from langfuse import Langfuse
from openai import OpenAI

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.config import (
    PIPELINE_VERSION,
    PROJECT_NAME,
    ContextualizationSettings,
    ExtractionSettings,
    Settings,
    VisionSettings,
    create_contextualization_llm,
    create_extraction_llm,
    create_langfuse_client,
    create_openai_client,
    load_contextualization_settings,
    load_extraction_settings,
    load_settings,
    load_vision_settings,
)
from src.image_parser import ImageParserError, parse_contract_image
from src.input_validation import InputValidationError, validate_pipeline_inputs
from src.models import ContractChangeOutput

TRACE_NAME = "contract-analysis"
TEXT_PREVIEW_LENGTH = 500


@dataclass(frozen=True)
class PipelineClients:
    openai_client: OpenAI
    langfuse_client: Langfuse
    contextualization_agent: ContextualizationAgent
    extraction_agent: ExtractionAgent


class PipelineError(Exception):
    """Raised when a pipeline stage fails."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


def create_pipeline_clients(settings: Settings | None = None) -> PipelineClients:
    """Create reusable clients and agents for a pipeline run."""
    resolved_settings = settings or load_settings()
    contextualization_settings = load_contextualization_settings()
    extraction_settings = load_extraction_settings()

    return PipelineClients(
        openai_client=create_openai_client(resolved_settings),
        langfuse_client=create_langfuse_client(resolved_settings),
        contextualization_agent=ContextualizationAgent(
            llm=create_contextualization_llm(
                resolved_settings, contextualization_settings
            ),
            agent_settings=contextualization_settings,
        ),
        extraction_agent=ExtractionAgent(
            llm=create_extraction_llm(resolved_settings, extraction_settings),
            agent_settings=extraction_settings,
        ),
    )


def _build_stage_metadata(
    stage: str,
    model: str,
    temperature: float,
) -> dict[str, str | float]:
    return {
        "project_name": PROJECT_NAME,
        "pipeline_version": PIPELINE_VERSION,
        "stage": stage,
        "model": model,
        "temperature": temperature,
    }


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
    try:
        validate_pipeline_inputs(original_image_path, amendment_image_path)
    except InputValidationError as exc:
        raise PipelineError(exc.stage, exc.message) from exc

    langfuse = clients.langfuse_client
    vision_settings = load_vision_settings()
    contextualization_settings = load_contextualization_settings()
    extraction_settings = load_extraction_settings()

    root_metadata = {
        "project_name": PROJECT_NAME,
        "pipeline_version": PIPELINE_VERSION,
        "stage": "pipeline",
    }

    try:
        with langfuse.start_as_current_observation(
            as_type="span",
            name=TRACE_NAME,
            input={
                "original_image_path": original_image_path,
                "amendment_image_path": amendment_image_path,
            },
            metadata=root_metadata,
            version=PIPELINE_VERSION,
        ) as root_span:
            original_text = _parse_original_contract(
                langfuse,
                clients.openai_client,
                original_image_path,
                vision_settings,
            )
            amendment_text = _parse_amendment_contract(
                langfuse,
                clients.openai_client,
                amendment_image_path,
                vision_settings,
            )
            context_map = _run_contextualization(
                langfuse,
                clients.contextualization_agent,
                original_text,
                amendment_text,
                contextualization_settings,
            )
            result = _run_extraction(
                langfuse,
                clients.extraction_agent,
                original_text,
                amendment_text,
                context_map,
                extraction_settings,
            )

            root_span.update(output=result.model_dump())
            return result
    finally:
        langfuse.flush()


def _parse_original_contract(
    langfuse: Langfuse,
    openai_client: OpenAI,
    image_path: str,
    vision_settings: VisionSettings,
) -> str:
    stage = "parse_original_contract"
    with langfuse.start_as_current_observation(
        as_type="span",
        name=stage,
        input={"image_path": image_path},
        metadata=_build_stage_metadata(
            stage,
            vision_settings.model,
            vision_settings.temperature,
        ),
        model=vision_settings.model,
        model_parameters={"temperature": vision_settings.temperature},
    ) as span:
        try:
            text = parse_contract_image(
                image_path,
                openai_client=openai_client,
                vision_settings=vision_settings,
            )
        except ImageParserError as exc:
            _record_stage_error(span, exc)
            raise PipelineError(stage, str(exc)) from exc

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
    vision_settings: VisionSettings,
) -> str:
    stage = "parse_amendment_contract"
    with langfuse.start_as_current_observation(
        as_type="span",
        name=stage,
        input={"image_path": image_path},
        metadata=_build_stage_metadata(
            stage,
            vision_settings.model,
            vision_settings.temperature,
        ),
        model=vision_settings.model,
        model_parameters={"temperature": vision_settings.temperature},
    ) as span:
        try:
            text = parse_contract_image(
                image_path,
                openai_client=openai_client,
                vision_settings=vision_settings,
            )
        except ImageParserError as exc:
            _record_stage_error(span, exc)
            raise PipelineError(stage, str(exc)) from exc

        span.update(
            output={
                "text_length": len(text),
                "text_preview": _text_preview(text),
            }
        )
        return text


def _run_contextualization(
    langfuse: Langfuse,
    agent: ContextualizationAgent,
    original_text: str,
    amendment_text: str,
    agent_settings: ContextualizationSettings,
) -> str:
    stage = "contextualization_agent"
    with langfuse.start_as_current_observation(
        as_type="span",
        name=stage,
        input={
            "original_text_length": len(original_text),
            "amendment_text_length": len(amendment_text),
        },
        metadata=_build_stage_metadata(
            stage,
            agent_settings.model,
            agent_settings.temperature,
        ),
        model=agent_settings.model,
        model_parameters={"temperature": agent_settings.temperature},
    ) as span:
        try:
            context_map = agent.analyze(original_text, amendment_text)
        except Exception as exc:
            _record_stage_error(span, exc)
            raise PipelineError(stage, str(exc)) from exc

        span.update(
            output={
                "context_map_length": len(context_map),
                "context_map_preview": _text_preview(context_map),
            }
        )
        return context_map


def _run_extraction(
    langfuse: Langfuse,
    agent: ExtractionAgent,
    original_text: str,
    amendment_text: str,
    context_map: str,
    agent_settings: ExtractionSettings,
) -> ContractChangeOutput:
    stage = "extraction_agent"
    with langfuse.start_as_current_observation(
        as_type="span",
        name=stage,
        input={
            "original_text_length": len(original_text),
            "amendment_text_length": len(amendment_text),
            "context_map_length": len(context_map),
        },
        metadata=_build_stage_metadata(
            stage,
            agent_settings.model,
            agent_settings.temperature,
        ),
        model=agent_settings.model,
        model_parameters={"temperature": agent_settings.temperature},
    ) as span:
        try:
            result = agent.analyze(original_text, amendment_text, context_map)
        except Exception as exc:
            _record_stage_error(span, exc)
            raise PipelineError(stage, str(exc)) from exc

        span.update(output=result.model_dump())
        return result
