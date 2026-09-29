"""Verificação contra o PBIP real (P8).

`data/` não é versionado, então estes testes são pulados em qualquer máquina que
não tenha o projeto. Eles existem para garantir que o parser continue lendo um
`model.bim` de verdade — 883 KB, 1600 de compatibilidade — e não apenas as
fixtures sintéticas.

Os números conferidos aqui são o inventário registrado no progress-log em
23/09/2026, com uma correção: as tabelas de data automáticas são 4, não 5.
"""

from pathlib import Path

import pytest

from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo

P8 = Path("data/pbip/P8_contoso-vendas")

pytestmark = pytest.mark.skipif(
    not P8.is_dir(), reason="PBIP P8 não está presente (data/ não é versionado)"
)


@pytest.fixture(scope="module")
def modelo():
    return ler_modelo(abrir_pbip(P8).model_bim)


def test_inventario_do_modelo_confere_com_o_registrado(modelo):
    colunas = [c for t in modelo.tabelas for c in t.colunas]
    calculadas = [c for t in modelo.tabelas for c in t.colunas_calculadas]

    assert modelo.compatibility_level == 1600
    assert len(modelo.tabelas) == 19
    assert len(modelo.medidas) == 93
    assert len(colunas) == 106
    assert len(calculadas) == 35
    assert len(modelo.relacionamentos) == 11


def test_encontra_as_quatro_tabelas_de_data_automaticas(modelo):
    automaticas = [
        t.nome
        for t in modelo.tabelas
        if t.nome.startswith(("DateTableTemplate_", "LocalDateTable_"))
    ]

    assert len(automaticas) == 4
    assert sum(n.startswith("DateTableTemplate_") for n in automaticas) == 1
    assert sum(n.startswith("LocalDateTable_") for n in automaticas) == 3


def test_o_modelo_tem_calendario_proprio_alem_das_automaticas(modelo):
    """É o que torna as tabelas automáticas um achado, e não uma necessidade."""
    nomes = {t.nome for t in modelo.tabelas}

    assert "DimCalendar" in nomes


def test_as_medidas_estao_concentradas_em_uma_tabela(modelo):
    por_tabela = {}
    for m in modelo.medidas:
        por_tabela[m.tabela] = por_tabela.get(m.tabela, 0) + 1

    assert por_tabela["_Medidas"] == 92
