"""Precisão e recall por regra, cruzando o gabarito com os achados.

`indeterminado` não é forçado para lado nenhum: cada regra sai com a versão
principal (sem os indeterminados), o piso (contra a regra) e o teto (a favor) —
o mesmo raciocínio que recusou a PERF-005. Sem divisor, a taxa é `None`: uma
regra sem achado não tem precisão 1, nem 0.
"""

from statistics import mean

from pydantic import BaseModel

import core.rules.todas  # noqa: F401 — registra as regras
from core.rules.base import Achado
from core.rules.registry import REGISTRO
from gabarito.candidatos import ErroDeGabarito
from gabarito.planilha import LinhaGabarito

LIMITE_R03 = 0.7
GATILHO_R12 = 40


class Matriz(BaseModel):
    vp: int = 0
    fp: int = 0
    fn: int = 0
    vn: int = 0
    ind_marcados: int = 0
    ind_nao_marcados: int = 0

    def __add__(self, outra: "Matriz") -> "Matriz":
        return Matriz(**{campo: getattr(self, campo) + getattr(outra, campo) for campo in Matriz.model_fields})


def _razao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def taxas(m: Matriz) -> dict[str, dict[str, float | None]]:
    return {
        "precisao": {
            "principal": _razao(m.vp, m.vp + m.fp),
            "piso": _razao(m.vp, m.vp + m.fp + m.ind_marcados),
            "teto": _razao(m.vp + m.ind_marcados, m.vp + m.fp + m.ind_marcados),
        },
        "recall": {
            "principal": _razao(m.vp, m.vp + m.fn),
            "piso": _razao(m.vp, m.vp + m.fn + m.ind_nao_marcados),
            "teto": _razao(m.vp + m.ind_marcados, m.vp + m.ind_marcados + m.fn),
        },
    }


class Medida(BaseModel):
    matriz: Matriz
    taxas: dict[str, dict[str, float | None]]


def _medida(m: Matriz) -> Medida:
    return Medida(matriz=m, taxas=taxas(m))


class Divergencia(BaseModel):
    tipo: str
    id: str
    justificativa: str | None


class ResultadoMedicao(BaseModel):
    por_regra: dict[str, Medida]
    por_categoria: dict[str, Medida]
    por_projeto: dict[str, Medida]
    total_micro: Medida
    macro: dict[str, float | None]
    macro_por_categoria: dict[str, dict[str, float | None]]
    r03: list[str]
    r12: dict[str, int]
    divergencias: list[Divergencia]


def medir(gabarito: list[LinhaGabarito], achados: dict[str, list[Achado]]) -> ResultadoMedicao:
    sem_veredito = [l.id for l in gabarito if l.veredito is None]
    if sem_veredito:
        raise ErroDeGabarito(f"{len(sem_veredito)} linha(s) do gabarito sem veredito, ex.: {sem_veredito[0]}")
    marcados = {f"{a.id_regra}|{projeto}|{a.evidencia.objeto}" for projeto, lista in achados.items() for a in lista}
    ids = {l.id for l in gabarito}
    sem_candidato = sorted(marcados - ids)
    if sem_candidato:
        raise ErroDeGabarito(f"achado(s) sem linha no gabarito — furo no gerador de candidatos: {', '.join(sem_candidato)}")

    por_regra: dict[str, Matriz] = {}
    por_projeto: dict[str, Matriz] = {}
    divergencias: list[Divergencia] = []
    for l in sorted(gabarito, key=lambda x: x.id):
        marcado = l.id in marcados
        if l.veredito == "indeterminado":
            parcela = Matriz(ind_marcados=1) if marcado else Matriz(ind_nao_marcados=1)
        elif l.veredito == "viola":
            parcela = Matriz(vp=1) if marcado else Matriz(fn=1)
        else:
            parcela = Matriz(fp=1) if marcado else Matriz(vn=1)
        if parcela.fp or parcela.fn:
            divergencias.append(Divergencia(tipo="FP" if parcela.fp else "FN", id=l.id, justificativa=l.justificativa))
        por_regra[l.id_regra] = por_regra.get(l.id_regra, Matriz()) + parcela
        por_projeto[l.projeto] = por_projeto.get(l.projeto, Matriz()) + parcela

    por_categoria: dict[str, Matriz] = {}
    for id_regra, m in por_regra.items():
        categoria = REGISTRO.meta(id_regra).categoria
        por_categoria[categoria] = por_categoria.get(categoria, Matriz()) + m

    medidas = {id_regra: _medida(m) for id_regra, m in sorted(por_regra.items())}
    total = sum(por_regra.values(), Matriz())

    def _macro(qual: str, regras: list[str] | None = None) -> float | None:
        valores = [
            m.taxas[qual]["principal"]
            for id_regra, m in medidas.items()
            if (regras is None or id_regra in regras) and m.taxas[qual]["principal"] is not None
        ]
        return mean(valores) if valores else None

    regras_da_categoria: dict[str, list[str]] = {}
    for id_regra in medidas:
        regras_da_categoria.setdefault(REGISTRO.meta(id_regra).categoria, []).append(id_regra)

    return ResultadoMedicao(
        por_regra=medidas,
        por_categoria={c: _medida(m) for c, m in sorted(por_categoria.items())},
        por_projeto={p: _medida(m) for p, m in sorted(por_projeto.items())},
        total_micro=_medida(total),
        macro={"precisao": _macro("precisao"), "recall": _macro("recall")},
        macro_por_categoria={
            c: {"precisao": _macro("precisao", regras), "recall": _macro("recall", regras)}
            for c, regras in sorted(regras_da_categoria.items())
        },
        r03=[
            id_regra
            for id_regra, m in medidas.items()
            if m.taxas["precisao"]["principal"] is not None and m.taxas["precisao"]["principal"] < LIMITE_R03
        ],
        r12={
            "vp": total.vp,
            "vp_sem_perf003": total.vp - por_regra.get("PERF-003", Matriz()).vp,
            "gatilho": GATILHO_R12,
        },
        divergencias=divergencias,
    )
