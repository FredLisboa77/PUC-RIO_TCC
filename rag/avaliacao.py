"""Conjunto de avaliação da recuperação (Fase 3).

A régua que decide chunking, embeddings e busca híbrida: o gabarito das regras
(página, seção âncora e frase-marca), as consultas por regra e por achado de
P1–P7, e as métricas. Desenho:
`docs/superpowers/specs/2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`.
"""

import argparse
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.base import Achado, RegraMeta
from core.rules.runner import ResultadoRegras
from core.rules.runner import avaliar as avaliar_regras
from core.rules.todas import REGISTRO
from rag.catalogo import RAIZ
from rag.consulta import montar_consulta
from rag.extracao import PASTA_TEXTOS, PaginaExtraida, caminho_do_texto
from rag.texto import normalizar
from rag.urls import caminho_sem_idioma, normalizar_url

RAIZ_REPO = RAIZ.parent
PASTA_AVALIACAO = RAIZ_REPO / "eval" / "recuperacao"
ARQUIVO_GABARITO = PASTA_AVALIACAO / "gabarito.yaml"
ARQUIVO_CONSULTAS = PASTA_AVALIACAO / "consultas.yaml"
PASTA_PBIP = RAIZ_REPO / "data" / "pbip"
PROJETOS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7")
"""O dataset de métricas. O P8 é estudo de caso (ADR-005) e fica fora."""


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


KS = (1, 3, 5, 10)
K_MAX = 10


class Trecho(BaseModel):
    """O que um recuperador devolve. A régua não sabe de chunking nem de índice."""

    texto: str
    id_pagina: str
    ancora: str | None = None


Buscador = Callable[[str, int], list[Trecho]]


class ResultadoConsulta(BaseModel):
    id: str
    id_regra: str
    tipo: Literal["regra", "achado"]
    posicao: int | None
    """Posição (a partir de 1) do primeiro trecho relevante; `None` se não houve até K_MAX."""
    relevantes_ate: dict[int, int]
    primeiro_devolvido: str | None
    """`id_pagina#ancora` do primeiro trecho devolvido, para explicar o erro."""


class Metricas(BaseModel):
    consultas: int
    acerto: dict[int, float]
    precisao: dict[int, float]
    mrr: float


class RelatorioRecuperacao(BaseModel):
    macro: Metricas
    micro: Metricas
    por_tipo: dict[str, Metricas]
    por_regra: dict[str, Metricas]
    resultados: list[ResultadoConsulta]

    @property
    def erros(self) -> list[ResultadoConsulta]:
        return [r for r in self.resultados if r.posicao is None or r.posicao > 1]


def _metricas(resultados: list[ResultadoConsulta]) -> Metricas:
    n = len(resultados)
    return Metricas(
        consultas=n,
        acerto={k: sum(1 for r in resultados if r.posicao is not None and r.posicao <= k) / n for k in KS},
        precisao={k: sum(r.relevantes_ate[k] for r in resultados) / (k * n) for k in KS},
        mrr=sum(1 / r.posicao for r in resultados if r.posicao is not None) / n,
    )


def _media(metricas: list[Metricas]) -> Metricas:
    n = len(metricas)
    return Metricas(
        consultas=sum(m.consultas for m in metricas),
        acerto={k: sum(m.acerto[k] for m in metricas) / n for k in KS},
        precisao={k: sum(m.precisao[k] for m in metricas) / n for k in KS},
        mrr=sum(m.mrr for m in metricas) / n,
    )


def avaliar(buscar: Buscador, conjunto: ConjuntoAvaliacao) -> RelatorioRecuperacao:
    """Mede um recuperador sobre o conjunto. A busca é feita uma vez por consulta,
    com K_MAX; os cortes menores saem da mesma lista."""
    if not conjunto.consultas:
        raise ErroDeAvaliacao("nenhuma consulta no conjunto")
    frases = {g.id_regra: normalizar(g.frase_marca) for g in conjunto.gabaritos}
    sem_gabarito = sorted({c.id_regra for c in conjunto.consultas} - set(frases))
    if sem_gabarito:
        raise ErroDeAvaliacao(f"consulta(s) de regra sem gabarito: {', '.join(sem_gabarito)}")

    resultados = []
    for consulta in conjunto.consultas:
        trechos = buscar(consulta.texto, K_MAX)
        if len(trechos) > K_MAX:
            raise ErroDeAvaliacao(
                f"{consulta.id}: o recuperador devolveu {len(trechos)} trechos para K = {K_MAX}"
            )
        relevante = [frases[consulta.id_regra] in normalizar(t.texto) for t in trechos]
        resultados.append(
            ResultadoConsulta(
                id=consulta.id,
                id_regra=consulta.id_regra,
                tipo=consulta.tipo,
                posicao=next((i + 1 for i, r in enumerate(relevante) if r), None),
                relevantes_ate={k: sum(relevante[:k]) for k in KS},
                primeiro_devolvido=(
                    f"{trechos[0].id_pagina}#{trechos[0].ancora or ''}" if trechos else None
                ),
            )
        )

    regras = sorted({r.id_regra for r in resultados})
    por_regra = {regra: _metricas([r for r in resultados if r.id_regra == regra]) for regra in regras}
    por_tipo = {
        tipo: _metricas([r for r in resultados if r.tipo == tipo])
        for tipo in ("regra", "achado")
        if any(r.tipo == tipo for r in resultados)
    }
    return RelatorioRecuperacao(
        macro=_media(list(por_regra.values())),
        micro=_metricas(resultados),
        por_tipo=por_tipo,
        por_regra=por_regra,
        resultados=resultados,
    )


