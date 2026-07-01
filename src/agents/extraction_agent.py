import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError
from pydantic import ValidationError

from src.config import (
    ExtractionSettings,
    create_extraction_llm,
    load_extraction_settings,
    load_settings,
)
from src.models import ContractChangeOutput

_BULLET_PREFIX = re.compile(r"^[\s]*[-*•]\s+", re.MULTILINE)
_NUMBERED_PREFIX = re.compile(r"^[\s]*\d+[.)]\s+", re.MULTILINE)
_MARKDOWN_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|__(.+?)__|\*(.+?)\*|_(.+?)_")
_WHITESPACE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{3,}")


class ExtractionAgentError(Exception):
    """Base error for extraction agent failures."""


class EmptyInputError(ExtractionAgentError):
    """Raised when a required input is empty."""


class ExtractionModelError(ExtractionAgentError):
    """Raised when the language model call fails."""


class ExtractionValidationError(ExtractionAgentError):
    """Raised when the model output cannot be validated."""


class ExtractionAgent:
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        agent_settings: ExtractionSettings | None = None,
    ) -> None:
        self._agent_settings = agent_settings or load_extraction_settings()
        if llm is None:
            settings = load_settings()
            self._llm = create_extraction_llm(settings, self._agent_settings)
        else:
            self._llm = llm

        self._structured_llm = self._llm.with_structured_output(ContractChangeOutput)

    def analyze(
        self,
        original_contract_text: str,
        amendment_contract_text: str,
        contextual_map: str,
    ) -> ContractChangeOutput:
        
        #Returns a Pydantic-validated result.
        self._validate_input(original_contract_text, "original contract")
        self._validate_input(amendment_contract_text, "amendment contract")
        self._validate_input(contextual_map, "contextual map")

        user_prompt = self._agent_settings.user_prompt_template.format(
            original_contract_text=original_contract_text.strip(),
            amendment_contract_text=amendment_contract_text.strip(),
            contextual_map=contextual_map.strip(),
        )

        messages = [
            SystemMessage(content=self._agent_settings.system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            result = self._structured_llm.invoke(messages)
        except RateLimitError as exc:
            raise ExtractionModelError(f"OpenAI rate limit exceeded: {exc}") from exc
        except APITimeoutError as exc:
            raise ExtractionModelError(f"OpenAI request timed out: {exc}") from exc
        except APIConnectionError as exc:
            raise ExtractionModelError(f"OpenAI connection error: {exc}") from exc
        except APIError as exc:
            raise ExtractionModelError(f"OpenAI API error: {exc}") from exc

        validated = self._validate_output(result)
        return self._normalize_output(validated)

    @staticmethod
    def _validate_input(value: str, label: str) -> None:
        if not value or not value.strip():
            raise EmptyInputError(f"The {label} is empty or contains only whitespace.")

    @staticmethod
    def _validate_output(result: object) -> ContractChangeOutput:
        if isinstance(result, ContractChangeOutput):
            return result

        try:
            return ContractChangeOutput.model_validate(result)
        except ValidationError as exc:
            raise ExtractionValidationError(
                f"Model output failed Pydantic validation: {exc}"
            ) from exc

    @staticmethod
    def _normalize_output(result: ContractChangeOutput) -> ContractChangeOutput:
        
        return ContractChangeOutput(
            sections_changed=result.sections_changed,
            topics_touched=ExtractionAgent._normalize_topics(result.topics_touched),
            summary_of_the_change=ExtractionAgent._sanitize_summary(
                result.summary_of_the_change
            ),
        )

    @staticmethod
    def _normalize_topics(topics: list[str]) -> list[str]:
        """Deduplicate topics and enforce consistent lowercase phrasing."""
        normalized: list[str] = []
        seen: set[str] = set()

        for topic in topics:
            cleaned = _WHITESPACE.sub(" ", topic.strip()).lower()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                normalized.append(cleaned)

        return normalized

    @staticmethod
    def _sanitize_summary(summary: str) -> str:
        
        text = summary.strip()
        text = _BULLET_PREFIX.sub("", text)
        text = _NUMBERED_PREFIX.sub("", text)
        text = _MARKDOWN_EMPHASIS.sub(
            lambda match: next(group for group in match.groups() if group), text
        )
        text = _BLANK_LINES.sub("\n\n", text)
        return text.strip()
