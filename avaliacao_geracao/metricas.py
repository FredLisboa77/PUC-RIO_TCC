"""Métricas da rubrica da geração (spec de 13/10/2026, seção 5).

Mesmo formato do gabarito: principal sem os indeterminados, piso e teto com eles
contra e a favor, e o intervalo de Wilson sobre a principal.
"""

from collections import Counter, defaultdict
from datetime import datetime

from avaliacao_geracao.estatistica import kappa, wilson
from avaliacao_geracao.planilha import ITENS, LinhaRubrica
from avaliacao_geracao.rodada import Rodada
from core.rules.registry import Registro
from core.rules.todas import REGISTRO


def _razao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def taxa(sim: int, nao: int, ind: int) -> dict:
    intervalo = wilson(sim, sim + nao)
    return {
        "n": {"sim": sim, "nao": nao, "indeterminado": ind},
        "principal": _razao(sim, sim + nao),
        "piso": _razao(sim, sim + nao + ind),
        "teto": _razao(sim + ind, sim + nao + ind),
        "wilson": list(intervalo) if intervalo else None,
    }


def _contar(vereditos: list[str]) -> dict:
    c = Counter(vereditos)
    return taxa(c["sim"], c["não"], c["indeterminado"])


def _recortes(pares: list[tuple[str, str, str]]) -> dict:
    """`pares` = (regra, categoria, veredito)."""
    por_regra, por_categoria = defaultdict(list), defaultdict(list)
    for regra, categoria, veredito in pares:
        por_regra[regra].append(veredito)
        por_categoria[categoria].append(veredito)
    return {
        "total": _contar([v for _, _, v in pares]),
        "por_regra": {r: _contar(v) for r, v in sorted(por_regra.items())},
        "por_categoria": {c: _contar(v) for c, v in sorted(por_categoria.items())},
    }


def _utilizavel(linha: LinhaRubrica) -> str:
    vereditos = [getattr(linha, n) for n in ITENS]
    if "não" in vereditos:
        return "não"
    return "sim" if all(v == "sim" for v in vereditos) else "indeterminado"


def _concordancia(pares: list[tuple[bool, str]]) -> dict:
    """`pares` = (automático diz sim, veredito humano); indeterminados ficam de fora."""
    tabela = {"a": 0, "b": 0, "c": 0, "d": 0}
    for automatico, humano in pares:
        if humano == "indeterminado":
            continue
        casa = ("a" if humano == "sim" else "b") if automatico else ("c" if humano == "sim" else "d")
        tabela[casa] += 1
    n = sum(tabela.values())
    return {
        "tabela": tabela,
        "n": n,
        "concordancia": _razao(tabela["a"] + tabela["d"], n),
        "kappa": kappa(tabela["a"], tabela["b"], tabela["c"], tabela["d"]),
    }


def medir(linhas: list[LinhaRubrica], rodada: Rodada, *, registro: Registro | None = None,
          commit: str | None = None) -> dict:
    registro = REGISTRO if registro is None else registro
    julgadas = [(l, rodada[l.id].item) for l in linhas if all(getattr(l, n) for n in ITENS)]

    def chave(item):
        meta = registro.meta(item.achado.id_regra)
        return meta.id, meta.categoria

    itens = {
        n: _recortes([(*chave(item), getattr(l, n)) for l, item in julgadas]) for n in ITENS
    }
    todos = [r.item for r in rodada.values()]
    descartados = [i for i in todos if i.situacao == "sem_fundamentacao"]
    return {
        "ambiente": {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "commit": commit,
            "linhas": len(julgadas),
        },
        "itens": itens,
        "utilizavel": _recortes([(*chave(item), _utilizavel(l)) for l, item in julgadas]),
        "descarte": {
            "achados": len(todos),
            "sem_fundamentacao": len(descartados),
            "taxa": _razao(len(descartados), len(todos)),
            "por_motivo": dict(sorted(Counter(i.motivo_descarte for i in descartados).items())),
        },
        "concordancia": {
            "pertinente": _concordancia([(bool(item.cita_ancora), l.pertinente) for l, item in julgadas]),
            "fiel": _concordancia([(not item.fidelidade.divergencias, l.fiel) for l, item in julgadas]),
        },
    }
