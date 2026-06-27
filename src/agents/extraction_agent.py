"""Extraction agent for identifying contract amendment changes."""

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


class ExtractionAgentError(Exception):
    """Base error for extraction agent failures."""


class EmptyInputError(ExtractionAgentError):
    """Raised when a required input is empty."""


class ExtractionModelError(ExtractionAgentError):
    """Raised when the language model call fails."""


class ExtractionValidationError(ExtractionAgentError):
    """Raised when the model output cannot be validated."""


class ExtractionAgent:
    """Identifies contract changes using a contextual map and returns validated output."""

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
        """Identify amendment changes and return a Pydantic-validated result."""
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

        return self._validate_output(result)

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
