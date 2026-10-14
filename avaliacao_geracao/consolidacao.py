"""Consolidado dos resultados: a fonte única das tabelas da monografia.

O resultado oficial da detecção é o da tag `regras-gt`; o arquivo de origem não
é alterado — o Wilson é acrescentado só aqui. A pós-correção vai junto, rotulada
como análise de erros.
"""

import copy
import json
import re
from pathlib import Path

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.estatistica import wilson
from rag.avaliacao import RAIZ_REPO

PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"
ORIGENS = {
    "regras": "regras-2026-10-12.json",
    "regras_pos_correcao": "regras-2026-10-12-pos-correcao.json",
    "recuperacao": "recuperacao-2026-10-11.json",
    "complementares": "complementares-2026-10-12.json",
}


PADRAO_GERACAO = re.compile(r"^geracao-\d{4}-\d{2}-\d{2}\.json$")


def _ler(pasta: Path, nome: str) -> dict:
    caminho = pasta / nome
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"falta {nome} em {pasta}")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _wilson_da_matriz(bloco: dict) -> dict:
    m = bloco["matriz"]
    precisao = wilson(m["vp"], m["vp"] + m["fp"])
    recall = wilson(m["vp"], m["vp"] + m["fn"])
    return {"precisao": list(precisao) if precisao else None, "recall": list(recall) if recall else None}


def _com_wilson(regras: dict, origem: str, rotulo: str) -> dict:
    saida = copy.deepcopy(regras)
    for grupo in ("por_regra", "por_categoria"):
        for bloco in saida.get(grupo, {}).values():
            bloco["wilson"] = _wilson_da_matriz(bloco)
    if "total_micro" in saida:
        saida["total_micro"]["wilson"] = _wilson_da_matriz(saida["total_micro"])
    return {"origem": origem, "rotulo": rotulo, **saida}


def consolidar(pasta: Path = PASTA_RESULTADOS) -> dict:
    regras = _ler(pasta, ORIGENS["regras"])
    pos = _ler(pasta, ORIGENS["regras_pos_correcao"])
    recuperacao = _ler(pasta, ORIGENS["recuperacao"])
    complementares = _ler(pasta, ORIGENS["complementares"])
    geracoes = sorted(p for p in pasta.glob("geracao-*.json") if PADRAO_GERACAO.match(p.name))
    if not geracoes:
        raise ErroDeAvaliacao(f"falta geracao-<data>.json em {pasta} — rode `python -m avaliacao_geracao medir`")

    vencedora = recuperacao["decisao"]["vencedora"]
    escolhida = next((r for r in recuperacao["resultados"] if r["configuracao"] == vencedora), None)
    if escolhida is None:
        raise ErroDeAvaliacao(f"falta o resultado da configuração vencedora em {ORIGENS['recuperacao']}")
    return {
        "regras": _com_wilson(regras, ORIGENS["regras"], "resultado oficial (tag regras-gt)"),
        "regras_pos_correcao": _com_wilson(pos, ORIGENS["regras_pos_correcao"], "análise de erros"),
        "recuperacao": {
            "origem": ORIGENS["recuperacao"], "configuracao": vencedora, "macro": escolhida["macro"],
            "justificativa": recuperacao["decisao"].get("justificativa"),
        },
        "complementares": {
            "origem": ORIGENS["complementares"],
            "macro": {busca: v["macro"] for busca, v in complementares["por_busca"].items()},
            "decisao": complementares["decisao"],
        },
        "geracao": {"origem": geracoes[-1].name, **json.loads(geracoes[-1].read_text(encoding="utf-8"))},
    }