def _linha(rotulo: str, m: Metricas) -> str:
    acertos = " · ".join(f"acerto@{k} {m.acerto[k]:.3f}" for k in KS)
    return f"{rotulo}: {acertos} · MRR@10 {m.mrr:.3f}"


def formatar_relatorio(relatorio: RelatorioRecuperacao) -> str:
    linhas = [
        _linha("Macro por regra (decide)", relatorio.macro),
        _linha(f"Micro ({relatorio.micro.consultas} consultas)", relatorio.micro),
        *(
            _linha(f"Tipo {tipo} ({m.consultas} consultas)", m)
            for tipo, m in relatorio.por_tipo.items()
        ),
        "Por regra:",
        *(_linha(f"  {regra} ({m.consultas})", m) for regra, m in relatorio.por_regra.items()),
        "Precision@K (micro): "
        + " · ".join(f"@{k} {relatorio.micro.precisao[k]:.3f}" for k in KS)
        + " — com uma só passagem relevante por consulta, tende a acerto@K / K.",
        f"Consultas fora da posição 1: {len(relatorio.erros)}",
    ]
    for erro in relatorio.erros:
        onde = (
            f"primeiro acerto na posição {erro.posicao}" if erro.posicao is not None else "não apareceu"
        )
        linhas.append(f"  {erro.id}: {onde} — primeiro devolvido: {erro.primeiro_devolvido or '(nada)'}")
    return "\n".join(linhas)


def _auditar_padrao(caminho: Path) -> ResultadoRegras:
    return avaliar_regras(ler_modelo(abrir_pbip(caminho).model_bim), REGISTRO)


def achados_dos_projetos(
    pasta: Path, auditar: Callable[[Path], ResultadoRegras] | None = None
) -> dict[str, list[Achado]]:
    """Roda as regras sobre P1–P7, na ordem. Uma regra com falha para tudo: gerar
    menos consultas em silêncio mudaria a régua sem aviso."""
    auditar = auditar or _auditar_padrao
    saida: dict[str, list[Achado]] = {}
    for codigo in PROJETOS:
        candidatos = sorted(pasta.glob(f"{codigo}_*")) if pasta.is_dir() else []
        if not candidatos:
            raise ErroDeAvaliacao(f"{codigo} não encontrado em {pasta} (data/ não é versionado)")
        resultado = auditar(candidatos[0])
        if resultado.regras_com_falha:
            falhas = ", ".join(f"{f.id_regra} ({f.erro})" for f in resultado.regras_com_falha)
            raise ErroDeAvaliacao(f"{codigo}: regra(s) com falha: {falhas}")
        saida[codigo] = resultado.achados
    return saida


def ler_pagina_extraida(id_pagina: str, pasta_textos: Path = PASTA_TEXTOS) -> PaginaExtraida:
    caminho = caminho_do_texto(pasta_textos, id_pagina)
    if not caminho.is_file():
        raise ErroDeAvaliacao(
            f"{id_pagina}: página não extraída — rode `python -m rag.coleta` e `python -m rag.extracao`"
        )
    return PaginaExtraida.model_validate_json(caminho.read_text(encoding="utf-8"))


def gerar_do_repositorio() -> ConjuntoAvaliacao:
    return gerar(
        metas=REGISTRO.metas(),
        frases=ler_frases_marca(ARQUIVO_GABARITO),
        ler_pagina=ler_pagina_extraida,
        achados_por_projeto=achados_dos_projetos(PASTA_PBIP),
    )


def resumo_conjunto(conjunto: ConjuntoAvaliacao) -> str:
    por_regra = Counter(c.id_regra for c in conjunto.consultas)
    n_regra = sum(c.tipo == "regra" for c in conjunto.consultas)
    return "\n".join(
        [
            f"Gabaritos: {len(conjunto.gabaritos)}",
            *(f"  {g.id_regra} -> {g.id_pagina}#{g.ancora}" for g in conjunto.gabaritos),
            f"Consultas: {len(conjunto.consultas)} ({n_regra} por regra, "
            f"{len(conjunto.consultas) - n_regra} por achado)",
            *(f"  {regra}: {n} consulta(s)" for regra, n in sorted(por_regra.items())),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.avaliacao",
        description="Conjunto de avaliação da recuperação.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="deduz os gabaritos e gera eval/recuperacao/consultas.yaml")
    parser.parse_args(argv)
    try:
        conjunto = gerar_do_repositorio()
    except ErroDeAvaliacao as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    ARQUIVO_CONSULTAS.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CONSULTAS.write_text(como_yaml(conjunto), encoding="utf-8", newline="\n")
    print(resumo_conjunto(conjunto))
    return 0


if __name__ == "__main__":
    sys.exit(main())
