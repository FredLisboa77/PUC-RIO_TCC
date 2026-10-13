"""Contrato entre a geração e o resto do pipeline.

O achado enriquecido guarda o contexto inteiro, não só as citações: a Fase 5 e
a banca precisam ver o que o modelo tinha à disposição para julgar a citação.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.rules.base import Achado, RegraMeta

Origem = Literal["ancora", "busca"]
Situacao = Literal["gerado", "sem_fundamentacao", "so_regras"]
MotivoDescarte = Literal[
    "json_invalido", "campo_vazio", "citacoes_fora_do_limite", "citacao_inexistente", "erro_llm",
    "contexto_excedido",
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
    modelo: str | None
    """`None` só em `so_regras`, quando nenhum LLM foi chamado."""
    segundos: float | None = None
    """Tempo da chamada, sem a carga do modelo. `None` quando o LLM não respondeu."""
    tokens_prompt: int | None = None
    """O `prompt_eval_count` do Ollama: custo do achado em tokens."""
    reducoes_de_contexto: int = 0
    """Quantos trechos complementares saíram para o prompt caber no `num_ctx`. O
    `contexto` gravado é o que o modelo de fato leu, já reduzido."""

    @model_validator(mode="after")
    def _situacao_coerente(self) -> "AchadoEnriquecido":
        if self.situacao == "so_regras":
            # Auditoria sem LLM: só a detecção, sem nada que pareça geração.
            coerentes = (
                not self.contexto
                and self.geracao is None
                and self.motivo_descarte is None
                and self.cita_ancora is None
                and self.fidelidade is None
                and self.modelo is None
                and self.segundos is None
                and self.tokens_prompt is None
            )
        else:
            gerado = self.situacao == "gerado"
            coerentes = (
                (self.geracao is not None) == gerado
                and (self.motivo_descarte is None) == gerado
                and (self.cita_ancora is not None) == gerado
                and (self.fidelidade is not None) == gerado
                and self.modelo is not None
            )
        if not coerentes:
            raise ValueError(
                f"achado enriquecido incoerente: situação {self.situacao} com geração, motivo, "
                "cita_ancora, fidelidade e modelo que não batem"
            )
        return self

    @classmethod
    def so_regras(cls, achado: Achado) -> "AchadoEnriquecido":
        """O achado de uma auditoria sem LLM, escolhida pelo usuário: a recomendação
        que sai é a padrão do catálogo, e o resultado é rotulado assim (spec de 13/10)."""
        return cls(achado=achado, contexto=[], situacao="so_regras", modelo=None)

    def recomendacao_final(self, meta: RegraMeta) -> str:
        """A recomendação que o relatório mostra. Método e não propriedade porque o
        achado guarda só o `id_regra`: a recomendação padrão vem do catálogo."""
        if meta.id != self.achado.id_regra:
            raise ValueError(f"meta da regra {meta.id} para um achado da regra {self.achado.id_regra}")
        if self.geracao is not None:
            return self.geracao.recomendacao
        return meta.recomendacao_padrao
