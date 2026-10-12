"""Quem entra na auditoria.

Princípio: auditar o que o autor escreveu. Cada exclusão aqui evita um falso
positivo concreto, observado no P8 — e nenhuma é por nome de objeto.
"""

import pytest

from core.rules.escopo import (
    anotacoes,
    coluna_gerada_por_analise,
    dax_escrito_pela_ferramenta,
    dimensao_de_data,
    fora_de_escopo,
    grupo_de_calculo,
    lado_muitos,
    lado_um,
    nomes_em_escopo,
    relacionamentos_em_escopo,
    tabela_apenas_de_medidas,
    tabela_automatica_de_data,
    tabela_de_parametro_de_campo,
    tabela_de_parametro_hipotetico,
    tabela_gerada_por_analise,
    tabela_por_nome,
    tabelas_com_dax_do_autor,
    tipo_da_coluna,
    um_para_um,
)
from conftest import coluna, medida, particao, relacionamento, tabela


def test_anotacoes_viram_dicionario(ler):
    modelo = ler(tabelas=[tabela("T", annotations={"PBI_Id": "abc"})])

    assert anotacoes(modelo.tabelas[0].bruto) == {"PBI_Id": "abc"}


def test_anotacoes_de_objeto_sem_annotations(ler):
    modelo = ler(tabelas=[tabela("T")])

    assert anotacoes(modelo.tabelas[0].bruto) == {}


def test_exclui_tabela_automatica_de_data(ler):
    modelo = ler(
        tabelas=[
            tabela("LocalDateTable_x", annotations={"__PBI_LocalDateTable": "true"}),
            tabela("DateTableTemplate_x", annotations={"__PBI_TemplateDateTable": "true"}),
            tabela("DimCalendar"),
        ]
    )
    local, template, calendario = modelo.tabelas

    assert tabela_automatica_de_data(local)
    assert tabela_automatica_de_data(template)
    assert not tabela_automatica_de_data(calendario)
    assert nomes_em_escopo(modelo) == {"DimCalendar"}


def test_exclui_tabela_apenas_de_medidas(ler):
    """Como a `_Medidas` do P8: medidas e nenhuma coluna de dados."""
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64")],
                medidas=[medida("Faturamento")],
                particoes=[particao(tipo="calculated", expressao='Row("Coluna", BLANK())')],
            ),
            tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")]),
        ]
    )
    so_medidas, dimensao = modelo.tabelas

    assert tabela_apenas_de_medidas(so_medidas)
    assert not tabela_apenas_de_medidas(dimensao)


def test_tabela_com_medidas_e_coluna_de_dados_continua_em_escopo(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "FactOnlineSales",
                colunas=[coluna("Valor", tipo_dado="decimal", resumir_por="sum")],
                medidas=[medida("Total")],
            )
        ]
    )

    assert not tabela_apenas_de_medidas(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == {"FactOnlineSales"}


def test_exclui_tabela_de_parametro_hipotetico(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Parâmetro",
                colunas=[coluna("Parâmetro", tipo="calculatedTableColumn", tipo_dado="double")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")],
            )
        ]
    )

    assert tabela_de_parametro_hipotetico(modelo.tabelas[0])


