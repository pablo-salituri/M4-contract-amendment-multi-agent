from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from src.config import (
    ContextualizationSettings,
    create_contextualization_llm,
    load_contextualization_settings,
    load_settings,
)


class ContextualizationAgentError(Exception):
    """Base error for contextualization agent failures."""


class EmptyContractTextError(ContextualizationAgentError):
    """Raised when a contract text input is empty."""


class ContextualizationModelError(ContextualizationAgentError):
    """Raised when the language model call fails."""


class EmptyContextMapError(ContextualizationAgentError):
    """Raised when the model returns an empty contextual map."""


class ContextualizationAgent:
    def __init__(
        self,
        llm: BaseChatModel | None = None,
        agent_settings: ContextualizationSettings | None = None,
    ) -> None:
        self._agent_settings = agent_settings or load_contextualization_settings()
        if llm is None:
            settings = load_settings()
            self._llm = create_contextualization_llm(settings, self._agent_settings)
        else:
            self._llm = llm

    def analyze(
        self,
        original_contract_text: str,
        amendment_contract_text: str,
    ) -> str:
        
        self._validate_contract_text(original_contract_text, "original")
        self._validate_contract_text(amendment_contract_text, "amendment")

        user_prompt = self._agent_settings.user_prompt_template.format(
            original_contract_text=original_contract_text.strip(),
            amendment_contract_text=amendment_contract_text.strip(),
        )

        try:
            response = self._llm.invoke(
                [
                    SystemMessage(content=self._agent_settings.system_prompt),
                    HumanMessage(content=user_prompt),
                ]
            )
        except RateLimitError as exc:
            raise ContextualizationModelError(
                f"OpenAI rate limit exceeded: {exc}"
            ) from exc
        except APITimeoutError as exc:
            raise ContextualizationModelError(
                f"OpenAI request timed out: {exc}"
            ) from exc
        except APIConnectionError as exc:
            raise ContextualizationModelError(
                f"OpenAI connection error: {exc}"
            ) from exc
        except APIError as exc:
            raise ContextualizationModelError(f"OpenAI API error: {exc}") from exc

        content = response.content
        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            context_map = "\n".join(part.strip() for part in text_parts if part.strip())
        else:
            context_map = str(content).strip()

        if not context_map:
            raise EmptyContextMapError("Model returned an empty contextual map.")

        return context_map

    @staticmethod
    def _validate_contract_text(contract_text: str, label: str) -> None:
        if not contract_text or not contract_text.strip():
            raise EmptyContractTextError(
                f"The {label} contract text is empty or contains only whitespace."
            )
