"""Conjunto de avaliação da recuperação (Fase 3).

A régua que decide chunking, embeddings e busca híbrida: o gabarito das regras
(página, seção âncora e frase-marca), as consultas por regra e por achado de
P1–P7, e as métricas. Desenho:
`docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`.
"""

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from core.rules.base import Achado, RegraMeta
from rag.catalogo import RAIZ
from rag.consulta import montar_consulta
from rag.extracao import PaginaExtraida
from rag.texto import normalizar
from rag.urls import caminho_sem_idioma, normalizar_url

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


CABECALHO_CONSULTAS = (
    "# Gerado por `python -m rag.avaliacao gerar` — não editar à mão.\n"
    "# Frases-marca: eval/recuperacao/gabarito.yaml. Desenho:\n"
    "# docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md\n"
)


class Gabarito(FraseMarca):
    """A frase-marca com a página e a seção âncora deduzidas da base extraída."""

    id_pagina: str
    ancora: str


class Consulta(BaseModel):
    id: str
    tipo: Literal["regra", "achado"]
    projeto: str | None = None
    id_regra: str
    objeto: str | None = None
    texto: str


class ConjuntoAvaliacao(BaseModel):
    gabaritos: list[Gabarito]
    consultas: list[Consulta]


def id_da_pagina(url: str) -> str:
    """`https://learn.microsoft.com/en-us/power-bi/guidance/star-schema` →
    `learn:power-bi/guidance/star-schema`, o id do catálogo."""
    return "learn:" + caminho_sem_idioma(normalizar_url(url))


def deduzir_secao(pagina: PaginaExtraida, frase_marca: str, id_regra: str) -> str:
    """A única seção cujo texto contém a frase-marca. Os blocos da seção são
    unidos com espaço: a frase pode começar num parágrafo e terminar numa lista."""
    alvo = normalizar(frase_marca)
    achadas = [
        secao.ancora
        for secao in pagina.secoes
        if alvo in normalizar(" ".join(bloco.texto for bloco in secao.blocos))
    ]
    if not achadas:
        raise ErroDeAvaliacao(f"{id_regra}: frase-marca em nenhuma seção de {pagina.id}")
    if len(achadas) > 1:
        raise ErroDeAvaliacao(
            f"{id_regra}: frase-marca em mais de uma seção de {pagina.id}: {', '.join(achadas)}"
        )
    return achadas[0]


def gerar(
    *,
    metas: list[RegraMeta],
    frases: list[FraseMarca],
    ler_pagina: Callable[[str], PaginaExtraida],
    achados_por_projeto: dict[str, list[Achado]],
) -> ConjuntoAvaliacao:
    """Gabaritos deduzidos e consultas: uma por regra, depois uma por achado,
    projeto a projeto em ordem e, dentro do projeto, na ordem do runner."""
    por_id = {meta.id: meta for meta in metas}
    frase_de = {frase.id_regra: frase for frase in frases}
    sem_gabarito = sorted(set(por_id) - set(frase_de))
    if sem_gabarito:
        raise ErroDeAvaliacao(f"regra(s) sem gabarito: {', '.join(sem_gabarito)}")
    sem_regra = sorted(set(frase_de) - set(por_id))
    if sem_regra:
        raise ErroDeAvaliacao(f"gabarito de regra inexistente: {', '.join(sem_regra)}")

    gabaritos = []
    for id_regra in sorted(por_id):
        frase = frase_de[id_regra]
        id_pagina = id_da_pagina(por_id[id_regra].url_canonica)
        ancora = deduzir_secao(ler_pagina(id_pagina), frase.frase_marca, id_regra)
        gabaritos.append(
            Gabarito(
                id_regra=id_regra, frase_marca=frase.frase_marca, id_pagina=id_pagina, ancora=ancora
            )
        )

    consultas = [
        Consulta(id=f"REGRA/{id_regra}", tipo="regra", id_regra=id_regra, texto=montar_consulta(por_id[id_regra]))
        for id_regra in sorted(por_id)
    ]
    for projeto in sorted(achados_por_projeto):
        contagem: Counter[str] = Counter()
        for achado in achados_por_projeto[projeto]:
            meta = por_id.get(achado.id_regra)
            if meta is None:
                raise ErroDeAvaliacao(f"{projeto}: achado de regra fora do registro: {achado.id_regra}")
            contagem[achado.id_regra] += 1
            consultas.append(
                Consulta(
                    id=f"{projeto}/{achado.id_regra}/{contagem[achado.id_regra]}",
                    tipo="achado",
                    projeto=projeto,
                    id_regra=achado.id_regra,
                    objeto=achado.evidencia.objeto,
                    texto=montar_consulta(meta, achado),
                )
            )
    return ConjuntoAvaliacao(gabaritos=gabaritos, consultas=consultas)


def como_yaml(conjunto: ConjuntoAvaliacao) -> str:
    corpo = yaml.safe_dump(
        conjunto.model_dump(mode="json"), allow_unicode=True, sort_keys=False, width=1000
    )
    return CABECALHO_CONSULTAS + corpo


def ler_conjunto(caminho: Path) -> ConjuntoAvaliacao:
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"{caminho} não existe — rode `python -m rag.avaliacao gerar`")
    return ConjuntoAvaliacao.model_validate(yaml.safe_load(caminho.read_text(encoding="utf-8")))
