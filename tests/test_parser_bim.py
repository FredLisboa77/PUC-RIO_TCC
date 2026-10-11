import json

from conftest import coluna, escrever_pbip, hierarquia, nivel, role, tabela
from core.parser_bim import ler_modelo


def modelo_com(tmp_path, model: dict):
    """Escreve um PBIP cujo model.bim tem o `model` indicado e devolve o caminho."""
    projeto = escrever_pbip(
        tmp_path,
        model_bim={"name": "SemanticModel", "compatibilityLevel": 1600, "model": model},
    )
    return projeto / "Minimal.SemanticModel" / "model.bim"


def test_le_tabelas_colunas_e_medidas(tmp_path):
    caminho = modelo_com(
        tmp_path,
        {
            "culture": "pt-BR",
            "tables": [
                {
                    "name": "Vendas",
                    "columns": [
                        {"name": "Valor", "dataType": "double"},
                        {"name": "Data", "dataType": "dateTime"},
                    ],
                    "measures": [
                        {"name": "Total", "expression": "SUM(Vendas[Valor])"}
                    ],
                }
            ],
        },
    )

    modelo = ler_modelo(caminho)

    assert modelo.cultura == "pt-BR"
    assert modelo.compatibility_level == 1600
    assert [t.nome for t in modelo.tabelas] == ["Vendas"]

    vendas = modelo.tabelas[0]
    assert [c.nome for c in vendas.colunas] == ["Valor", "Data"]
    assert [m.nome for m in vendas.medidas] == ["Total"]
    assert vendas.medidas[0].expressao == "SUM(Vendas[Valor])"


def test_junta_expressao_dax_escrita_como_lista_de_linhas(tmp_path):
    """O TMSL grava DAX ora como string, ora como lista de linhas (ADR-001)."""
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [
                {
                    "name": "Vendas",
                    "measures": [
                        {
                            "name": "Margem",
                            "expression": [
                                "DIVIDE(",
                                "    [Lucro],",
                                "    [Receita]",
                                ")",
                            ],
                        }
                    ],
                }
            ]
        },
    )

    modelo = ler_modelo(caminho)

    assert modelo.tabelas[0].medidas[0].expressao == (
        "DIVIDE(\n    [Lucro],\n    [Receita]\n)"
    )


def test_le_relacionamentos_com_direcao_e_estado(tmp_path):
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [{"name": "Vendas"}, {"name": "DimCalendar"}],
            "relationships": [
                {
                    "name": "r1",
                    "fromTable": "Vendas",
                    "fromColumn": "DataId",
                    "toTable": "DimCalendar",
                    "toColumn": "DataId",
                },
                {
                    "name": "r2",
                    "fromTable": "Vendas",
                    "fromColumn": "DataEnvioId",
                    "toTable": "DimCalendar",
                    "toColumn": "DataId",
                    "crossFilteringBehavior": "bothDirections",
                    "isActive": False,
                },
            ],
        },
    )

    modelo = ler_modelo(caminho)

    r1, r2 = modelo.relacionamentos
    assert (r1.tabela_origem, r1.coluna_origem) == ("Vendas", "DataId")
    assert r1.direcao_filtro == "um_sentido"
    assert r1.ativo is True

    assert r2.direcao_filtro == "ambos_sentidos"
    assert r2.ativo is False


def test_distingue_coluna_calculada_de_coluna_comum(tmp_path):
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [
                {
                    "name": "Vendas",
                    "columns": [
                        {"name": "Valor", "dataType": "double"},
                        {
                            "name": "Ano",
                            "dataType": "int64",
                            "type": "calculated",
                            "expression": "YEAR(Vendas[Data])",
                        },
                    ],
                }
            ]
        },
    )

    vendas = ler_modelo(caminho).tabelas[0]

    assert [c.nome for c in vendas.colunas_calculadas] == ["Ano"]
    assert vendas.colunas[0].e_calculada is False


def test_le_a_expressao_m_da_particao(tmp_path):
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [
                {
                    "name": "Vendas",
                    "partitions": [
                        {
                            "name": "Vendas-part",
                            "mode": "import",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    '    Fonte = Sql.Database("servidor", "DW")',
                                    "in",
                                    "    Fonte",
                                ],
                            },
                        }
                    ],
                }
            ]
        },
    )

    particao = ler_modelo(caminho).tabelas[0].particoes[0]

    assert particao.modo == "import"
    assert particao.origem.startswith("let\n")
    assert "Sql.Database" in particao.origem


