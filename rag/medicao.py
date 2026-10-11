"""Medição da recuperação (Fase 3).

Mede as 24 combinações de chunking, cabeçalho, busca e corpus com a régua
congelada e escolhe a vencedora pela regra fixada antes de medir. Desenho:
`docs/superpowers/specs/2026-10-11-medicao-da-recuperacao-design.md`, seção 5.
"""

import argparse
import hashlib
import json
import sys
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import BaseModel

from rag.avaliacao import (
    ARQUIVO_CONSULTAS,
    RAIZ_REPO,
    ConjuntoAvaliacao,
    ErroDeAvaliacao,
    Metricas,
    ResultadoConsulta,
    avaliar,
    ler_conjunto,
    ler_pagina_extraida,
)
from rag.busca import IndiceBm25, TipoBusca, criar_buscador
from rag.catalogo import ARQUIVO_FONTES
from rag.chunking import Estrategia, TrechoIndexado, ids_do_corpus_guidance, montar_trechos
from rag.coleta import paginas_do_catalogo
from rag.embeddings import MODELO, PASTA_EMBEDDINGS, Embedder, EmbedderBge, ErroDeEmbeddings, vetores_com_cache
from rag.extracao import VERSAO_EXTRATOR, PaginaExtraida
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


PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"
VARIANTES = ("secao-sem", "secao-com", "janela-sem", "janela-com")


def carregar_paginas() -> list[PaginaExtraida]:
    """As páginas indexáveis do catálogo, extraídas, em ordem de id."""
    return [ler_pagina_extraida(p.id) for p in paginas_do_catalogo(ARQUIVO_FONTES)]


def trechos_das_variantes(paginas: list[PaginaExtraida]) -> dict[str, list[TrechoIndexado]]:
    return {
        f"{estrategia}-{'com' if cabecalho else 'sem'}": montar_trechos(paginas, estrategia, cabecalho)
        for estrategia in ("secao", "janela")
        for cabecalho in (False, True)
    }


def ambiente(trechos: dict[str, list[TrechoIndexado]]) -> dict:
    return {
        "data": date.today().isoformat(),
        "modelo": MODELO,
        "versoes": {
            p: version(p) for p in ("torch", "sentence-transformers", "transformers", "rank-bm25", "chromadb", "numpy")
        },
        "trechos_por_variante": {v: len(t) for v, t in trechos.items()},
        "versao_extrator": VERSAO_EXTRATOR,
        "sha256_consultas": hashlib.sha256(ARQUIVO_CONSULTAS.read_bytes()).hexdigest(),
    }


def gravar_resultado(
    caminho: Path, resultados: list[ResultadoConfiguracao], decisao: Decisao, ambiente: dict
) -> None:
    dados = {
        "ambiente": ambiente,
        "decisao": decisao.model_dump(mode="json"),
        "resultados": [r.model_dump(mode="json") for r in resultados],
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def ler_resultado(caminho: Path) -> tuple[list[ResultadoConfiguracao], Decisao]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return (
        [ResultadoConfiguracao.model_validate(r) for r in dados["resultados"]],
        Decisao.model_validate(dados["decisao"]),
    )


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        prog="python -m rag.medicao",
        description="Mede as 24 combinações de recuperação com a régua congelada.",
    ).parse_args(argv)
    try:
        conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
        paginas = carregar_paginas()
        trechos = trechos_das_variantes(paginas)
        for variante, lista in trechos.items():
            falhas = verificar_oraculo(lista, conjunto)
            if falhas:
                raise ErroDeMedicao(f"oráculo: {variante} parte a frase-marca de {', '.join(falhas)}")
        embedder = EmbedderBge()
        vetores = {
            v: vetores_com_cache(embedder, [t.texto_indexado for t in lista], pasta=PASTA_EMBEDDINGS, nome=v)
            for v, lista in trechos.items()
        }
        fontes = yaml.safe_load(ARQUIVO_FONTES.read_text(encoding="utf-8"))
        resultados = medir(
            conjunto,
            trechos=trechos,
            vetores=vetores,
            embedder=embedder,
            paginas_guidance=ids_do_corpus_guidance(fontes),
        )
    except (ErroDeAvaliacao, ErroDeEmbeddings, ErroDeMedicao) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    decisao = decidir(resultados)
    destino = PASTA_RESULTADOS / f"recuperacao-{date.today().isoformat()}.json"
    gravar_resultado(destino, resultados, decisao, ambiente(trechos))
    print(formatar_tabela(resultados, decisao))
    print(f"Resultado gravado em {destino.relative_to(RAIZ_REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
