"""Pertinência dos trechos complementares e a escolha da busca (semana 8).

Desenho: `docs/superpowers/specs/2026-10-12-pertinencia-dos-complementares-design.md`.
A régua de 11/10 mede se a âncora é recuperada; desde a semana 7 a âncora entra no
contexto sem depender da busca. Esta régua mede o que sobra para a busca: se os trechos
2 a 5 que o LLM recebe são pertinentes ao achado.
"""

import argparse
import hashlib
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from importlib.metadata import version
from statistics import mean

from pydantic import BaseModel

from core.analise.contexto import K_BUSCA, escolher_complementares
from rag.avaliacao import ARQUIVO_CONSULTAS, RAIZ_REPO, Consulta, ErroDeAvaliacao, avaliar, ler_conjunto
from rag.chunking import TrechoIndexado
from rag.embeddings import MODELO

Ranqueador = Callable[[str, int], list[int]]
"""Consulta e k → índices em `trechos`, do mais ao menos relevante."""
TIPOS = ("bm25", "densa", "hibrida")


class ErroDeComplementares(Exception):
    """A medição não pode seguir sem perder algo em silêncio."""


class ConsultaMedida(BaseModel):
    id: str
    id_regra: str
    secoes: list[str]
    """Uma entrada por complementar entregue, na ordem; partes da mesma seção repetem o id."""


class ItemPool(BaseModel):
    id: str
    id_regra: str
    trecho: TrechoIndexado
    """A primeira parte da seção que alguma busca trouxe: é o que a planilha mostra."""


def id_da_secao(id_regra: str, t: TrechoIndexado) -> str:
    return f"{id_regra}|{t.id_pagina}#{t.ancora}"


def _escolhidos(
    consulta: Consulta, ancoras: dict[str, TrechoIndexado], trechos: list[TrechoIndexado], ranquear: Ranqueador
) -> list[TrechoIndexado]:
    resultados = [trechos[i] for i in ranquear(consulta.texto, K_BUSCA)]
    return escolher_complementares(ancoras[consulta.id_regra], resultados)


def complementares_por_busca(
    consultas: list[Consulta],
    ancoras: dict[str, TrechoIndexado],
    trechos: list[TrechoIndexado],
    ranqueadores: dict[str, Ranqueador],
) -> dict[str, list[ConsultaMedida]]:
    return {
        tipo: [
            ConsultaMedida(
                id=c.id,
                id_regra=c.id_regra,
                secoes=[id_da_secao(c.id_regra, t) for t in _escolhidos(c, ancoras, trechos, ranquear)],
            )
            for c in consultas
        ]
        for tipo, ranquear in ranqueadores.items()
    }


def formar_pool(
    consultas: list[Consulta],
    ancoras: dict[str, TrechoIndexado],
    trechos: list[TrechoIndexado],
    ranqueadores: dict[str, Ranqueador],
) -> list[ItemPool]:
    """União, por regra, das seções que as buscas escolhem — o *pooling* do TREC."""
    pool: dict[str, ItemPool] = {}
    for ranquear in ranqueadores.values():
        for c in consultas:
            for t in _escolhidos(c, ancoras, trechos, ranquear):
                chave = id_da_secao(c.id_regra, t)
                pool.setdefault(chave, ItemPool(id=chave, id_regra=c.id_regra, trecho=t))
    return [pool[chave] for chave in sorted(pool)]


MARGEM = 0.10
"""Fixada antes de medir: uma alternativa só substitui o BM25 se ganhar por isto na macro."""
_EPS = 1e-9


class Precisao(BaseModel):
    principal: float | None
    piso: float | None
    teto: float | None


class MedidaBusca(BaseModel):
    macro: Precisao
    micro: Precisao
    por_regra: dict[str, Precisao]
    sem_complementar: int
    """Consultas sem nenhum complementar: não entram na média, mas aparecem."""


