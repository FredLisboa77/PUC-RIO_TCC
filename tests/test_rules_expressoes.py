"""Testes da varredura de expressões DAX."""

from core.rules.expressoes import varrer_dax
from conftest import coluna, medida, particao, role, tabela


def test_varre_medida_coluna_calculada_e_particao_calculada(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Margem", tipo="calculated", expressao="[a] - [b]")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(1,2)")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert {e.sitio for e in v.expressoes} == {
        "medida",
        "coluna calculada",
        "particao calculada",
    }
    assert v.lacunas == []


def test_nao_varre_particao_m(ler):
    """10 das 19 partições do P8 são M. `/` em caminho de arquivo não é divisão."""
    modelo = ler(
        tabelas=[
            tabela("Vendas", particoes=[particao(tipo="m", expressao='Csv.Document("c:/x")')])
        ]
    )

    assert varrer_dax(modelo).expressoes == []


def test_respeita_as_exclusoes_de_escopo(ler):
    """Tabela de data automática não entra: auditar o que o autor escreveu."""
    modelo = ler(
        tabelas=[
            tabela(
                "LocalDateTable_x",
                colunas=[coluna("Trim", tipo="calculated", expressao="INT([Mes]/3)")],
                annotations={"__PBI_LocalDateTable": "true"},
            )
        ]
    )

    assert varrer_dax(modelo).expressoes == []


def test_objeto_vem_qualificado(ler):
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Total", "1")])])

    assert varrer_dax(modelo).expressoes[0].objeto == "Vendas[Total]"


def test_expressao_com_caractere_estranho_vira_lacuna(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[medida("Boa", "SUM(Vendas[Valor])"), medida("Ruim", "[a] § [b]")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert [e.objeto for e in v.expressoes] == ["Vendas[Boa]"]
    assert [l.objeto for l in v.lacunas] == ["Vendas[Ruim]"]
    assert v.lacunas[0].motivo == "caractere não reconhecido: '§'"
    assert v.lacunas[0].posicao == 4
    assert "§" in v.lacunas[0].trecho


def test_a_expressao_com_lacuna_nao_chega_as_regras(ler):
    """A garantia estrutural: nenhuma regra vê o que o relatório diz não ter lido."""
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Ruim", "[a] § [b]")])])

    v = varrer_dax(modelo)

    assert v.expressoes == []
    assert len(v.lacunas) == 1


def test_a_soma_fecha_com_o_total_de_sitios(ler):
    """Critério de aceite 2. Lacuna que desaparece da soma é lacuna escondida."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("X", tipo="calculated", expressao="1")],
                medidas=[medida("A", "1"), medida("B", "[a] § [b]")],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(1,2)")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert v.total == 4
    assert len(v.expressoes) == 3
    assert len(v.lacunas) == 1


def test_varre_a_expressao_de_filtro_da_role(ler):
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro='Vendas[Regiao] = "Sul"')],
    )

    v = varrer_dax(modelo)

    assert [e.sitio for e in v.expressoes] == ["role"]
    assert v.expressoes[0].objeto == "Vendedor:Vendas"


def test_varre_role_mesmo_em_tabela_excluida_do_escopo_de_dax(ler):
    """O laço de role não aplica `tabelas_com_dax_do_autor`.

    Um filtro de RLS sobre uma tabela de data automática ainda é DAX escrito
    pelo autor — a exclusão de `dax_escrito_pela_ferramenta` é sobre quem
    escreveu o DAX *daquela tabela*, não sobre quem escreveu o filtro da role
    que a referencia. Sem este teste, um erro que filtrasse o laço de role
    pelo mesmo escopo das tabelas só apareceria ao auditar um PBIP real com
    RLS sobre uma tabela de data automática.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "LocalDateTable_x",
                colunas=[coluna("Date")],
                annotations={"__PBI_LocalDateTable": "true"},
            )
        ],
        roles=[role("Vendedor", tabela="LocalDateTable_x", filtro="[Date] > 0")],
    )

    v = varrer_dax(modelo)

    assert [e.sitio for e in v.expressoes] == ["role"]
    assert v.expressoes[0].tabela == "LocalDateTable_x"


def test_medida_com_expressao_vazia_ainda_e_sitio(ler):
    """`if m.expressao:` era truthiness: uma medida com `expression: ""` saía
    das duas listas, e a soma deixava de fechar com o total de sítios
    (critério de aceite 2). Expressão vazia tokeniza para lista vazia, sem
    lacuna — então ela entra como expressão, não como lacuna."""
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Vazia", "")])])

    v = varrer_dax(modelo)

    assert [e.objeto for e in v.expressoes] == ["Vendas[Vazia]"]
    assert v.lacunas == []
    assert v.total == 1
