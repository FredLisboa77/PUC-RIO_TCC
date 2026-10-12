"""Candidatos do gabarito: o universo de cada regra, com fatos neutros."""

import pytest
from conftest import coluna, medida, relacionamento, tabela

from gabarito.candidatos import COLUNAS_DE_FATOS, candidatos_do_dataset, candidatos_do_modelo
from rag.avaliacao import PASTA_PBIP, achados_dos_projetos


def _por_regra(candidatos, id_regra):
    return {c.objeto: c for c in candidatos if c.id_regra == id_regra}


def _modelo_basico(ler):
    return ler(
        tabelas=[
            tabela("Vendas", colunas=[coluna("ProdutoKey", tipo_dado="int64"), coluna("DataKey", tipo_dado="int64")]),
            tabela("Produto", colunas=[coluna("ProdutoKey", tipo_dado="int64"), coluna("CategoriaKey", tipo_dado="int64")]),
            tabela("Categoria", colunas=[coluna("CategoriaKey", tipo_dado="int64")]),
            tabela("Medidas", medidas=[medida("Total", "SUM(Vendas[ProdutoKey])")]),
            tabela(
                "LocalDateTable_1",
                colunas=[coluna("Date", tipo_dado="dateTime")],
                annotations={"__PBI_LocalDateTable": "true"},
            ),
        ],
        relacionamentos=[
            relacionamento("Vendas", "ProdutoKey", "Produto", "ProdutoKey", bidirecional=True),
            relacionamento("Produto", "CategoriaKey", "Categoria", "CategoriaKey"),
            relacionamento(
                "Produto", "ProdutoKey", "Categoria", "CategoriaKey",
                cardinalidade_origem="one", cardinalidade_destino="one", bidirecional=True,
            ),
        ],
    )


def test_id_junta_regra_projeto_e_objeto(ler):
    c = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-003")["Produto"]
    assert c.id == "MOD-003|P1|Produto"


def test_mod001_lista_todas_as_tabelas_inclusive_a_automatica(ler):
    mod001 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-001")
    assert set(mod001) == {"Vendas", "Produto", "Categoria", "Medidas", "LocalDateTable_1"}
    assert mod001["LocalDateTable_1"].fatos["anotacoes"] == "__PBI_LocalDateTable"


def test_tabela_automatica_so_e_candidata_da_mod001(ler):
    candidatos = candidatos_do_modelo("P1", _modelo_basico(ler))
    regras = {c.id_regra for c in candidatos if c.objeto == "LocalDateTable_1"}
    assert regras == {"MOD-001"}


def test_mod003_mostra_contagens_sem_julgar(ler):
    mod003 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-003")
    assert set(mod003) == {"Vendas", "Produto", "Categoria", "Medidas"}
    assert mod003["Medidas"].fatos == {"relacionamentos": "0", "medidas": "1", "colunas": "0", "oculta": "não"}
    assert mod003["Produto"].fatos["relacionamentos"] == "3"


def test_mod002_exclui_um_para_um_e_mod007_lista_todos(ler):
    candidatos = candidatos_do_modelo("P1", _modelo_basico(ler))
    mod002 = _por_regra(candidatos, "MOD-002")
    mod007 = _por_regra(candidatos, "MOD-007")
    assert set(mod002) == {"Vendas[ProdutoKey] → Produto[ProdutoKey]", "Produto[CategoriaKey] → Categoria[CategoriaKey]"}
    assert len(mod007) == 3
    um_para_um = mod007["Produto[ProdutoKey] → Categoria[CategoriaKey]"]
    assert um_para_um.fatos["cardinalidades"] == "um:um"
    assert mod002["Vendas[ProdutoKey] → Produto[ProdutoKey]"].fatos["direcao"] == "ambos_sentidos"


def test_mod006_mostra_quem_filtra_e_quem_e_filtrado(ler):
    mod006 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-006")
    produto = mod006["Produto"].fatos
    # Vendas → Produto (muitos:um): Produto filtra Vendas. Produto → Categoria
    # (muitos:um): Categoria filtra Produto. O um-para-um não tem lado "muitos".
    assert produto["filtra"] == "Vendas"
    assert produto["filtrada_por"] == "Categoria"


def test_todo_candidato_tem_exatamente_as_colunas_de_fatos_da_regra(ler):
    for c in candidatos_do_modelo("P1", _modelo_basico(ler)):
        assert tuple(c.fatos) == COLUNAS_DE_FATOS[c.id_regra], c.id


def test_mod005_lista_tabelas_com_coluna_de_data_e_a_variations(ler):
    modelo = ler(
        tabelas=[
            tabela("Calendario", colunas=[coluna("Data", tipo_dado="dateTime", variacao_para="LocalDateTable_9")]),
            tabela("Pedidos", colunas=[coluna("Emissao", tipo_dado="dateTime"), coluna("Valor", tipo_dado="double")]),
            tabela("Produto", colunas=[coluna("Nome")]),
        ]
    )
    mod005 = _por_regra(candidatos_do_modelo("P1", modelo), "MOD-005")
    assert set(mod005) == {"Calendario", "Pedidos"}
    assert mod005["Calendario"].fatos["colunas_de_data"] == "Data -> LocalDateTable_9"
    assert mod005["Pedidos"].fatos["colunas_de_data"] == "Emissao"