def test_parametro_hipotetico_sem_medida_continua_fora_de_escopo(ler):
    """A exclusão existe por si, não pelo acaso de a tabela ter uma medida."""
    modelo = ler(
        tabelas=[
            tabela(
                "Meta",
                colunas=[coluna("Meta", tipo="calculatedTableColumn", tipo_dado="double")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 100, 10)")],
            )
        ]
    )
    assert not tabela_apenas_de_medidas(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == set()


def test_reconhece_generateseries_com_caixa_espaco_e_comentario(ler):
    """Review Focus 5: um predicado literal demais reabre o falso positivo."""
    variantes = [
        "  generateseries(0, 1, 0.05)",
        "GENERATESERIES (0, 1, 0.05)",
        "// parametro de previsao\n\nGenerateSeries(0, 1, 0.05)",
        ["", "// comentario", "GENERATESERIES(0, 1, 0.05)"],
    ]
    for i, expressao in enumerate(variantes):
        modelo = ler(
            tabelas=[
                tabela(f"P{i}", particoes=[particao(tipo="calculated", expressao=expressao)])
            ]
        )
        assert tabela_de_parametro_hipotetico(modelo.tabelas[0]), expressao


def test_nao_confunde_outra_tabela_calculada_com_parametro(ler):
    modelo = ler(
        tabelas=[tabela("DimCalendar", particoes=[particao(tipo="calculated", expressao="CALENDAR(1, 2)")])]
    )

    assert not tabela_de_parametro_hipotetico(modelo.tabelas[0])


def test_exclui_tabela_gerada_por_analise(ler):
    modelo = ler(tabelas=[tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "1"})])

    assert tabela_gerada_por_analise(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == set()


def test_exclui_coluna_de_agrupamento_ou_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimCustomer",
                colunas=[
                    coluna(
                        "Faixa de Renda",
                        tipo="calculated",
                        expressao="SWITCH(...)",
                        annotations={"GroupingDesignState": "{}"},
                    ),
                    coluna("Salário", tipo="calculated", expressao="[Base] * 1.1", tipo_dado="double"),
                ],
            )
        ]
    )
    faixa, salario = modelo.tabelas[0].colunas

    assert coluna_gerada_por_analise(faixa)
    assert not coluna_gerada_por_analise(salario)


def test_relacionamentos_em_escopo_descartam_pontas_excluidas(ler):
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
            tabela("FactOnlineSales", colunas=[coluna("PromotionKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date"),
            relacionamento("FactOnlineSales", "PromotionKey", "DimPromotion", "PromotionKey"),
        ],
    )

    nomes = [r.nome for r in relacionamentos_em_escopo(modelo)]

    assert nomes == ["FactOnlineSales-DimPromotion-PromotionKey"]


