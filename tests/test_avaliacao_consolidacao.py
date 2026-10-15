"""Consolidado: fonte única das tabelas da monografia."""

import json

import pytest

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.consolidacao import ORIGENS, consolidar


def _matriz(vp, fp, fn):
    return {"matriz": {"vp": vp, "fp": fp, "fn": fn, "vn": 0, "ind_marcados": 0, "ind_nao_marcados": 0},
            "taxas": {"precisao": {"principal": vp / (vp + fp)}, "recall": {"principal": vp / (vp + fn)}}}


def _regras():
    return {"por_regra": {"MOD-001": _matriz(10, 0, 0)}, "por_categoria": {"modelagem": _matriz(46, 6, 6)},
            "total_micro": _matriz(46, 6, 6), "macro": {"precisao": 0.88}}


def _escrever(pasta, sem=None):
    conteudos = {
        "regras": _regras(),
        "regras_pos_correcao": _regras(),
        "recuperacao": {
            "decisao": {"vencedora": {"busca": "bm25"}, "justificativa": "j"},
            "resultados": [{"configuracao": {"busca": "densa"}, "macro": {"mrr": 0.1}},
                           {"configuracao": {"busca": "bm25"}, "macro": {"mrr": 0.9, "acerto": {"5": 1.0}}}],
        },
        "complementares": {"por_busca": {"bm25": {"macro": {"principal": 0.62}}}, "decisao": {"vencedora": "bm25"}},
    }
    for chave, nome in ORIGENS.items():
        if chave != sem:
            (pasta / nome).write_text(json.dumps(conteudos[chave]), encoding="utf-8")
    if sem != "geracao":
        (pasta / "geracao-2026-10-14.json").write_text(json.dumps({"itens": {"velho": 1}}), encoding="utf-8")
        (pasta / "geracao-2026-10-15.json").write_text(json.dumps({"itens": {"novo": 1}}), encoding="utf-8")


def test_consolida_com_wilson_e_origens(tmp_path):
    _escrever(tmp_path)
    c = consolidar(tmp_path)
    assert c["regras"]["origem"] == ORIGENS["regras"]
    assert [round(x, 4) for x in c["regras"]["total_micro"]["wilson"]["precisao"]] == [0.7703, 0.946]
    assert c["regras"]["por_regra"]["MOD-001"]["wilson"]["recall"][1] == 1.0
    assert c["recuperacao"]["macro"]["mrr"] == 0.9
    assert c["complementares"]["macro"] == {"bm25": {"principal": 0.62}}
    assert c["geracao"]["origem"] == "geracao-2026-10-15.json" and c["geracao"]["itens"] == {"novo": 1}


@pytest.mark.parametrize("sem", [*ORIGENS, "geracao"])
def test_origem_ausente_diz_qual(tmp_path, sem):
    _escrever(tmp_path, sem=sem)
    with pytest.raises(ErroDeAvaliacao, match="falta"):
        consolidar(tmp_path)


def test_ignora_geracao_com_nome_fora_do_padrao(tmp_path):
    _escrever(tmp_path)
    pasta = tmp_path
    (pasta / "geracao-2026-10-20-teste.json").write_text(json.dumps({"itens": {"teste": 1}}), encoding="utf-8")
    c = consolidar(pasta)
    assert c["geracao"]["origem"] == "geracao-2026-10-15.json"
