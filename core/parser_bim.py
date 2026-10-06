"""Leitura do `model.bim` (TMSL) para o modelo interno normalizado.

Princípio: nunca falhar por uma propriedade ausente ou desconhecida. O conjunto
de propriedades do TMSL varia com o `compatibilityLevel`, e a Microsoft
acrescenta propriedades sem aviso. Tudo o que não é reconhecido segue em
`bruto`, disponível para as regras.
"""

import json
from pathlib import Path
from typing import Any

from core.model import (
    Coluna,
    Medida,
    ModeloSemantico,
    Particao,
    Relacionamento,
    Tabela,
)


def _texto(valor: Any) -> str | None:
    """Normaliza uma expressão DAX ou M.

    O TMSL grava expressões ora como string, ora como lista de linhas. As regras
    trabalham sempre com uma string só, com quebras de linha preservadas.
    """
    if valor is None:
        return None
    if isinstance(valor, list):
        return "\n".join(str(linha) for linha in valor)
    return str(valor)


def _coluna(bruto: dict) -> Coluna:
    return Coluna(
        nome=bruto.get("name", ""),
        tipo_dado=bruto.get("dataType"),
        tipo=bruto.get("type"),
        resumir_por=bruto.get("summarizeBy"),
        expressao=_texto(bruto.get("expression")),
        oculta=bool(bruto.get("isHidden", False)),
        bruto=bruto,
    )


def _medida(bruto: dict, tabela: str) -> Medida:
    return Medida(
        nome=bruto.get("name", ""),
        expressao=_texto(bruto.get("expression")) or "",
        tabela=tabela,
        pasta=bruto.get("displayFolder"),
        formato=bruto.get("formatString"),
        oculta=bool(bruto.get("isHidden", False)),
        bruto=bruto,
    )


def _particao(bruto: dict) -> Particao:
    origem = bruto.get("source") or {}
    return Particao(
        nome=bruto.get("name", ""),
        modo=bruto.get("mode"),
        tipo_origem=origem.get("type"),
        origem=_texto(origem.get("expression")),
        bruto=bruto,
    )


def _tabela(bruto: dict) -> Tabela:
    nome = bruto.get("name", "")
    return Tabela(
        nome=nome,
        oculta=bool(bruto.get("isHidden", False)),
        data_category=bruto.get("dataCategory"),
        colunas=[_coluna(c) for c in bruto.get("columns", [])],
        medidas=[_medida(m, nome) for m in bruto.get("measures", [])],
        particoes=[_particao(p) for p in bruto.get("partitions", [])],
        bruto=bruto,
    )


CARDINALIDADE = {"one": "um", "many": "muitos"}


def _cardinalidade(valor: Any, padrao: str) -> str:
    """Normaliza `fromCardinality`/`toCardinality` para o vocabulário interno.

    Ausentes, os dois significam muitos-para-um: o lado `from` é "muitos" e o
    lado `to` é "um". Quando presentes vêm em inglês. As regras dependem disso:
    um `fromCardinality: "one"` explícito descreve um relacionamento
    um-para-um, e tratá-lo como muitos-para-um inverteria os lados.
    """
    if valor is None:
        return padrao
    return CARDINALIDADE.get(str(valor), str(valor))


def _relacionamento(bruto: dict) -> Relacionamento:
    # No TMSL, `crossFilteringBehavior` ausente significa filtro em um sentido.
    # "automatic" deixa o motor decidir; para efeito de auditoria só interessa
    # distinguir o bidirecional explícito, que é o padrão problemático.
    bidirecional = bruto.get("crossFilteringBehavior") == "bothDirections"

    return Relacionamento(
        nome=bruto.get("name", ""),
        tabela_origem=bruto.get("fromTable", ""),
        coluna_origem=bruto.get("fromColumn", ""),
        tabela_destino=bruto.get("toTable", ""),
        coluna_destino=bruto.get("toColumn", ""),
        direcao_filtro="ambos_sentidos" if bidirecional else "um_sentido",
        ativo=bool(bruto.get("isActive", True)),
        cardinalidade_origem=_cardinalidade(bruto.get("fromCardinality"), "muitos"),
        cardinalidade_destino=_cardinalidade(bruto.get("toCardinality"), "um"),
        bruto=bruto,
    )


def ler_modelo(caminho: str | Path) -> ModeloSemantico:
    """Lê um `model.bim` e devolve o modelo normalizado."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    model = dados.get("model", {})

    return ModeloSemantico(
        nome=dados.get("name", ""),
        compatibility_level=dados.get("compatibilityLevel"),
        cultura=model.get("culture"),
        tabelas=[_tabela(t) for t in model.get("tables", [])],
        relacionamentos=[
            _relacionamento(r) for r in model.get("relationships", [])
        ],
    )