def test_tolera_propriedades_desconhecidas_e_secoes_ausentes(tmp_path):
    caminho = modelo_com(
        tmp_path,
        {
            "propriedadeQueAindaNaoExiste": {"algo": 1},
            "tables": [
                {
                    "name": "Vendas",
                    "lineageTag": "abc-123",
                    "columns": [{"name": "Valor", "sourceColumn": "Valor", "naoConhecida": True}],
                }
            ],
        },
    )

    modelo = ler_modelo(caminho)

    assert modelo.tabelas[0].colunas[0].nome == "Valor"
    assert modelo.relacionamentos == []
    # A propriedade desconhecida continua acessível para as regras.
    assert modelo.tabelas[0].colunas[0].bruto["naoConhecida"] is True


def test_le_as_propriedades_que_as_regras_precisam(tmp_path):
    """`type`, `summarizeBy`, `dataCategory` e `source.type` viram campos próprios."""
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [
                {
                    "name": "DimCalendar",
                    "dataCategory": "Time",
                    "columns": [
                        {"name": "Data", "dataType": "dateTime", "summarizeBy": "none"},
                        {
                            "name": "Ano",
                            "dataType": "string",
                            "type": "calculated",
                            "summarizeBy": "none",
                            "expression": "YEAR([Data])",
                        },
                        {"name": "Valor", "dataType": "double", "summarizeBy": "sum"},
                    ],
                    "partitions": [
                        {
                            "name": "p",
                            "mode": "import",
                            "source": {"type": "calculated", "expression": "CALENDAR(1, 2)"},
                        }
                    ],
                }
            ],
            "relationships": [],
        },
    )

    modelo = ler_modelo(caminho)
    tabela = modelo.tabelas[0]
    data, ano, valor = tabela.colunas

    assert tabela.data_category == "Time"
    assert data.tipo is None
    assert ano.tipo == "calculated"
    assert valor.resumir_por == "sum"
    assert data.resumir_por == "none"
    assert tabela.particoes[0].tipo_origem == "calculated"


def test_normaliza_a_cardinalidade_do_relacionamento(tmp_path):
    """O TMSL grava `one`/`many`; o padrão ausente é muitos-para-um.

    O P8 tem um relacionamento com `fromCardinality: "one"` explícito, que é
    um-para-um. Presumir muitos-para-um faria MOD-006 e MOD-007 errarem.
    """
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [],
            "relationships": [
                {"name": "padrao", "fromTable": "F", "fromColumn": "k", "toTable": "D", "toColumn": "k"},
                {
                    "name": "um-para-um",
                    "fromTable": "A",
                    "fromColumn": "k",
                    "toTable": "B",
                    "toColumn": "k",
                    "fromCardinality": "one",
                },
                {
                    "name": "explicito",
                    "fromTable": "F2",
                    "fromColumn": "k",
                    "toTable": "D2",
                    "toColumn": "k",
                    "fromCardinality": "many",
                    "toCardinality": "one",
                },
            ],
        },
    )

    padrao, um_para_um, explicito = ler_modelo(caminho).relacionamentos

    assert (padrao.cardinalidade_origem, padrao.cardinalidade_destino) == ("muitos", "um")
    assert (um_para_um.cardinalidade_origem, um_para_um.cardinalidade_destino) == ("um", "um")
    assert (explicito.cardinalidade_origem, explicito.cardinalidade_destino) == ("muitos", "um")


def test_le_sort_by_column(ler):
    """10 colunas do P8 ordenam por outra coluna. Esquecer isso faria a
    PERF-005 recomendar apagar a coluna de ordenação."""
    modelo = ler(
        tabelas=[
            tabela(
                "DimDate",
                colunas=[
                    coluna("MesNome", ordenar_por="MesNumero"),
                    coluna("MesNumero", tipo_dado="int64"),
                ],
            )
        ]
    )

    assert modelo.tabelas[0].colunas[0].ordenar_por == "MesNumero"
    assert modelo.tabelas[0].colunas[1].ordenar_por is None


def test_le_hierarquias_e_seus_niveis(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimProduct",
                colunas=[coluna("Categoria"), coluna("Produto")],
                hierarquias=[
                    hierarquia(
                        "Produtos",
                        niveis=[nivel("Categoria", "Categoria"), nivel("Produto", "Produto")],
                    )
                ],
            )
        ]
    )

    h = modelo.tabelas[0].hierarquias[0]
    assert h.nome == "Produtos"
    assert h.tabela == "DimProduct"
    assert [n.coluna for n in h.niveis] == ["Categoria", "Produto"]
    assert h.niveis[0].tabela == "DimProduct"