def test_tipo_da_coluna_devolve_none_em_referencia_inexistente(ler):
    """Review Focus 3: modelo inconsistente não pode virar KeyError."""
    modelo = ler(tabelas=[tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")])])

    assert tipo_da_coluna(modelo, "DimProduct", "ProductKey") == "int64"
    assert tipo_da_coluna(modelo, "DimProduct", "NaoExiste") is None
    assert tipo_da_coluna(modelo, "TabelaFantasma", "ProductKey") is None
    assert tabela_por_nome(modelo, "TabelaFantasma") is None


def test_dimensao_de_data_sobrevive_a_relacionamento_orfao(ler):
    """Review Focus 3, continuação: o lookup falho não derruba a detecção."""
    modelo = ler(
        tabelas=[tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")])],
        relacionamentos=[relacionamento("TabelaFantasma", "DateKey", "DimCalendar", "Data")],
    )

    assert dimensao_de_data(modelo) == set()


def test_dimensao_de_data_e_o_lado_um_de_relacionamento_entre_datas(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data"),
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey"),
        ],
    )

    assert dimensao_de_data(modelo) == {"DimCalendar"}


def test_lados_do_relacionamento_respeitam_a_cardinalidade(ler):
    modelo = ler(
        relacionamentos=[
            relacionamento("FactOnlineSales", "k", "DimStore", "k"),
            relacionamento("DimGeography", "k", "DimCustomer", "k", cardinalidade_origem="one"),
        ]
    )
    muitos_para_um, de_um_para_um = modelo.relacionamentos

    assert lado_um(muitos_para_um) == {"DimStore"}
    assert lado_muitos(muitos_para_um) == {"FactOnlineSales"}
    assert not um_para_um(muitos_para_um)

    assert lado_um(de_um_para_um) == {"DimGeography", "DimCustomer"}
    assert lado_muitos(de_um_para_um) == set()
    assert um_para_um(de_um_para_um)


# --- correções da revisão final ---


def test_anotacoes_tolera_annotations_nulo(ler):
    """`"annotations": null` num `model.bim` editado à mão.

    `bruto.get("annotations", [])` devolve `None` quando a chave existe com
    valor nulo, e iterar `None` levanta `TypeError` — em `fora_de_escopo`, o que
    derruba todas as oito regras e entrega auditoria vazia.
    """
    modelo = ler(tabelas=[tabela("T")])
    modelo.tabelas[0].bruto["annotations"] = None

    assert anotacoes(modelo.tabelas[0].bruto) == {}
    assert nomes_em_escopo(modelo) == {"T"}


def test_tabela_calculada_com_medida_e_varias_colunas_continua_em_escopo(ler):
    """Uma dimensão calculada em DAX não sai do escopo por carregar uma medida.

    Toda coluna de tabela calculada é `calculatedTableColumn`, então o único
    sinal que separava a `_Medidas` de uma dimensão de verdade era ter medida.
    Basta o autor pendurar uma medida numa dimensão calculada para a tabela
    inteira deixar de ser auditada, em silêncio.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "DimProdutoCalc",
                colunas=[
                    coluna("ProductKey", tipo="calculatedTableColumn", tipo_dado="int64"),
                    coluna("Nome", tipo="calculatedTableColumn"),
                    coluna("Preco", tipo="calculatedTableColumn", tipo_dado="double", resumir_por="sum"),
                ],
                medidas=[medida("Preço Médio")],
                particoes=[particao(tipo="calculated", expressao="SELECTCOLUMNS(DimProduct, ...)")],
            )
        ]
    )

    assert not tabela_apenas_de_medidas(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == {"DimProdutoCalc"}


def test_dimensao_de_data_reconhece_tabela_marcada_como_tabela_de_data(ler):
    """`dataCategory: "Time"` é a marcação; ela identifica a dimensão sozinha."""
    modelo = ler(
        tabelas=[
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")], data_category="Time"),
        ]
    )

    assert dimensao_de_data(modelo) == {"DimCalendar"}


def test_dimensao_de_data_reconhece_tabela_de_data_com_chave_inteira(ler):
    """A convenção de data warehouse: chave substituta inteira no formato aaaammdd.

    Sem este sinal, a dimensão de data fica invisível, e PERF-001 volta a marcar
    as colunas de calendário que a documentação recomenda acrescentar — o
    defeito que derrubou PERF-004.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="int64")]),
            tabela(
                "DimCalendar",
                colunas=[
                    coluna("DateKey", tipo_dado="int64"),
                    coluna("Ano", tipo="calculated", expressao="YEAR([Data])"),
                ],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(DATE(2020,1,1), DATE(2024,12,31))")],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "DateKey")],
    )

    assert dimensao_de_data(modelo) == {"DimCalendar"}


def test_dimensao_de_data_nao_confunde_outra_tabela_calculada(ler):
    """`SUMMARIZE` não é tabela de data; só `CALENDAR`/`CALENDARAUTO` são."""
    modelo = ler(
        tabelas=[
            tabela(
                "ResumoVendas",
                colunas=[coluna("Ano", tipo="calculatedTableColumn")],
                particoes=[particao(tipo="calculated", expressao="SUMMARIZE(FactOnlineSales, ...)")],
            )
        ]
    )

    assert dimensao_de_data(modelo) == set()


# --- correção de 08/10/2026: DAX da ferramenta vs. DAX do autor ---


def test_dax_do_autor_inclui_a_tabela_so_de_medidas(ler):
    """A tabela de medidas sai das regras de nivel de tabela, nao da auditoria de DAX.

    Ela nao tem relacionamento por natureza, e e por isso que `fora_de_escopo` a
    exclui — nao porque seu DAX seja de outra pessoa. No PBIP real ela carrega
    93 das 105 expressoes do modelo.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
            )
        ]
    )
    t = modelo.tabelas[0]

    assert tabela_apenas_de_medidas(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is False
    assert [x.nome for x in tabelas_com_dax_do_autor(modelo)] == ["_Medidas"]


def test_dax_do_autor_exclui_tabela_de_data_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "LocalDateTable_x",
                colunas=[coluna("Trim", tipo="calculated", expressao="INT([Mes]/3)")],
                annotations={"__PBI_LocalDateTable": "true"},
            )
        ]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []


def test_dax_do_autor_exclui_tabela_de_cluster(ler):
    modelo = ler(
        tabelas=[tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "x"})]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []


def test_dax_do_autor_exclui_parametro_hipotetico(ler):
    """O Desktop escreve a medida do parametro hipotetico, nao o autor.

    No P8: `% Previsao = SELECTEDVALUE('Parametro'[Parametro])`, gerada pelo
    recurso de parametro hipotetico junto com a tabela.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Parametro",
                colunas=[coluna("Parametro", tipo="calculatedTableColumn")],
                medidas=[medida("Valor", "SELECTEDVALUE(Parametro[Parametro])")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.1)")],
            )
        ]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []


