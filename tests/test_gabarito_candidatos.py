"""Candidatos do gabarito: o universo de cada regra, com fatos neutros."""

from conftest import coluna, medida, relacionamento, tabela

from gabarito.candidatos import COLUNAS_DE_FATOS, candidatos_do_modelo


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