def test_le_roles_com_expressao_de_filtro(ler):
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro="[Regiao] = \"Sul\"")],
    )

    assert modelo.roles[0].nome == "Vendedor"
    assert modelo.roles[0].permissoes[0].tabela == "Vendas"
    assert modelo.roles[0].permissoes[0].expressao_filtro == '[Regiao] = "Sul"'


def test_modelo_sem_roles_tem_lista_vazia(ler):
    """O P8 não tem a chave `roles`. Ausência não pode virar None."""
    modelo = ler(tabelas=[tabela("Vendas")])
    assert modelo.roles == []


def test_le_a_ordem_do_nivel_de_hierarquia(ler):
    """A chave é `ordinal`. Propriedade lida e nunca exercitada é como a
    MOD-005 errou: ninguém percebe que o nome está errado."""
    modelo = ler(
        tabelas=[
            tabela(
                "DimProduct",
                colunas=[coluna("Categoria"), coluna("Produto")],
                hierarquias=[
                    hierarquia(
                        "Produtos",
                        niveis=[
                            nivel("Categoria", "Categoria", ordem=0),
                            nivel("Produto", "Produto"),
                        ],
                    )
                ],
            )
        ]
    )

    niveis = modelo.tabelas[0].hierarquias[0].niveis
    assert niveis[0].ordem == 0
    assert niveis[1].ordem is None


def test_nulo_explicito_no_tmsl_nao_derruba_o_parser(tmp_path):
    """`"annotations": null` derrubou as oito regras de uma vez em 06/10/2026.

    `.get(chave, [])` devolve o padrao so quando a chave esta AUSENTE. Com a
    chave presente e valor nulo devolve None, e a compreensao de lista estoura.
    Toda lista lida do TMSL usa `or []` por isso — e todo escalar que alimenta
    um campo obrigatorio do Pydantic usa `or ""`, pelo mesmo motivo: `"model":
    null` e `"name": null` numa tabela sao a mesma classe de defeito, só que
    um derruba com `AttributeError` antes de chegar ao Pydantic, e o outro com
    `ValidationError` dentro dele.
    """
    bruto = {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": None,
    }
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    modelo = ler_modelo(caminho)

    assert modelo.tabelas == []
    assert modelo.relacionamentos == []
    assert modelo.roles == []


def test_nulo_explicito_dentro_do_model_nao_derruba_o_parser(tmp_path):
    """As listas de dentro de `model` continuam tolerando `null`, isoladas do teste acima."""
    bruto = {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "pt-BR",
            "tables": None,
            "relationships": None,
            "roles": None,
        },
    }
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    modelo = ler_modelo(caminho)

    assert modelo.tabelas == []
    assert modelo.relacionamentos == []
    assert modelo.roles == []


def test_json_de_topo_nao_objeto_nao_derruba_o_parser_com_traceback_cru(tmp_path):
    """Uma lista ou string no nível superior do JSON levanta erro claro, não
    `AttributeError: 'list' object has no attribute 'get'`."""
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    try:
        ler_modelo(caminho)
        assert False, "deveria ter levantado ValueError"
    except ValueError as erro:
        assert "não é um objeto" in str(erro)


def test_nulo_explicito_em_escalar_obrigatorio_nao_derruba_o_parser(tmp_path):
    """`"name": null` numa tabela, numa coluna e num nível de hierarquia: o
    mesmo defeito do teste acima, agora num escalar que alimenta um campo
    Pydantic não opcional em vez de uma lista.
    """
    bruto = {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "pt-BR",
            "tables": [
                {
                    "name": None,
                    "columns": [{"name": None, "dataType": "string"}],
                    "hierarchies": [
                        {"name": "H", "levels": [{"name": "N", "column": None}]}
                    ],
                }
            ],
            "roles": [
                {
                    "name": "Vendedor",
                    "tablePermissions": [{"name": None, "filterExpression": "TRUE()"}],
                }
            ],
        },
    }
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    modelo = ler_modelo(caminho)

    assert modelo.tabelas[0].nome == ""
    assert modelo.tabelas[0].colunas[0].nome == ""
    assert modelo.tabelas[0].hierarquias[0].niveis[0].coluna == ""
    assert modelo.roles[0].permissoes[0].tabela == ""


def test_nulo_explicito_dentro_da_tabela_nao_derruba_o_parser(tmp_path):
    bruto = {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "pt-BR",
            "tables": [
                {
                    "name": "Vendas",
                    "columns": None,
                    "measures": None,
                    "partitions": None,
                    "hierarchies": None,
                    "annotations": None,
                }
            ],
        },
    }
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    t = ler_modelo(caminho).tabelas[0]

    assert (t.colunas, t.medidas, t.particoes, t.hierarquias) == ([], [], [], [])
