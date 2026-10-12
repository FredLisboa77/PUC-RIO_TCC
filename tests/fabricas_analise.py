"""Fábricas dos testes da geração (`core/analise`, `core/auditoria`).

Ficam fora do `conftest.py` porque não são fixtures: são construtores que cada
teste chama com os parâmetros que quer variar.
"""

from core.analise.base import TrechoDeContexto
from core.rules.base import Achado, Evidencia, RegraMeta

RECOMENDACAO_PADRAO = (
    "Desative a opção global de data/hora automática e use uma tabela de datas própria."
)


def meta(id_regra: str = "MOD-001", termos: tuple[str, ...] = ("auto date time",)) -> RegraMeta:
    return RegraMeta(
        id=id_regra,
        titulo="Tabela de data automática",
        categoria="modelagem",
        severidade="media",
        url_canonica="https://learn.microsoft.com/x",
        termos_consulta=termos,
        recomendacao_padrao=RECOMENDACAO_PADRAO,
    )


def achado(
    id_regra: str = "MOD-001",
    *,
    objeto: str = "LocalDateTable_1",
    mensagem: str = "O modelo tem 4 tabelas de data automáticas.",
    trecho: str | None = None,
    detalhe: dict | None = None,
    tipo_objeto: str = "tabela",
) -> Achado:
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(
            tipo_objeto=tipo_objeto, objeto=objeto, tabela=objeto, trecho=trecho, detalhe=detalhe or {}
        ),
        mensagem=mensagem,
    )


def trecho_de_contexto(
    numero: int, texto: str = "Disable the auto date/time option.", origem: str | None = None
) -> TrechoDeContexto:
    return TrechoDeContexto(
        numero=numero,
        id_pagina=f"learn:p{numero}",
        url=f"https://learn.microsoft.com/p{numero}",
        titulo=f"Página {numero}",
        ancora="s",
        caminho="Seção",
        texto=texto,
        origem=origem or ("ancora" if numero == 1 else "busca"),
    )


def contexto(n: int = 3) -> list[TrechoDeContexto]:
    return [trecho_de_contexto(i) for i in range(1, n + 1)]
