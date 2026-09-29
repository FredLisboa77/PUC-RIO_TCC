import json

from conftest import escrever_pbip
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
