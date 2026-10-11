"""Construtores de PBIP sintéticos para os testes.

Um PBIP real tem centenas de arquivos. Os testes precisam apenas da parte que o
MVP lê: a pasta `.SemanticModel` com `definition.pbism` e `model.bim`. O
construtor abaixo monta exatamente isso, e permite variar cada peça para
exercitar os casos de erro.
"""

import json
from pathlib import Path

import pytest

from core.model import ModeloSemantico
from core.parser_bim import ler_modelo

MODELO_MINIMO = {
    "name": "SemanticModel",
    "compatibilityLevel": 1600,
    "model": {
        "culture": "pt-BR",
        "tables": [],
        "relationships": [],
    },
}


def escrever_pbip(
    raiz: Path,
    nome: str = "Minimal",
    model_bim: dict | None = MODELO_MINIMO,
    pbism_version: str | None = "4.2",
    tmdl: bool = False,
) -> Path:
    """Monta um PBIP em `raiz` e devolve a pasta do projeto.

    `model_bim=None` omite o arquivo; `pbism_version=None` omite o
    `definition.pbism`; `tmdl=True` cria a pasta `definition/` no lugar do
    `model.bim`, como faz o Power BI com o preview de TMDL ligado.
    """
    projeto = raiz / nome
    semantic = projeto / f"{nome}.SemanticModel"
    semantic.mkdir(parents=True)

    if pbism_version is not None:
        (semantic / "definition.pbism").write_text(
            json.dumps({"version": pbism_version, "settings": {}}),
            encoding="utf-8",
        )

    if tmdl:
        definicao = semantic / "definition"
        definicao.mkdir()
        (definicao / "model.tmdl").write_text("model Model\n", encoding="utf-8")
    elif model_bim is not None:
        (semantic / "model.bim").write_text(
            json.dumps(model_bim, ensure_ascii=False), encoding="utf-8"
        )

    (projeto / f"{nome}.pbip").write_text(
        json.dumps({"version": "1.0", "artifacts": []}), encoding="utf-8"
    )
    return projeto


@pytest.fixture
def pbip_minimo(tmp_path: Path) -> Path:
    """Um PBIP válido em TMSL, sem tabelas."""
    return escrever_pbip(tmp_path)


def coluna(
    nome: str,
    *,
    tipo_dado: str = "string",
    tipo: str | None = None,
    expressao: str | None = None,
    resumir_por: str = "none",
    oculta: bool = False,
    annotations: dict[str, str] | None = None,
    variacao_para: str | None = None,
    ordenar_por: str | None = None,
) -> dict:
    """Uma coluna TMSL. `tipo` é o `type`: `calculated`, `calculatedTableColumn`.

    `variacao_para` pendura na coluna uma `variations` apontando para a tabela
    indicada — é assim que o Tempo automático de data/hora liga a coluna de data
    à tabela de data que ele gerou.
    """
    bruto: dict = {"name": nome, "dataType": tipo_dado, "summarizeBy": resumir_por}
    if variacao_para is not None:
        bruto["variations"] = [
            {
                "name": "Variation",
                "isDefault": True,
                "relationship": f"rel-{nome}",
                "defaultHierarchy": {"hierarchy": "Date Hierarchy", "table": variacao_para},
            }
        ]
    if tipo is not None:
        bruto["type"] = tipo
    if expressao is not None:
        bruto["expression"] = expressao
    if oculta:
        bruto["isHidden"] = True
    if annotations:
        bruto["annotations"] = _annotations(annotations)
    if ordenar_por is not None:
        bruto["sortByColumn"] = ordenar_por
    return bruto


def nivel(nome: str, coluna_de: str, *, ordem: int | None = None) -> dict:
    """Um nível de hierarquia. `coluna_de` é o nome da coluna que ele usa."""
    bruto: dict = {"name": nome, "column": coluna_de}
    if ordem is not None:
        bruto["ordinal"] = ordem
    return bruto