class DecisaoBusca(BaseModel):
    vencedora: str
    justificativa: str


def _contagem(secoes: list[str], julgamentos: dict[str, str]) -> tuple[int, int, int]:
    faltando = sorted({s for s in secoes if s not in julgamentos})
    if faltando:
        raise ErroDeComplementares(
            f"complementar sem julgamento — o pool mudou desde a planilha: {', '.join(faltando)}"
        )
    vereditos = [julgamentos[s] for s in secoes]
    return vereditos.count("pertinente"), vereditos.count("não pertinente"), vereditos.count("indeterminado")


def _precisao(pert: int, nao: int, ind: int) -> Precisao:
    total = pert + nao + ind
    return Precisao(
        principal=pert / (pert + nao) if pert + nao else None,
        piso=pert / total if total else None,
        teto=(pert + ind) / total if total else None,
    )


def _media(valores: list[float | None]) -> float | None:
    presentes = [v for v in valores if v is not None]
    return mean(presentes) if presentes else None


def _media_precisoes(precisoes: list[Precisao]) -> Precisao:
    return Precisao(
        principal=_media([p.principal for p in precisoes]),
        piso=_media([p.piso for p in precisoes]),
        teto=_media([p.teto for p in precisoes]),
    )


def medir_busca(medidas: list[ConsultaMedida], julgamentos: dict[str, str]) -> MedidaBusca:
    por_consulta: dict[str, list[Precisao]] = {}
    soma = [0, 0, 0]
    vazias = 0
    for m in medidas:
        por_consulta.setdefault(m.id_regra, [])
        if not m.secoes:
            vazias += 1
            continue
        contagem = _contagem(m.secoes, julgamentos)
        soma = [a + b for a, b in zip(soma, contagem)]
        por_consulta[m.id_regra].append(_precisao(*contagem))
    por_regra = {regra: _media_precisoes(lista) for regra, lista in sorted(por_consulta.items())}
    return MedidaBusca(
        macro=_media_precisoes(list(por_regra.values())),
        micro=_precisao(*soma),
        por_regra=por_regra,
        sem_complementar=vazias,
    )


def decidir_busca(macros: dict[str, float | None]) -> DecisaoBusca:
    base = macros.get("bm25")
    if base is None:
        raise ErroDeComplementares("sem macro do bm25 — nada contra o que comparar")
    candidatas = [
        t for t in ("densa", "hibrida") if macros.get(t) is not None and macros[t] >= base + MARGEM - _EPS
    ]
    if not candidatas:
        return DecisaoBusca(
            vencedora="bm25",
            justificativa=f"nenhuma alternativa supera a macro do bm25 ({base:.3f}) por {MARGEM:.2f}; fica o bm25",
        )
    vencedora = max(candidatas, key=lambda t: (round(macros[t], 9), -TIPOS.index(t)))
    return DecisaoBusca(
        vencedora=vencedora,
        justificativa=(
            f"{vencedora} ({macros[vencedora]:.3f}) supera a macro do bm25 ({base:.3f}) por {MARGEM:.2f} ou mais"
            + ("; empate resolvido pela mais simples" if len(candidatas) == 2 and abs(macros["densa"] - macros["hibrida"]) < _EPS else "")
        ),
    )


ARQUIVO_PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "pertinencia-complementares.xlsx"
ARQUIVO_CSV = RAIZ_REPO / "eval" / "recuperacao" / "pertinencia.csv"
PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"


@dataclass
class Ambiente:
    consultas: list[Consulta]
    ancoras: dict[str, TrechoIndexado]
    trechos: list[TrechoIndexado]
    ranqueadores: dict[str, Ranqueador]


