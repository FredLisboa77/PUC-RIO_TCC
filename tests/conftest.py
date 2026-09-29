"""Construtores de PBIP sintéticos para os testes.

Um PBIP real tem centenas de arquivos. Os testes precisam apenas da parte que o
MVP lê: a pasta `.SemanticModel` com `definition.pbism` e `model.bim`. O
construtor abaixo monta exatamente isso, e permite variar cada peça para
exercitar os casos de erro.
"""

import json
from pathlib import Path

import pytest

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
