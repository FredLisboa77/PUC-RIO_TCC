"""As regras de performance estática.

PERF-001 tem a exclusão mais importante do conjunto: a documentação que a
sustenta recomenda explicitamente colunas calculadas numa tabela de data em DAX.
Seis dos sete achados que a regra produzia no P8 eram padrão recomendado.
"""

from core.rules.performance import coluna_calculada_em_dax, ponto_flutuante_somado
from conftest import coluna, particao, relacionamento, tabela


def test_perf001_marca_coluna_calculada_em_dax(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimEmployee",
                colunas=[
                    coluna("Base", tipo_dado="decimal", resumir_por="sum"),
                    coluna("Salário", tipo="calculated", tipo_dado="decimal",
                           expressao="[Base] * 1.1", resumir_por="sum"),
                ],
            )
        ]
    )

    achados = list(coluna_calculada_em_dax(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimEmployee[Salário]"]
    assert achados[0].id_regra == "PERF-001"
    assert achados[0].evidencia.tipo_objeto == "coluna"
    assert achados[0].evidencia.tabela == "DimEmployee"
    assert achados[0].evidencia.trecho == "[Base] * 1.1"


def test_perf001_ignora_coluna_da_dimensao_de_data(ler):
    """A página de tempo automático recomenda exatamente isto.

    "You can then add calculated columns to support the known time filtering and
    grouping requirements." Marcar essas colunas seria produzir um achado que a
    fonte citada refuta.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela(
                "DimCalendar",
                colunas=[
                    coluna("Data", tipo_dado="dateTime"),
                    coluna("Ano", tipo="calculated", expressao="YEAR([Data])"),
                    coluna("Trimestre", tipo="calculated", expressao='"T" & QUARTER([Data])'),
                ],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf001_ignora_coluna_de_agrupamento_ou_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimCustomer",
                colunas=[
                    coluna("Faixa de Renda", tipo="calculated", expressao="SWITCH(...)",
                           annotations={"GroupingDesignState": "{}"}),
                ],
            )
        ]
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf001_ignora_coluna_de_tabela_calculada(ler):
    """`calculatedTableColumn` é coluna de tabela calculada, não coluna em DAX."""
    modelo = ler(
        tabelas=[
            tabela(
                "Tabela",
                colunas=[
                    coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64"),
                    coluna("Normal", tipo_dado="string"),
                ],
            )
        ]
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf003_marca_ponto_flutuante_somado(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Previsões",
                colunas=[
                    coluna("Previsao", tipo_dado="double", resumir_por="sum"),
                    coluna("Fator", tipo_dado="double", resumir_por="none"),
                    coluna("Valor", tipo_dado="decimal", resumir_por="sum"),
                ],
            )
        ]
    )

    achados = list(ponto_flutuante_somado(modelo))

    assert [a.evidencia.objeto for a in achados] == ["Previsões[Previsao]"]
    assert achados[0].id_regra == "PERF-003"
    assert achados[0].evidencia.detalhe == {"dataType": "double", "summarizeBy": "sum"}


def test_perf003_ignora_tabela_fora_de_escopo(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "ClusterMappingTable",
                colunas=[coluna("Previsao", tipo_dado="double", resumir_por="sum")],
                annotations={"ClusterMappingTable": "1"},
            )
        ]
    )

    assert list(ponto_flutuante_somado(modelo)) == []



# --- correções da revisão final ---


def test_perf001_ignora_dimensao_de_data_com_chave_inteira(ler):
    """A dimensão de data da convenção de data warehouse.

    `FactSales[DateKey] int64 → DimCalendar[DateKey] int64` é o padrão Kimball.
    Sem reconhecê-la, PERF-001 marca as colunas de calendário que a página de
    tempo automático recomenda acrescentar — achado refutado pela fonte citada.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="int64")]),
            tabela(
                "DimCalendar",
                colunas=[
                    coluna("DateKey", tipo_dado="int64"),
                    coluna("Ano", tipo="calculated", expressao="YEAR([Data])"),
                    coluna("Mês", tipo="calculated", expressao="FORMAT([Data], \"MMMM\")"),
                ],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(DATE(2020,1,1), DATE(2024,12,31))")],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "DateKey")],
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