def carregar_ambiente() -> Ambiente:
    """Os trechos do índice e as três buscas sobre eles. Os vetores vêm do cache da
    medição de 11/10; sem ele, falha — recalcular em silêncio mudaria o que se mede."""
    from core.analise.contexto import carregar_gabaritos
    from rag.busca import K_FUSAO, IndiceBm25, fundir_rrf, ranquear
    from rag.embeddings import PASTA_EMBEDDINGS, EmbedderBge, ler_cache
    from rag.indice import BaseRag

    base = BaseRag.carregar()
    trechos = base.trechos
    textos = [t.texto_indexado for t in trechos]
    embedder = EmbedderBge()
    vetores = ler_cache(PASTA_EMBEDDINGS, base.configuracao.variante, embedder.nome, textos)
    if vetores is None:
        raise ErroDeComplementares(
            f"sem cache de embeddings para {base.configuracao.variante} - rode `python -m rag.medicao`"
        )
    bm25 = IndiceBm25(textos)

    def por_bm25(consulta: str, k: int) -> list[int]:
        return ranquear(bm25.pontuacoes(consulta), None, k)

    def densa(consulta: str, k: int) -> list[int]:
        return ranquear(vetores @ embedder.vetor_consulta(consulta), None, k)

    def hibrida(consulta: str, k: int) -> list[int]:
        return fundir_rrf([densa(consulta, K_FUSAO), por_bm25(consulta, K_FUSAO)], k)

    ancoras = {
        id_regra: base.trecho_ancora(g.id_pagina, g.ancora, g.frase_marca)
        for id_regra, g in carregar_gabaritos().items()
    }
    return Ambiente(
        consultas=ler_conjunto(ARQUIVO_CONSULTAS).consultas,
        ancoras=ancoras,
        trechos=trechos,
        ranqueadores={"bm25": por_bm25, "densa": densa, "hibrida": hibrida},
    )


class ResultadoComplementares(BaseModel):
    por_busca: dict[str, MedidaBusca]
    por_busca_achados: dict[str, MedidaBusca]
    """Só as consultas de achado — as únicas que o pipeline faz. Registro ao lado da macro
    da spec, que inclui as 9 consultas da regra; não decide."""
    decisao: DecisaoBusca
    regua_antiga: dict[str, dict[str, float]]
    """Acerto@5 e MRR@10 da âncora, por busca, nas 70 consultas: registro, não decide."""
    ambiente: dict


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.2f}"


def formatar(r: ResultadoComplementares) -> str:
    regras = sorted(next(iter(r.por_busca.values())).por_regra)
    linhas = ["regra      " + "".join(f"{t:>10}" for t in TIPOS)]
    for regra in regras:
        linhas.append(f"{regra:<10} " + "".join(f"{_pct(r.por_busca[t].por_regra[regra].principal):>10}" for t in TIPOS))
    linhas.append("macro      " + "".join(f"{_pct(r.por_busca[t].macro.principal):>10}" for t in TIPOS))
    linhas.append("micro      " + "".join(f"{_pct(r.por_busca[t].micro.principal):>10}" for t in TIPOS))
    linhas.append("piso-teto  " + "".join(
        f"{_pct(r.por_busca[t].macro.piso) + '-' + _pct(r.por_busca[t].macro.teto):>10}" for t in TIPOS
    ))
    linhas.append("regua antiga (acerto@5 / MRR@10): " + ", ".join(
        f"{t} {r.regua_antiga[t]['acerto5']:.3f}/{r.regua_antiga[t]['mrr']:.3f}" for t in TIPOS
    ))
    linhas.append("so achados " + "".join(f"{_pct(r.por_busca_achados[t].macro.principal):>10}" for t in TIPOS))
    linhas.append(f"Decisao: {r.decisao.vencedora} - {r.decisao.justificativa}")
    return _ascii("\n".join(linhas))


def _pool(amb: Ambiente) -> list[ItemPool]:
    return formar_pool(amb.consultas, amb.ancoras, amb.trechos, amb.ranqueadores)


