"""Verificação contra o PBIP real (P8).

`data/` não é versionado, então estes testes são pulados em qualquer máquina que
não tenha o projeto. Eles existem para garantir que o parser continue lendo um
`model.bim` de verdade — 883 KB, 1600 de compatibilidade — e não apenas as
fixtures sintéticas.

Os números conferidos aqui são o inventário registrado no progress-log em
23/09/2026, com uma correção: as tabelas de data automáticas são 4, não 5.
"""

from collections import Counter
from pathlib import Path

import pytest

from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.runner import avaliar
from core.rules.todas import REGISTRO

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


ESPERADO_P8 = {
    "MOD-001": 4,  # 1 DateTableTemplate + 3 LocalDateTable
    "MOD-002": 3,  # 4 bidirecionais, menos o um-para-um que MOD-007 assume
    "MOD-003": 2,  # DimEmployee e Tabela de Regressão Linear
    "MOD-005": 1,  # DimCalendar, com tempo automático pendurado na coluna de data
    "MOD-006": 2,  # DimProduct e DimProductSubcategory
    "MOD-007": 1,  # DimGeography → DimCustomer
    "PERF-001": 1,  # DimEmployee[Salário]
    "PERF-003": 1,  # Tabela de Regressão Linear[Previsao]
}


@pytest.fixture(scope="module")
def resultado(modelo):
    return avaliar(modelo, registro=REGISTRO)


def test_as_oito_regras_rodam_sem_falhar_no_pbip_real(resultado):
    assert resultado.regras_com_falha == []
    assert resultado.regras_executadas == 8


def test_as_contagens_por_regra_no_p8(resultado):
    """Trava o rendimento medido em 06/10/2026.

    Se uma mudança futura fizer PERF-001 saltar de 1 para 35, ou MOD-005 de 1
    para 4, as exclusões de escopo quebraram — e é aqui que isso aparece.
    """
    assert Counter(a.id_regra for a in resultado.achados) == Counter(ESPERADO_P8)
    assert len(resultado.achados) == 15


def test_os_objetos_apontados_sao_os_esperados(resultado):
    por_regra: dict[str, list[str]] = {}
    for a in resultado.achados:
        por_regra.setdefault(a.id_regra, []).append(a.evidencia.objeto)

    assert por_regra["MOD-005"] == ["DimCalendar"]
    assert sorted(por_regra["MOD-006"]) == ["DimProduct", "DimProductSubcategory"]
    assert por_regra["PERF-001"] == ["DimEmployee[Salário]"]
    assert por_regra["PERF-003"] == ["Tabela de Regressão Linear[Previsao]"]
    assert "DimGeography[CustomerKey]" in por_regra["MOD-007"][0]
    assert sorted(por_regra["MOD-003"]) == ["DimEmployee", "Tabela de Regressão Linear"]


def test_a_cadeia_causal_do_estudo_de_caso_aparece_nos_achados(resultado):
    """A DimCalendar não marcada é a causa de uma das tabelas automáticas."""

    def objetos_de(id_regra: str) -> set[str]:
        return {a.evidencia.objeto for a in resultado.achados if a.id_regra == id_regra}

    automaticas = objetos_de("MOD-001")

    assert objetos_de("MOD-005") == {"DimCalendar"}
    assert len(automaticas) == 4
    assert all(n.startswith(("DateTableTemplate_", "LocalDateTable_")) for n in automaticas)


def test_a_saida_vem_ordenada_por_severidade(resultado):
    severidades = [REGISTRO.meta(a.id_regra).severidade for a in resultado.achados]
    ordem = {"alta": 0, "media": 1, "baixa": 2}

    assert severidades == sorted(severidades, key=lambda s: ordem[s])


def test_inventario_dos_sitios_estruturais(modelo):
    """Os sítios que a PERF-005 precisa varrer, medidos no P8 em 08/10/2026."""
    niveis = [n for t in modelo.tabelas for h in t.hierarquias for n in h.niveis]
    ordenacoes = [c for t in modelo.tabelas for c in t.colunas if c.ordenar_por]

    assert len(modelo.relacionamentos) == 11
    assert sum(len(t.hierarquias) for t in modelo.tabelas) == 4
    assert len(niveis) == 16
    assert len(ordenacoes) == 10
    assert modelo.roles == []


def test_o_lexer_tokeniza_todo_o_dax_do_p8(modelo):
    """Critério de aceite 1: zero token DESCONHECIDO nas expressões do P8.

    Mede a cobertura do lexer contra um corpus real em vez de contra a
    imaginação de quem o escreveu. É o número que a monografia cita no lugar de
    "usamos expressões regulares".
    """
    from core.dax import tem_desconhecido, tokenizar

    textos = []
    for t in modelo.tabelas:
        textos += [m.expressao for m in t.medidas]
        textos += [c.expressao for c in t.colunas if c.expressao]
        textos += [
            p.origem for p in t.particoes if p.tipo_origem == "calculated" and p.origem
        ]

    assert len(textos) == 137
    falhas = [x for x in textos if tem_desconhecido(tokenizar(x))]
    assert falhas == []
