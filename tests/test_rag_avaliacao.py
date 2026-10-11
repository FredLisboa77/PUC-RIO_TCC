"""Conjunto de avaliação da recuperação: gabarito, consultas e métricas.

Dados sintéticos; os testes sobre a base e os PBIP reais estão em
`test_rag_avaliacao_real.py`.
"""

import pytest

from core.rules.todas import REGISTRO
from rag.avaliacao import (
    ARQUIVO_GABARITO,
    ErroDeAvaliacao,
    FraseMarca,
    ler_frases_marca,
)


def test_ler_frases_marca_ordena_por_regra(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-006\n  frase_marca: b\n- id_regra: MOD-003\n  frase_marca: a\n",
        encoding="utf-8",
    )
    assert ler_frases_marca(arquivo) == [
        FraseMarca(id_regra="MOD-003", frase_marca="a"),
        FraseMarca(id_regra="MOD-006", frase_marca="b"),
    ]


def test_gabarito_ausente_falha(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="não existe"):
        ler_frases_marca(tmp_path / "nao-existe.yaml")


def test_regra_repetida_no_gabarito_falha(tmp_path):
    arquivo = tmp_path / "gabarito.yaml"
    arquivo.write_text(
        "- id_regra: MOD-003\n  frase_marca: a\n- id_regra: MOD-003\n  frase_marca: b\n",
        encoding="utf-8",
    )
    with pytest.raises(ErroDeAvaliacao, match="MOD-003.*mais de uma vez"):
        ler_frases_marca(arquivo)


def test_gabarito_versionado_cobre_exatamente_as_regras_do_registro():
    frases = ler_frases_marca(ARQUIVO_GABARITO)
    assert [f.id_regra for f in frases] == REGISTRO.ids()
    assert all(0 < len(f.frase_marca.split()) <= 12 for f in frases)