def _gerar() -> int:
    from rag.pertinencia import gerar_planilha

    amb = carregar_ambiente()
    pool = _pool(amb)
    gerar_planilha(pool, amb.ancoras, ARQUIVO_PLANILHA)
    print(_ascii(f"Planilha gerada em {ARQUIVO_PLANILHA} ({len(pool)} secoes)"))
    return 0


def _importar(parcial: bool) -> int:
    from rag.pertinencia import gravar_csv, ler_planilha, progresso, validar

    lidas = ler_planilha(ARQUIVO_PLANILHA)
    problemas = validar(lidas, _pool(carregar_ambiente()), parcial=parcial)
    if problemas:
        for p in problemas:
            onde = f"linha {p.linha}" if p.linha is not None else "fora da planilha"
            print(_ascii(f"erro: {p.aba} {onde} | {p.id} | {p.motivo}"), file=sys.stderr)
        print(f"erro: {len(problemas)} problema(s); nada foi gravado", file=sys.stderr)
        return 1
    if parcial:
        for regra, (julgadas, total) in sorted(progresso(lidas).items()):
            print(f"{regra}: {julgadas}/{total}")
        return 0
    gravar_csv([l for _, _, l in lidas], ARQUIVO_CSV)
    print(_ascii(f"Pertinencia gravada em {ARQUIVO_CSV} ({len(lidas)} linhas)"))
    return 0


def _medir() -> int:
    from rag.pertinencia import ler_csv

    if not ARQUIVO_CSV.is_file():
        print(f"erro: {ARQUIVO_CSV.name} ausente - rode `python -m rag.complementares importar`", file=sys.stderr)
        return 1
    julgamentos = ler_csv(ARQUIVO_CSV)
    amb = carregar_ambiente()
    medidas = complementares_por_busca(amb.consultas, amb.ancoras, amb.trechos, amb.ranqueadores)
    por_busca = {t: medir_busca(medidas[t], julgamentos) for t in TIPOS}
    de_achado = {c.id for c in amb.consultas if c.tipo == "achado"}
    por_busca_achados = {
        t: medir_busca([m for m in medidas[t] if m.id in de_achado], julgamentos) for t in TIPOS
    }
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    regua_antiga = {}
    for t in TIPOS:
        relatorio = avaliar(lambda q, k, r=amb.ranqueadores[t]: [amb.trechos[i].para_regua() for i in r(q, k)], conjunto)
        regua_antiga[t] = {"acerto5": relatorio.macro.acerto[5], "mrr": relatorio.macro.mrr}
    resultado = ResultadoComplementares(
        por_busca=por_busca,
        por_busca_achados=por_busca_achados,
        decisao=decidir_busca({t: por_busca[t].macro.principal for t in TIPOS}),
        regua_antiga=regua_antiga,
        ambiente={
            "data": date.today().isoformat(),
            "modelo": MODELO,
            "versoes": {p: version(p) for p in ("torch", "sentence-transformers", "rank-bm25", "chromadb", "numpy")},
            "sha256_consultas": hashlib.sha256(ARQUIVO_CONSULTAS.read_bytes()).hexdigest(),
            "sha256_pertinencia": hashlib.sha256(ARQUIVO_CSV.read_bytes()).hexdigest(),
            "margem": MARGEM,
        },
    )
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"complementares-{date.today().isoformat()}.json"
    destino.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(formatar(resultado))
    print(_ascii(f"Resultado em {destino}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rag.complementares", description="Pertinencia dos complementares.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="gera a planilha cega de pertinencia")
    importar = sub.add_parser("importar", help="valida a planilha e grava eval/recuperacao/pertinencia.csv")
    importar.add_argument("--parcial", action="store_true", help="so mostra o progresso")
    sub.add_parser("medir", help="precisao dos complementares por busca e decisao")
    args = parser.parse_args(argv)
    try:
        if args.comando == "gerar":
            return _gerar()
        if args.comando == "importar":
            return _importar(args.parcial)
        return _medir()
    except (ErroDeComplementares, ErroDeAvaliacao, OSError) as erro:
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
