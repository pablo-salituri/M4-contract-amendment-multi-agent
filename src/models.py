"""Pydantic models for contract amendment analysis output."""

from pydantic import BaseModel, Field


class ContractChangeOutput(BaseModel):
    """Structured output describing changes introduced by a contract amendment."""

    sections_changed: list[str] = Field(
        description=(
            "List of section identifiers or titles that were added, removed, "
            "or modified in the amendment."
        )
    )
    topics_touched: list[str] = Field(
        description=(
            "List of contract topics affected by the amendment "
            "(e.g., payment, term, parties, termination, liability)."
        )
    )
    summary_of_the_change: str = Field(
        description=(
            "Concise summary of all changes, explicitly distinguishing "
            "additions, deletions, and modifications."
        )
    )
