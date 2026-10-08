"""Testes da resolução de uso de coluna.

Oito sítios. Um esquecido faz a PERF-005 recomendar apagar coluna em uso — e no
P8 há 10 `sortByColumn` e 16 níveis de hierarquia esperando por esse erro.
"""

from core.rules.referencias import usos_de_coluna
from conftest import coluna, hierarquia, medida, nivel, particao, relacionamento, role, tabela


def test_chave_de_relacionamento_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[coluna("ClienteKey", tipo_dado="int64")]),
            tabela("Cliente", colunas=[coluna("ClienteKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("Fato", "ClienteKey", "Cliente", "ClienteKey")],
    )

    usos = usos_de_coluna(modelo)

    assert "relacionamento" in usos[("Fato", "ClienteKey")]
    assert "relacionamento" in usos[("Cliente", "ClienteKey")]


def test_nivel_de_hierarquia_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Produto",
                colunas=[coluna("Categoria"), coluna("Nome")],
                hierarquias=[hierarquia("H", niveis=[nivel("Cat", "Categoria")])],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "hierarquia" in usos[("Produto", "Categoria")]
    assert usos[("Produto", "Nome")] == set()


def test_sort_by_column_e_uso_da_coluna_apontada(ler):
    """O caso que quebraria a ordenação do relatório se fosse esquecido."""
    modelo = ler(
        tabelas=[
            tabela(
                "Data",
                colunas=[
                    coluna("MesNome", ordenar_por="MesNumero"),
                    coluna("MesNumero", tipo_dado="int64"),
                ],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "ordenacao" in usos[("Data", "MesNumero")]
    assert usos[("Data", "MesNome")] == set()


def test_variations_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela("Vendas", colunas=[coluna("Data", tipo_dado="dateTime", variacao_para="LDT")]),
            tabela("LDT", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ]
    )

    assert "variacao" in usos_de_coluna(modelo)[("Vendas", "Data")]


def test_referencia_qualificada_em_medida_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double"), coluna("Sobra")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Vendas", "Valor")]
    assert usos[("Vendas", "Sobra")] == set()


def test_nome_de_coluna_em_comentario_nao_e_uso(ler):
    """O lexer já separou: comentário é COMENTARIO, não REFERENCIA."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double")],
                medidas=[medida("Total", "// usa Vendas[Valor]\n1")],
            )
        ]
    )

    assert usos_de_coluna(modelo)[("Vendas", "Valor")] == set()


def test_nome_de_coluna_em_string_nao_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double")],
                medidas=[medida("Rotulo", '"Vendas[Valor]"')],
            )
        ]
    )

    assert usos_de_coluna(modelo)[("Vendas", "Valor")] == set()


def test_referencia_em_coluna_calculada_e_em_particao(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[
                    coluna("Base", tipo_dado="double"),
                    coluna("Dobro", tipo="calculated", expressao="Vendas[Base] * 2"),
                    coluna("Semente", tipo_dado="int64"),
                ],
                particoes=[particao(tipo="calculated", expressao="ROW(\"x\", Vendas[Semente])")],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de coluna calculada" in usos[("Vendas", "Base")]
    assert "dax de particao calculada" in usos[("Vendas", "Semente")]


def test_coluna_homonima_em_outra_tabela_nao_e_marcada(ler):
    """O P8 tem três `GeographyKey`, em tabelas diferentes.

    `Cliente[GeographyKey]` numa medida não é uso de `Loja[GeographyKey]`.
    Marcar a tabela errada faria a PERF-005 julgar a coluna errada: a usada
    pareceria sem uso, e a sem uso pareceria usada.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Cliente",
                colunas=[coluna("GeoKey", tipo_dado="int64")],
                medidas=[medida("Conta", "DISTINCTCOUNT(Cliente[GeoKey])")],
            ),
            tabela("Loja", colunas=[coluna("GeoKey", tipo_dado="int64")]),
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Cliente", "GeoKey")]
    assert usos[("Loja", "GeoKey")] == set()


def test_referencia_nao_qualificada_resolve_na_tabela_da_expressao(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Cliente",
                colunas=[coluna("Idade", tipo_dado="int64")],
                medidas=[medida("Media", "AVERAGE([Idade])")],
            ),
            tabela("Loja", colunas=[coluna("Idade", tipo_dado="int64")]),
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Cliente", "Idade")]
    assert usos[("Loja", "Idade")] == set()


def test_referencia_em_filtro_de_role_e_uso(ler):
    """Condição de existência da PERF-005: sem isto, um modelo com RLS teria a
    coluna do filtro marcada como sem uso."""
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro='Vendas[Regiao] = "Sul"')],
    )

    assert "dax de role" in usos_de_coluna(modelo)[("Vendas", "Regiao")]