def test_perf001_lista_colunas_calculadas_com_a_expressao(ler):
    modelo = ler(
        tabelas=[
            tabela("Pessoa", colunas=[
                coluna("Salário", tipo="calculated", expressao="Pessoa[Base] * 1.1", tipo_dado="double"),
                coluna("Base", tipo_dado="double"),
            ])
        ]
    )
    perf001 = _por_regra(candidatos_do_modelo("P1", modelo), "PERF-001")
    assert set(perf001) == {"Pessoa[Salário]"}
    assert perf001["Pessoa[Salário]"].fatos["expressao"] == "Pessoa[Base] * 1.1"


def test_perf003_lista_toda_coluna_double_somada_ou_nao(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[
                coluna("Valor", tipo_dado="double", resumir_por="sum"),
                coluna("Taxa", tipo_dado="double"),
                coluna("Qtd", tipo_dado="int64", resumir_por="sum"),
            ])
        ]
    )
    perf003 = _por_regra(candidatos_do_modelo("P1", modelo), "PERF-003")
    assert set(perf003) == {"Fato[Valor]", "Fato[Taxa]"}
    assert perf003["Fato[Taxa]"].fatos == {"tipo_dado": "double", "resumir_por": "none"}


def test_dax001_lista_expressoes_com_barra_e_o_que_vem_depois_de_cada_uma(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[coluna("Valor", tipo_dado="double")], medidas=[
                medida("Margem", "SUM(Fato[Valor]) / [Receita]"),
                medida("Metade", "SUM(Fato[Valor]) / 2"),
                medida("Total", "SUM(Fato[Valor])"),
            ])
        ]
    )
    dax001 = _por_regra(candidatos_do_modelo("P1", modelo), "DAX-001")
    assert set(dax001) == {"Fato[Margem]", "Fato[Metade]"}
    assert dax001["Fato[Margem]"].fatos["sitio"] == "medida"
    assert dax001["Fato[Margem]"].fatos["divisoes"] == "/ [Receita]"
    assert dax001["Fato[Metade]"].fatos["divisoes"] == "/ 2"


def test_expressao_longa_e_cortada(ler):
    longa = "SUM(Fato[Valor]) / [Receita] + " + "1 + " * 600 + "1"
    modelo = ler(tabelas=[tabela("Fato", colunas=[coluna("Valor", tipo_dado="double")], medidas=[medida("Longa", longa)])])
    fatos = _por_regra(candidatos_do_modelo("P1", modelo), "DAX-001")["Fato[Longa]"].fatos
    assert len(fatos["expressao"]) == 1500 + len(" […]")
    assert fatos["expressao"].endswith(" […]")


SEM_DADOS = not (PASTA_PBIP / "P1_AdventureWorks Sales").is_dir()


@pytest.mark.skipif(SEM_DADOS, reason="data/ não é versionado")
def test_todo_achado_real_de_p1_a_p7_casa_com_um_candidato():
    ids = {c.id for c in candidatos_do_dataset()}
    faltando = [
        f"{a.id_regra}|{projeto}|{a.evidencia.objeto}"
        for projeto, achados in achados_dos_projetos(PASTA_PBIP).items()
        for a in achados
        if f"{a.id_regra}|{projeto}|{a.evidencia.objeto}" not in ids
    ]
    assert faltando == []


def test_relacionamento_com_tabela_automatica_nao_entra_nas_outras_regras(ler):
    modelo = ler(
        tabelas=[
            tabela("Vendas", colunas=[coluna("ProdutoKey", tipo_dado="int64"), coluna("Data", tipo_dado="dateTime")]),
            tabela("Produto", colunas=[coluna("ProdutoKey", tipo_dado="int64")]),
            tabela(
                "LocalDateTable_1",
                colunas=[coluna("Date", tipo_dado="dateTime")],
                annotations={"__PBI_LocalDateTable": "true"},
            ),
        ],
        relacionamentos=[
            relacionamento("Vendas", "ProdutoKey", "Produto", "ProdutoKey"),
            relacionamento("Vendas", "Data", "LocalDateTable_1", "Date"),
        ],
    )
    candidatos = candidatos_do_modelo("P1", modelo)
    assert [c for c in candidatos if "LocalDateTable_1" in c.objeto and c.id_regra != "MOD-001"] == []
    assert _por_regra(candidatos, "MOD-006")["Vendas"].fatos["filtrada_por"] == "Produto"
    assert _por_regra(candidatos, "MOD-003")["Vendas"].fatos["relacionamentos"] == "1"
