"""Tabelas da monografia geradas de eval/results."""

from academico.compilacao import compilar
from academico.tabelas import (
    PASTA_GERADO,
    carregar,
    escapar,
    faixa,
    gerar_todas,
    num,
    tabela_catalogo,
    tabela_concordancia,
    tabela_geracao,
    tabela_regras,
)

BLOCO_REGRAS = {
    "origem": "regras-x.json",
    "por_regra": {
        "MOD-002": {
            "matriz": {"vp": 0, "fp": 0, "fn": 0, "vn": 45, "ind_marcados": 0, "ind_nao_marcados": 0},
            "taxas": {"precisao": {"principal": None}, "recall": {"principal": None}},
            "wilson": {"precisao": None, "recall": None},
        },
        "DAX-001": {
            "matriz": {"vp": 6, "fp": 0, "fn": 0, "vn": 4, "ind_marcados": 1, "ind_nao_marcados": 2},
            "taxas": {
                "precisao": {"principal": 1.0, "piso": 0.857, "teto": 1.0},
                "recall": {"principal": 1.0, "piso": 0.667, "teto": 1.0},
            },
            "wilson": {"precisao": [0.6096, 0.99999], "recall": [0.6096, 0.99999]},
        },
        "MOD-007": {
            "matriz": {"vp": 1, "fp": 0, "fn": 0, "vn": 45, "ind_marcados": 0, "ind_nao_marcados": 0},
            "taxas": {
                "precisao": {"principal": 1.0, "piso": 1.0, "teto": 1.0},
                "recall": {"principal": 1.0, "piso": 1.0, "teto": 1.0},
            },
            "wilson": {"precisao": [0.2065, 1.0], "recall": [0.2065, 1.0]},
        },
    },
    "total_micro": {
        "matriz": {"vp": 6, "fp": 0, "fn": 0, "vn": 49, "ind_marcados": 1, "ind_nao_marcados": 2},
        "taxas": {"precisao": {"principal": 1.0}, "recall": {"principal": 1.0}},
        "wilson": {"precisao": [0.6096, 0.99999], "recall": [0.6096, 0.99999]},
    },
}


def test_num_usa_virgula_e_traco_para_ausente():
    assert num(0.8846) == "0,88"
    assert num(-0.0796) == "-0,08"
    assert num(None) == "—"
    assert num(0.61296, 3) == "0,613"


def test_faixa_wilson():
    assert faixa([0.6096, 0.99999]) == "[0,61; 1,00]"
    assert faixa(None) == "—"


def test_escapar_neutraliza_marcacao_do_typst():
    assert escapar("a*b_c#d@e<f>$g") == r"a\*b\_c\#d\@e\<f\>\$g"
    assert escapar(r"x\y") == r"x\\y"


def test_escapar_mantem_literal_a_sintaxe_que_depende_de_posicao(tmp_path):
    import json

    import typst

    from academico.tabelas import _celula

    textos = ["a // b c", "- item", "= titulo", "+ mais", "1. lista", "x /* y"]
    doc = tmp_path / "doc.typ"
    doc.write_text("#table(columns: 1, " + ", ".join(_celula(t) for t in textos) + ")", encoding="utf-8")
    assert compilar(doc).startswith(b"%PDF")
    for elemento in ("list", "enum", "heading"):
        assert json.loads(typst.query(str(doc), elemento, root=str(tmp_path))) == [], elemento


def test_tabela_regras_ordena_mostra_ausente_e_total():
    texto = tabela_regras(BLOCO_REGRAS, "tab-x", "Legenda")
    assert texto.index("[DAX-001]") < texto.index("[MOD-002]")
    assert "[MOD-002], [0], [0], [0], [0], [0], [—], [—], [—]" in texto
    assert r"[DAX-001], [6], [0], [0], [1], [2], [1,00 (0,86–1,00)], [\[0,61; 1,00\]], [1,00 (0,67–1,00)]" in texto


def test_tabela_regras_omite_piso_e_teto_quando_coincidem_com_o_principal():
    texto = tabela_regras(BLOCO_REGRAS, "tab-x", "Legenda")
    assert r"[MOD-007], [1], [0], [0], [0], [0], [1,00], [\[0,21; 1,00\]], [1,00]" in texto
    assert "[*Total (micro)*]" in texto
    assert texto.rstrip().endswith("`regras-x.json`.]")
    assert "<tab-x>" in texto


