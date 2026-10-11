"""Conjunto de avaliação da recuperação (Fase 3).

A régua que decide chunking, embeddings e busca híbrida: o gabarito das regras
(página, seção âncora e frase-marca), as consultas por regra e por achado de
P1–P7, e as métricas. Desenho:
`docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

from rag.catalogo import RAIZ

RAIZ_REPO = RAIZ.parent
PASTA_AVALIACAO = RAIZ_REPO / "eval" / "recuperacao"
ARQUIVO_GABARITO = PASTA_AVALIACAO / "gabarito.yaml"
ARQUIVO_CONSULTAS = PASTA_AVALIACAO / "consultas.yaml"


class ErroDeAvaliacao(Exception):
    """O conjunto não pode ser gerado ou medido sem perder algo em silêncio."""


class FraseMarca(BaseModel):
    """Escrita à mão: um trecho curto da passagem que a regra cita."""

    id_regra: str
    frase_marca: str


def ler_frases_marca(caminho: Path) -> list[FraseMarca]:
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"{caminho} não existe")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    frases = [FraseMarca.model_validate(d) for d in dados]
    vistos: set[str] = set()
    for frase in frases:
        if frase.id_regra in vistos:
            raise ErroDeAvaliacao(f"{frase.id_regra} aparece mais de uma vez em {caminho.name}")
        vistos.add(frase.id_regra)
    return sorted(frases, key=lambda f: f.id_regra)
