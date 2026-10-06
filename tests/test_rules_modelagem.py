"""As regras de modelagem.

Cada regra tem caso positivo e negativo. Os negativos são o que separa uma
auditoria útil de uma lista de ruído, e vários deles vêm de falsos positivos
observados no P8.
"""

from core.rules.modelagem import (
    relacionamento_bidirecional,
    tabela_sem_relacionamento,
    tempo_automatico_ligado,
)
from conftest import coluna, medida, particao, relacionamento, tabela


def test_mod001_marca_cada_tabela_de_data_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela("DateTableTemplate_abc", annotations={"__PBI_TemplateDateTable": "true"}),
            tabela("LocalDateTable_def", annotations={"__PBI_LocalDateTable": "true"}),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
        ]
    )

    achados = list(tempo_automatico_ligado(modelo))

    assert {a.evidencia.objeto for a in achados} == {
        "DateTableTemplate_abc",
        "LocalDateTable_def",
    }
    assert all(a.id_regra == "MOD-001" for a in achados)
    assert all(a.evidencia.tipo_objeto == "tabela" for a in achados)
    assert achados[0].evidencia.detalhe["annotation"] in (
        "__PBI_TemplateDateTable",
        "__PBI_LocalDateTable",
    )


def test_mod001_nao_marca_modelo_sem_tempo_automatico(ler):
    modelo = ler(tabelas=[tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")])])

    assert list(tempo_automatico_ligado(modelo)) == []


def test_mod002_marca_relacionamento_bidirecional(ler):
    modelo = ler(
        tabelas=[
            tabela("DimProduct", colunas=[coluna("SubKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey", bidirecional=True)
        ],
    )

    achados = list(relacionamento_bidirecional(modelo))

    assert len(achados) == 1
    assert achados[0].id_regra == "MOD-002"
    assert achados[0].evidencia.tipo_objeto == "relacionamento"
    assert "DimProduct[SubKey]" in achados[0].evidencia.objeto
    assert achados[0].evidencia.detalhe["crossFilteringBehavior"] == "bothDirections"


def test_mod002_ignora_um_para_um(ler):
    """Review Focus 2: todo um-para-um é obrigatoriamente bidirecional.

    A documentação diz que não é possível configurar de outro jeito, então o
    achado de bidirecional traria recomendação impossível de cumprir. O problema
    real é o um-para-um, e quem o afirma é MOD-007.
    """
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento(
                "DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                bidirecional=True, cardinalidade_origem="one",
            )
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod002_ignora_cross_filtering_automatic(ler):
    """Review Focus 4: `automatic` deixa o motor decidir, não é bidirecional."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey", cross_filtering="automatic")
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod002_ignora_relacionamento_com_tabela_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[
            relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date", bidirecional=True)
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod003_marca_tabela_sem_relacionamento(ler):
    modelo = ler(
        tabelas=[
            tabela("DimEmployee", colunas=[coluna("EmployeeKey", tipo_dado="int64")]),
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    achados = list(tabela_sem_relacionamento(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimEmployee"]
    assert achados[0].id_regra == "MOD-003"


def test_mod003_ignora_tabela_apenas_de_medidas(ler):
    """Como a `_Medidas` do P8: 92 medidas, zero relacionamento, e tudo certo."""
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64")],
                medidas=[medida("Faturamento")],
                particoes=[particao(tipo="calculated", expressao='Row("Coluna", BLANK())')],
            )
        ]
    )

    assert list(tabela_sem_relacionamento(modelo)) == []


def test_mod003_ignora_parametro_hipotetico_e_tabela_de_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela("Parâmetro", particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")]),
            tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "1"}),
        ]
    )

    assert list(tabela_sem_relacionamento(modelo)) == []


def test_mod003_considera_relacionada_a_tabela_ligada_so_a_uma_automatica(ler):
    """A tabela automática está fora de escopo, mas o relacionamento existe."""
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date")],
    )

    assert list(tabela_sem_relacionamento(modelo)) == []
