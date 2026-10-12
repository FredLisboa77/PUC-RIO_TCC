"""Contrato entre a geração e o resto do pipeline.

O achado enriquecido guarda o contexto inteiro, não só as citações: a Fase 5 e
a banca precisam ver o que o modelo tinha à disposição para julgar a citação.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.rules.base import Achado, RegraMeta

Origem = Literal["ancora", "busca"]
Situacao = Literal["gerado", "sem_fundamentacao"]
MotivoDescarte = Literal[
    "json_invalido", "campo_vazio", "citacoes_fora_do_limite", "citacao_inexistente", "erro_llm"
]


class TrechoDeContexto(BaseModel):
    """Um trecho entregue ao LLM, com o número pelo qual ele é citado."""

    numero: int
    id_pagina: str
    url: str
    titulo: str
    ancora: str
    caminho: str
    texto: str
    origem: Origem
    """`ancora` é sempre o número 1 (emenda de 09/10 da ADR-002)."""


class Geracao(BaseModel):
    explicacao: str
    recomendacao: str
    citacoes: list[int]


class Fidelidade(BaseModel):
    divergencias: list[str] = Field(default_factory=list)
    """Números e nomes da resposta que não aparecem no achado nem nos trechos.
    Vazia = sem divergência. Registra, não descarta: a heurística ainda não está
    calibrada para ser portão."""


class AchadoEnriquecido(BaseModel):
    achado: Achado
    contexto: list[TrechoDeContexto]
    geracao: Geracao | None = None
    situacao: Situacao
    motivo_descarte: MotivoDescarte | None = None
    cita_ancora: bool | None = None
    """Pertinência automática: o trecho âncora está entre as citações."""
    fidelidade: Fidelidade | None = None
    modelo: str
    segundos: float | None = None
    """Tempo da chamada, sem a carga do modelo. `None` quando o LLM não respondeu."""

    @model_validator(mode="after")
    def _situacao_coerente(self) -> "AchadoEnriquecido":
        gerado = self.situacao == "gerado"
        coerentes = (
            (self.geracao is not None) == gerado
            and (self.motivo_descarte is None) == gerado
            and (self.cita_ancora is not None) == gerado
            and (self.fidelidade is not None) == gerado
        )
        if not coerentes:
            raise ValueError(
                f"achado enriquecido incoerente: situação {self.situacao} com geração, motivo, "
                "cita_ancora e fidelidade que não batem"
            )
        return self

    def recomendacao_final(self, meta: RegraMeta) -> str:
        """A recomendação que o relatório mostra. Método e não propriedade porque o
        achado guarda só o `id_regra`: a recomendação padrão vem do catálogo."""
        if meta.id != self.achado.id_regra:
            raise ValueError(f"meta da regra {meta.id} para um achado da regra {self.achado.id_regra}")
        if self.geracao is not None:
            return self.geracao.recomendacao
        return meta.recomendacao_padrao
