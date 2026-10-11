"""Medição da recuperação (Fase 3).

Mede as 24 combinações de chunking, cabeçalho, busca e corpus com a régua
congelada e escolhe a vencedora pela regra fixada antes de medir. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 5.
"""

from typing import Literal

import numpy as np
from pydantic import BaseModel

from rag.avaliacao import ConjuntoAvaliacao, Metricas, ResultadoConsulta, avaliar
from rag.busca import IndiceBm25, TipoBusca, criar_buscador
from rag.chunking import Estrategia, TrechoIndexado
from rag.embeddings import Embedder
from rag.texto import normalizar

MARGEM = 1 / 9
"""Uma regra em nove: diferença menor que isso é ruído nesta régua."""
_EPS = 1e-9
TipoCorpus = Literal["completo", "guidance"]
_ORDEM_BUSCA = {"densa": 0, "bm25": 1, "hibrida": 2}


class ErroDeMedicao(Exception):
    """A medição não pode seguir sem medir algo errado."""


class Configuracao(BaseModel):
    model_config = {"frozen": True}

    chunking: Estrategia
    cabecalho: bool
    busca: TipoBusca
    corpus: TipoCorpus

    @property
    def variante(self) -> str:
        return f"{self.chunking}-{'com' if self.cabecalho else 'sem'}"

    @property
    def nome(self) -> str:
        return f"{self.variante}-{self.busca}-{self.corpus}"

    @property
    def complexidade(self) -> int:
        return int(self.busca == "hibrida") + int(self.chunking == "janela") + int(self.cabecalho)


GRADE = [
    Configuracao(chunking=chunking, cabecalho=cabecalho, busca=busca, corpus=corpus)
    for chunking in ("secao", "janela")
    for cabecalho in (False, True)
    for busca in ("densa", "bm25", "hibrida")
    for corpus in ("completo", "guidance")
]


class ResultadoConfiguracao(BaseModel):
    configuracao: Configuracao
    macro: Metricas
    micro: Metricas
    por_tipo: dict[str, Metricas]
    por_regra: dict[str, Metricas]
    erros: list[ResultadoConsulta]


class Decisao(BaseModel):
    vencedora: Configuracao
    empatadas: list[str]
    justificativa: str
    aviso_corpus: str | None = None


def verificar_oraculo(trechos: list[TrechoIndexado], conjunto: ConjuntoAvaliacao) -> list[str]:
    """Regras cuja frase-marca não está inteira em nenhum trecho da página âncora.
    Lista vazia = o chunking não parte nenhuma frase-marca."""
    falhas = []
    for gabarito in conjunto.gabaritos:
        alvo = normalizar(gabarito.frase_marca)
        if not any(t.id_pagina == gabarito.id_pagina and alvo in normalizar(t.texto) for t in trechos):
            falhas.append(gabarito.id_regra)
    return falhas


def medir(
    conjunto: ConjuntoAvaliacao,
    *,
    trechos: dict[str, list[TrechoIndexado]],
    vetores: dict[str, np.ndarray],
    embedder: Embedder,
    paginas_guidance: frozenset[str],
    grade: list[Configuracao] = GRADE,
) -> list[ResultadoConfiguracao]:
    indices_bm25: dict[str, IndiceBm25] = {}
    resultados = []
    for configuracao in grade:
        variante = configuracao.variante
        if configuracao.busca != "densa" and variante not in indices_bm25:
            indices_bm25[variante] = IndiceBm25([t.texto_indexado for t in trechos[variante]])
        buscar = criar_buscador(
            configuracao.busca,
            trechos[variante],
            vetores=vetores.get(variante),
            embedder=embedder,
            indice_bm25=indices_bm25.get(variante),
            paginas=paginas_guidance if configuracao.corpus == "guidance" else None,
        )
        relatorio = avaliar(buscar, conjunto)
        resultados.append(
            ResultadoConfiguracao(
                configuracao=configuracao,
                macro=relatorio.macro,
                micro=relatorio.micro,
                por_tipo=relatorio.por_tipo,
                por_regra=relatorio.por_regra,
                erros=relatorio.erros,
            )
        )
    return resultados


def _chave_de_simplicidade(r: ResultadoConfiguracao) -> tuple:
    c = r.configuracao
    return (c.complexidade, -r.macro.mrr, _ORDEM_BUSCA[c.busca], c.chunking != "secao", c.cabecalho)


def decidir(resultados: list[ResultadoConfiguracao]) -> Decisao:
    candidatas = [r for r in resultados if r.configuracao.corpus == "completo"]
    if not candidatas:
        raise ErroDeMedicao("nenhuma combinação do corpus completo foi medida")
    melhor = max(r.macro.acerto[5] for r in candidatas)
    empatadas = [r for r in candidatas if melhor - r.macro.acerto[5] < MARGEM - _EPS]
    vencedora = min(empatadas, key=_chave_de_simplicidade)
    justificativa = (
        f"maior macro acerto@5 do corpus completo = {melhor:.3f}; {len(empatadas)} combinação(ões) a menos "
        f"de 1/9 dela; vence a de menor complexidade ({vencedora.configuracao.complexidade}), "
        f"desempate por macro MRR@10 e pela ordem fixa"
    )
    aviso = None
    guidance = [r for r in resultados if r.configuracao.corpus == "guidance"]
    if guidance:
        melhor_guidance = max(guidance, key=lambda r: r.macro.acerto[5])
        if melhor_guidance.macro.acerto[5] - melhor >= MARGEM - _EPS:
            aviso = (
                f"o corpus guidance ({melhor_guidance.configuracao.nome}, macro acerto@5 "
                f"{melhor_guidance.macro.acerto[5]:.3f}) supera o completo ({melhor:.3f}) por 1/9 ou mais: "
                f"a decisão sobre o corpus é do Fred"
            )
    return Decisao(
        vencedora=vencedora.configuracao,
        empatadas=[r.configuracao.nome for r in empatadas],
        justificativa=justificativa,
        aviso_corpus=aviso,
    )


def formatar_tabela(resultados: list[ResultadoConfiguracao], decisao: Decisao) -> str:
    cabecalho = (
        f"{'':2}{'combinação':34} {'@1':>6} {'@3':>6} {'@5':>6} {'@10':>6} {'MRR':>6} "
        f"{'micro@5':>8} {'regra@5':>8} {'achado@5':>9}"
    )
    linhas = [cabecalho]
    for r in resultados:
        marca = "* " if r.configuracao == decisao.vencedora else "  "
        m = r.macro
        linhas.append(
            f"{marca}{r.configuracao.nome:34} {m.acerto[1]:6.3f} {m.acerto[3]:6.3f} {m.acerto[5]:6.3f} "
            f"{m.acerto[10]:6.3f} {m.mrr:6.3f} {r.micro.acerto[5]:8.3f} "
            f"{r.por_tipo['regra'].acerto[5] if 'regra' in r.por_tipo else float('nan'):8.3f} "
            f"{r.por_tipo['achado'].acerto[5] if 'achado' in r.por_tipo else float('nan'):9.3f}"
        )
    linhas.append(f"Vencedora: {decisao.vencedora.nome} — {decisao.justificativa}")
    if decisao.aviso_corpus:
        linhas.append(f"AVISO: {decisao.aviso_corpus}")
    linhas.append("Precision@K não entra na decisão; na janela ela conta passagens repetidas pela sobreposição.")
    return "\n".join(linhas)
