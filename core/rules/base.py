"""Contrato entre as regras e o resto do pipeline.

Três objetos. `RegraMeta` descreve a regra e vive no catálogo; `Evidencia`
descreve o objeto problemático e o que a regra leu para afirmar isso; `Achado`
liga os dois.

O achado guarda apenas o `id_regra`, nunca uma cópia dos metadados. O catálogo
é fonte única de verdade: é dele que sai a tabela de regras da monografia, e
nenhum achado pode divergir dele.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Categoria = Literal["modelagem", "performance", "dax", "m"]
Severidade = Literal["alta", "media", "baixa"]
TipoObjeto = Literal[
    "tabela", "coluna", "medida", "relacionamento", "particao", "modelo"
]

ORDEM_SEVERIDADE: dict[str, int] = {"alta": 0, "media": 1, "baixa": 2}

TAMANHO_MINIMO_RECOMENDACAO = 40
"""Uma recomendação padrão curta demais é um rótulo, não uma orientação. Ela sai
no relatório quando a geração do LLM é descartada (ADR-003), então é a única
coisa que o leitor recebe nesse caso."""


class RegraMeta(BaseModel):
    """Metadados de uma regra. Imutável: o catálogo não muda em execução."""

    model_config = {"frozen": True}

    id: str
    titulo: str
    categoria: Categoria
    severidade: Severidade
    url_canonica: str
    """A página da documentação oficial que sustenta o achado. A Fase 5 compara
    a citação escolhida pelo LLM com esta URL para medir pertinência."""
    termos_consulta: tuple[str, ...]
    """Termos de busca em inglês, para a recuperação com `bge-small-en`."""
    recomendacao_padrao: str
    """Precisa conter as exceções que a própria fonte declara."""
    nota_de_verificacao: str | None = None
    """Ressalva sobre a detecção, quando houver pendência empírica."""

    @field_validator("url_canonica")
    @classmethod
    def _precisa_ser_url(cls, valor: str) -> str:
        if not valor.startswith("https://"):
            raise ValueError(
                "url_canonica precisa ser uma URL https da documentação oficial"
            )
        return valor

    @field_validator("termos_consulta")
    @classmethod
    def _precisa_ter_termos(cls, valor: tuple[str, ...]) -> tuple[str, ...]:
        if not valor:
            raise ValueError(
                "termos_consulta não pode ser vazio: a Fase 3 recupera por eles"
            )
        return valor

    @field_validator("recomendacao_padrao")
    @classmethod
    def _precisa_ter_texto(cls, valor: str) -> str:
        if len(valor.strip()) < TAMANHO_MINIMO_RECOMENDACAO:
            raise ValueError(
                "recomendacao_padrao precisa de pelo menos "
                f"{TAMANHO_MINIMO_RECOMENDACAO} caracteres de texto útil"
            )
        return valor


class Evidencia(BaseModel):
    """Onde está o problema, e o que a regra leu para afirmar isso."""

    tipo_objeto: TipoObjeto
    objeto: str
    """Nome qualificado: `DimProduct[ProductKey]` numa coluna."""
    tabela: str | None = None
    trecho: str | None = None
    """O DAX, o M ou a propriedade TMSL lida."""
    detalhe: dict[str, Any] = Field(default_factory=dict)
    """Os valores que a regra de fato leu."""


class Achado(BaseModel):
    """Uma ocorrência. Um achado por objeto violador, nunca agregado."""

    id_regra: str
    evidencia: Evidencia
    mensagem: str
    """A frase da ocorrência específica, escrita pela regra."""