def _grupo_de_calculo(nome: str, valor=None) -> dict:
    t = tabela(nome, colunas=[coluna(nome)])
    t["calculationGroup"] = valor if valor is not None else {
        "calculationItems": [
            {"name": "YTD", "expression": "CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))"}
        ]
    }
    return t


def _parametro_de_campo(nome: str, propriedades) -> dict:
    campos = coluna("Parameter Fields", tipo="calculatedTableColumn")
    campos["extendedProperties"] = propriedades
    return tabela(
        nome,
        colunas=[coluna(nome, tipo="calculatedTableColumn"), campos],
        particoes=[particao(tipo="calculated", expressao="{ (\"Area\", NAMEOF('Area'[Area]), 0) }")],
    )


METADADO_DE_CAMPO = [{"name": "ParameterMetadata", "type": "json", "value": {"kind": 2, "version": 3}}]


def test_grupo_de_calculo_fica_fora_de_escopo_mas_o_dax_e_do_autor(ler):
    """Como `Date Role` e `Time Intelligence` do P1: sem relacionamento por natureza,
    mas o DAX dos itens de cálculo é escrito pelo autor."""
    t = ler(tabelas=[_grupo_de_calculo("Time Intelligence")]).tabelas[0]
    assert grupo_de_calculo(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is False


def test_calculation_group_nulo_nao_e_grupo_de_calculo(ler):
    t = tabela("Editada", colunas=[coluna("A")])
    t["calculationGroup"] = None
    assert grupo_de_calculo(ler(tabelas=[t]).tabelas[0]) is False


def test_parametro_de_campo_fica_fora_de_escopo_e_o_dax_e_da_ferramenta(ler):
    """Como os dois `Toggle…` do P2: as tuplas NAMEOF são escritas pelo Desktop."""
    t = ler(tabelas=[_parametro_de_campo("Toggle", METADADO_DE_CAMPO)]).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is True


def test_parametro_hipotetico_com_metadado_sem_kind_nao_e_parametro_de_campo(ler):
    """O `Parâmetro` do P8 tem ParameterMetadata `{"version": 0}`: é parâmetro
    hipotético, já excluído pelo GENERATESERIES."""
    coluna_parametro = coluna("Parâmetro", tipo="calculatedTableColumn", tipo_dado="double")
    coluna_parametro["extendedProperties"] = [{"name": "ParameterMetadata", "type": "json", "value": {"version": 0}}]
    t = ler(
        tabelas=[
            tabela(
                "Parâmetro",
                colunas=[coluna_parametro],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")],
            )
        ]
    ).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is False
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is True


@pytest.mark.parametrize(
    "propriedades",
    [
        None,
        [],
        ["ParameterMetadata"],
        [{"name": "ParameterMetadata", "value": "kind=2"}],
        [{"name": "ParameterMetadata", "value": {"kind": 1}}],
        [{"name": "Outra", "value": {"kind": 2}}],
    ],
)
def test_extended_properties_malformadas_ou_de_outro_tipo_nao_sao_parametro_de_campo(ler, propriedades):
    t = ler(tabelas=[_parametro_de_campo("Tabela", propriedades)]).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is False


def test_tabela_comum_nao_e_grupo_nem_parametro(ler):
    t = ler(tabelas=[tabela("DimProduto", colunas=[coluna("Nome")])]).tabelas[0]
    assert grupo_de_calculo(t) is False
    assert tabela_de_parametro_de_campo(t) is False
    assert fora_de_escopo(t) is False
