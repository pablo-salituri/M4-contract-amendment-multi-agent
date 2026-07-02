"""Pydantic models for contract amendment analysis output."""

from pydantic import BaseModel, Field


class ContractChangeOutput(BaseModel):
    sections_changed: list[str] = Field(
        description=(
            "Lista de claves semánticas en snake_case para secciones o temas "
            "con cambios confirmados en la enmienda "
            "(p. ej., duracion, canon_mensual, alcance_territorial)."
        )
    )
    topics_touched: list[str] = Field(
        description=(
            "Lista de frases descriptivas en español en minúsculas sobre los "
            "conceptos contractuales afectados "
            "(p. ej., duracion contractual, canon mensual de locacion, "
            "alcance territorial, restriccion de uso)."
        )
    )
    summary_of_the_change: str = Field(
        description=(
            "Resumen conciso en español de los cambios confirmados, "
            "indicando valores anteriores y nuevos cuando estén visibles "
            "en los textos."
        )
    )