def test_tabela_geracao_conta_n_com_indeterminados():
    bloco = {
        "origem": "g.json",
        "itens": {
            nome: {"total": {"n": {"sim": 2, "nao": 1, "indeterminado": 1}, "principal": 0.5, "wilson": [0.1, 0.9]}}
            for nome in ("pertinente", "fiel", "recomendacao_correta")
        },
        "utilizavel": {"total": {"n": {"sim": 1, "nao": 3, "indeterminado": 0}, "principal": 0.25, "wilson": [0.05, 0.7]}},
    }
    texto = tabela_geracao(bloco)
    assert r"[Fiel], [2 \/ 4], [0,50], [\[0,10; 0,90\]]" in texto
    assert r"[*Utilizável como está*], [1 \/ 4], [0,25], [\[0,05; 0,70\]]" in texto


def test_tabela_concordancia_explica_as_celulas():
    bloco = {
        "origem": "g.json",
        "concordancia": {
            "pertinente": {"tabela": {"a": 60, "b": 0, "c": 1, "d": 0}, "n": 61, "concordancia": 0.9836, "kappa": 0.0},
            "fiel": {"tabela": {"a": 24, "b": 24, "c": 8, "d": 5}, "n": 61, "concordancia": 0.4754, "kappa": -0.0796},
        },
    }
    texto = tabela_concordancia(bloco)
    assert r"[Fiel], [Sem aviso de números ou nomes], [24], [24], [8], [5], [0,48], [\-0,08]" in texto


def test_catalogo_usa_os_termos_do_texto():
    texto = tabela_catalogo()
    assert "[desempenho]" in texto and "[performance]" not in texto
    assert "[média]" in texto and "[media]" not in texto
    assert "[DAX]" in texto


def test_arquivos_gerados_em_dia_com_o_consolidado():
    esperadas = gerar_todas(carregar())
    assert sorted(p.name for p in PASTA_GERADO.glob("*.typ")) == sorted(esperadas)
    for nome, conteudo in esperadas.items():
        assert (PASTA_GERADO / nome).read_text(encoding="utf-8") == conteudo, (
            f"{nome} desatualizado: rode `python -m academico tabelas`"
        )


def test_cada_tabela_gerada_compila_incluida_como_no_capitulo(tmp_path):
    abnt = (PASTA_GERADO.parent / "abnt.typ").read_text(encoding="utf-8")
    (tmp_path / "abnt.typ").write_text(abnt, encoding="utf-8")
    (tmp_path / "gerado").mkdir()
    (tmp_path / "capitulos").mkdir()
    for nome, conteudo in gerar_todas(carregar()).items():
        (tmp_path / "gerado" / nome).write_text(conteudo, encoding="utf-8")
        (tmp_path / "capitulos" / "c.typ").write_text(f'#include "../gerado/{nome}"\n', encoding="utf-8")
        doc = tmp_path / "doc.typ"
        doc.write_text('#import "abnt.typ": abnt\n#show: abnt\n#include "capitulos/c.typ"\n', encoding="utf-8")
        assert compilar(doc).startswith(b"%PDF"), nome


def test_atualizar_readme_substitui_so_o_miolo_do_bloco():
    from academico.tabelas import atualizar_readme

    texto = "antes\n<!-- tabela:regras -->\nvelho\n<!-- /tabela -->\ndepois\n"
    novo = atualizar_readme(texto, {"regras": "| a |\n|---|\n| 1 |"})
    assert novo == "antes\n<!-- tabela:regras -->\n| a |\n|---|\n| 1 |\n<!-- /tabela -->\ndepois\n"


def test_atualizar_readme_bloco_ausente_e_erro():
    import pytest

    from academico.tabelas import atualizar_readme

    with pytest.raises(KeyError, match="geracao"):
        atualizar_readme("sem blocos", {"geracao": "x"})


def test_blocos_markdown_numeros_em_portugues():
    from academico.tabelas import blocos_markdown

    blocos = blocos_markdown(carregar())
    assert set(blocos) == {"regras", "recuperacao", "geracao"}
    assert "| **Total (micro)** | 46 | 6 | 6 |" in blocos["regras"]
    assert "| Fiel | 32 / 61 | 0,52 |" in blocos["geracao"]


def test_readme_em_dia_com_o_consolidado():
    from academico.tabelas import README, atualizar_readme, blocos_markdown

    texto = README.read_text(encoding="utf-8")
    assert atualizar_readme(texto, blocos_markdown(carregar())) == texto, "rode `python -m academico tabelas`"
