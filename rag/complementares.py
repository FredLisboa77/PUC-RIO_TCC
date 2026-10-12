"""Pertinência dos trechos complementares e a escolha da busca (semana 8).

Desenho: `docs/superpowers/specs/2026-10-12-pertinencia-dos-complementares-design.md`.
A régua de 11/10 mede se a âncora é recuperada; desde a semana 7 a âncora entra no
contexto sem depender da busca. Esta régua mede o que sobra para a busca: se os trechos
2 a 5 que o LLM recebe são pertinentes ao achado.
"""

from collections.abc import Callable
from statistics import mean

from pydantic import BaseModel

from core.analise.contexto import K_BUSCA, escolher_complementares
from rag.avaliacao import Consulta
from rag.chunking import TrechoIndexado

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