def hierarquia(nome: str, *, niveis: list[dict] | tuple = ()) -> dict:
    return {"name": nome, "levels": list(niveis)}


def role(nome: str, *, tabela: str, filtro: str) -> dict:
    """Uma role de RLS com uma permissão de tabela e sua expressão de filtro."""
    return {
        "name": nome,
        "modelPermission": "read",
        "tablePermissions": [{"name": tabela, "filterExpression": filtro}],
    }


def medida(nome: str, expressao: str = "1") -> dict:
    return {"name": nome, "expression": expressao}


def particao(
    nome: str = "particao",
    *,
    tipo: str = "m",
    expressao: str = "let Fonte = 1 in Fonte",
) -> dict:
    return {
        "name": nome,
        "mode": "import",
        "source": {"type": tipo, "expression": expressao},
    }


def tabela(
    nome: str,
    *,
    colunas: list[dict] | tuple = (),
    medidas: list[dict] | tuple = (),
    particoes: list[dict] | tuple = (),
    hierarquias: list[dict] | tuple = (),
    data_category: str | None = None,
    annotations: dict[str, str] | None = None,
) -> dict:
    bruto: dict = {
        "name": nome,
        "columns": list(colunas),
        "measures": list(medidas),
        "partitions": list(particoes),
    }
    if hierarquias:
        bruto["hierarchies"] = list(hierarquias)
    if data_category is not None:
        bruto["dataCategory"] = data_category
    if annotations:
        bruto["annotations"] = _annotations(annotations)
    return bruto


def relacionamento(
    origem: str,
    coluna_origem: str,
    destino: str,
    coluna_destino: str,
    *,
    bidirecional: bool = False,
    cross_filtering: str | None = None,
    cardinalidade_origem: str | None = None,
    cardinalidade_destino: str | None = None,
    ativo: bool = True,
) -> dict:
    """Um relacionamento TMSL.

    `cross_filtering` existe para exercitar valores que não são
    `bothDirections`, como `automatic`.
    """
    bruto: dict = {
        "name": f"{origem}-{destino}-{coluna_origem}",
        "fromTable": origem,
        "fromColumn": coluna_origem,
        "toTable": destino,
        "toColumn": coluna_destino,
    }
    if bidirecional:
        bruto["crossFilteringBehavior"] = "bothDirections"
    elif cross_filtering is not None:
        bruto["crossFilteringBehavior"] = cross_filtering
    if cardinalidade_origem is not None:
        bruto["fromCardinality"] = cardinalidade_origem
    if cardinalidade_destino is not None:
        bruto["toCardinality"] = cardinalidade_destino
    if not ativo:
        bruto["isActive"] = False
    return bruto


def modelo_tmsl(tabelas=(), relacionamentos=(), roles=()) -> dict:
    model: dict = {
        "culture": "pt-BR",
        "tables": list(tabelas),
        "relationships": list(relacionamentos),
    }
    if roles:
        model["roles"] = list(roles)
    return {"name": "SemanticModel", "compatibilityLevel": 1600, "model": model}


def _annotations(pares: dict[str, str]) -> list[dict]:
    return [{"name": n, "value": v} for n, v in pares.items()]


@pytest.fixture
def ler(tmp_path: Path):
    """Escreve um `model.bim` sintético e devolve o modelo já parseado.

    As regras recebem `ModeloSemantico`, não dicionário. Passar pelo parser nos
    testes garante que o que a regra lê é o que o parser produz.
    """

    def _ler(tabelas=(), relacionamentos=(), roles=()) -> ModeloSemantico:
        caminho = tmp_path / "model.bim"
        caminho.write_text(
            json.dumps(
                modelo_tmsl(tabelas, relacionamentos, roles), ensure_ascii=False
            ),
            encoding="utf-8",
        )
        return ler_modelo(caminho)

    return _ler
