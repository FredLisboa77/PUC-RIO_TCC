"""As regras de modelagem.

Cada regra tem caso positivo e negativo. Os negativos são o que separa uma
auditoria útil de uma lista de ruído, e vários deles vêm de falsos positivos
observados no P8.
"""

from core.rules.modelagem import (
    dimensao_de_data_nao_marcada,
    dimensao_em_floco_de_neve,
    relacionamento_bidirecional,
    relacionamento_um_para_um,
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


def test_mod005_marca_dimensao_de_data_sem_data_category(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    achados = list(dimensao_de_data_nao_marcada(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimCalendar"]
    assert achados[0].id_regra == "MOD-005"
    assert achados[0].evidencia.detalhe["dataCategory"] is None


def test_mod005_nao_marca_dimensao_de_data_ja_marcada(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")], data_category="Time"),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []


def test_mod005_ignora_tabelas_de_data_automaticas(ler):
    """Review Focus 1: em P8 isso valeria 3 achados inventados.

    `DimPromotion[StartDate] → LocalDateTable_x[Date]` é `dateTime → dateTime` e
    a tabela automática não tem `dataCategory`. Sem o filtro de escopo, MOD-005
    marcaria exatamente os objetos que MOD-001 já aponta — e pediria ao autor
    para marcar como tabela de data algo que ele não criou.
    """
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []


def test_mod005_ignora_relacionamento_que_nao_e_entre_datas(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []


def test_mod006_marca_a_dimensao_intermediaria_da_cadeia(ler):
    """A cadeia do P8: FactOnlineSales → DimProduct → DimProductSubcategory."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("ProductKey", tipo_dado="int64")]),
            tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "ProductKey", "DimProduct", "ProductKey"),
            relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey"),
        ],
    )

    achados = list(dimensao_em_floco_de_neve(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimProduct"]
    assert achados[0].id_regra == "MOD-006"
    assert achados[0].evidencia.detalhe["aponta_para"] == ["DimProductSubcategory"]


def test_mod006_nao_marca_estrela_simples(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey"),
            relacionamento("FactOnlineSales", "CustomerKey", "DimCustomer", "CustomerKey"),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod006_nao_confunde_um_para_um_com_floco_de_neve(ler):
    """Review Focus 2: num um-para-um nenhuma ponta é lado "muitos".

    No P8, `DimGeography → DimCustomer` é um-para-um. Presumir que o lado `from`
    é sempre "muitos" faria a `DimCustomer` aparecer como intermediária de uma
    cadeia que não existe.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "CustomerKey", "DimCustomer", "CustomerKey"),
            relacionamento("DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                           cardinalidade_origem="one"),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod007_marca_relacionamento_um_para_um(ler):
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                           bidirecional=True, cardinalidade_origem="one"),
        ],
    )

    achados = list(relacionamento_um_para_um(modelo))

    assert len(achados) == 1
    assert achados[0].id_regra == "MOD-007"
    assert achados[0].evidencia.tipo_objeto == "relacionamento"
    assert achados[0].evidencia.detalhe["cardinalidade"] == "um-para-um"


def test_mod007_nao_marca_muitos_para_um(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    assert list(relacionamento_um_para_um(modelo)) == []


# --- correções da revisão final ---


def test_mod006_nao_marca_tabela_cujo_unico_papel_um_vem_de_um_para_um(ler):
    """O dual do Review Focus 2, que o P8 não exibe.

    `lado_um` devolve as duas pontas de um um-para-um, e com razão — as duas são
    lado "um". Mas MOD-006 não pode usar isso: se o único papel "um" de uma
    tabela vem de um um-para-um, não há cadeia dimensão-para-dimensão. Pior, o
    achado saía com a frase quebrada ("é filtrada por  e filtra Z"), porque o
    lado "muitos" do um-para-um é vazio.
    """
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("DimCountry", colunas=[coluna("k", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimGeography", "k", "DimCustomer", "k", cardinalidade_origem="one"),
            relacionamento("DimCustomer", "k", "DimCountry", "k"),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod006_nao_marca_cadeia_cujo_elo_e_muitos_para_muitos(ler):
    """O outro caminho para a frase quebrada, e para o achado errado.

    Num muitos-para-muitos `lado_um` é vazio, então uma tabela que é lado "um"
    noutro relacionamento entrava na interseção com um dos lados da cadeia
    vazio — e a mensagem saía com um buraco onde devia haver nome de tabela.
    Uma cadeia precisa das duas pontas.
    """
    modelo = ler(
        tabelas=[
            tabela("Vendedor", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("Regiao", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("FactVendas", colunas=[coluna("k", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("Vendedor", "k", "Regiao", "k",
                           cardinalidade_origem="many", cardinalidade_destino="many"),
            relacionamento("FactVendas", "k", "Vendedor", "k"),
        ],
    )

    for achado in dimensao_em_floco_de_neve(modelo):
        assert achado.evidencia.detalhe["aponta_para"], achado.mensagem
        assert achado.evidencia.detalhe["recebe_de"], achado.mensagem


def test_mod002_ignora_relacionamento_inativo(ler):
    """Relacionamento inativo não propaga filtro nenhum até `USERELATIONSHIP`.

    A página argumenta a partir de desempenho de consulta e de ambiguidade de
    filtro, e nenhum dos dois existe num relacionamento inativo. Dizer que ele
    "filtra nos dois sentidos" seria afirmar o que não acontece.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DataPedido", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "DataPedido", "DimCalendar", "Data",
                           bidirecional=True, ativo=False),
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod006_ignora_relacionamento_inativo(ler):
    """Sem propagação de filtro não há cadeia de floco de neve."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("DimProduct", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("k", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "k", "DimProduct", "k"),
            relacionamento("DimProduct", "k", "DimProductSubcategory", "k", ativo=False),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod007_marca_um_para_um_mesmo_inativo(ler):
    """Aqui o problema é o desenho, não a propagação: duas tabelas para a mesma
    entidade continuam sendo duas tabelas, com o relacionamento ativo ou não."""
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("k", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("k", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimGeography", "k", "DimCustomer", "k",
                           cardinalidade_origem="one", ativo=False),
        ],
    )

    assert len(list(relacionamento_um_para_um(modelo))) == 1


def test_mod005_marca_dimensao_de_data_com_chave_inteira(ler):
    """O caso em que a própria recomendação de MOD-005 diz que marcar é preciso."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="int64")]),
            tabela(
                "DimCalendar",
                colunas=[coluna("DateKey", tipo_dado="int64")],
                particoes=[particao(tipo="calculated", expressao="CALENDARAUTO()")],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "DateKey")],
    )

    achados = list(dimensao_de_data_nao_marcada(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimCalendar"]
