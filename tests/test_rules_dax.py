"""Testes das regras de DAX por padrão textual."""

from core.rules.dax import divisao_sem_divide
from conftest import coluna, medida, particao, role, tabela


def test_dax001_marca_divisao_com_operador(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("A", tipo_dado="double"), coluna("B", tipo_dado="double")],
                medidas=[medida("Razao", "SUM(Vendas[A]) / SUM(Vendas[B])")],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert [a.evidencia.objeto for a in achados] == ["Vendas[Razao]"]
    assert achados[0].id_regra == "DAX-001"
    assert achados[0].evidencia.detalhe["ocorrencias"] == 1
    assert achados[0].evidencia.trecho is not None


def test_dax001_nao_marca_quem_usa_divide(ler):
    modelo = ler(
        tabelas=[
            tabela("Vendas", medidas=[medida("Razao", "DIVIDE([A], [B])")]),
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_um_achado_por_expressao_nao_por_barra(ler):
    """Um achado por ocorrência, e a ocorrência é a expressão: é nela que o
    autor corrige. O número de barras marcadas vai no detalhe.

    As duas divisões aqui têm denominador variável, então as duas contam."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("Duas", "[a]/[b] + [c]/[d]")])]
    )

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.detalhe["ocorrencias"] == 2


def test_dax001_ignora_barra_em_comentario(ler):
    """O sósia que torna a regex inviável: 92 das 128 expressões do P8 têm `//`."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("A", "// taxa a/b\nDIVIDE([a],[b])")])]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_barra_em_string(ler):
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Unidade", '"km/h"')])])

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_barra_em_nome_de_coluna(ler):
    """`[Receita/Custo]` é um nome, não uma divisão."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Receita/Custo", tipo_dado="double")],
                medidas=[medida("Total", "SUM(Vendas[Receita/Custo])")],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_particao_m(ler):
    """`/` em caminho de arquivo do Power Query não é divisão em DAX."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                particoes=[particao(tipo="m", expressao='Csv.Document(File.Contents("c:/d/x.csv"))')],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_nao_marca_denominador_constante(ler):
    """A documentação **recomenda** o operador quando o denominador é constante.

    "In the case that the denominator is a constant value, we recommend that you
    use the divide operator." Marcar isto seria apontar como defeito o que a
    fonte recomenda — o erro que derrubou a PERF-004 em 06/10.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Mes", tipo_dado="int64")],
                medidas=[
                    medida("Trimestre", "INT(Vendas[Mes] / 3)"),
                    medida("Percentual", "[Taxa] / 100"),
                    medida("Constante entre parenteses", "[Taxa] / (2 * 3)"),
                ],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_marca_denominador_que_e_expressao(ler):
    """O caso que a página manda trocar: denominador que pode dar zero ou BLANK."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[
                    medida("Razao de medidas", "[Lucro] / [Receita]"),
                    medida("Razao com funcao", "[Lucro] / SUM(Vendas[Receita])"),
                    medida("Razao em grupo", "[Lucro] / ([Receita] + 1)"),
                ],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert sorted(a.evidencia.objeto for a in achados) == [
        "Vendas[Razao com funcao]",
        "Vendas[Razao de medidas]",
        "Vendas[Razao em grupo]",
    ]


def test_dax001_conta_so_as_barras_que_marca(ler):
    """Uma expressão com as duas formas: só a de denominador variável conta."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("Mista", "[a]/100 + [b]/[c]")])]
    )

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.detalhe["ocorrencias"] == 1


def test_dax001_marca_denominador_variavel_com_sinal_unario(ler):
    """`[a] / -[b]` tem denominador variável, e o sinal não muda isso.

    O lexer emite o `-` unário como OPERADOR comum, igual ao binário. Sem
    pular o sinal, o operando mínimo seria o próprio `-`, que não contém
    referência nem identificador — e a regra concluiria "constante" e se
    calaria exatamente no caso que a fonte manda trocar por DIVIDE.

    `- -[b]` (sinal duplo, DAX válido) cobre o laço: um único `if` pularia só
    um sinal e devolveria o segundo `-` como operando, repetindo o mesmo erro.
    Precisa do espaço entre os sinais: `--` colado é comentário de linha para
    este lexer (ver `core/dax.py`), não dois operadores unários.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[
                    medida("Sinal simples", "[a] / -[b]"),
                    medida("Sinal em funcao", "[a] / -SUM(Vendas[b])"),
                    medida("Sinal duplo", "[a] / - -[b]"),
                ],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert sorted(a.evidencia.objeto for a in achados) == [
        "Vendas[Sinal duplo]",
        "Vendas[Sinal em funcao]",
        "Vendas[Sinal simples]",
    ]


def test_dax001_nao_marca_denominador_constante_com_sinal_unario(ler):
    """`[a] / -3` continua constante: a documentação recomenda o operador."""
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Razao", "[a] / -3")])])

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_barra_sem_denominador_e_tratada_como_variavel(ler):
    """Expressão malformada, barra sem nada depois: `_denominador` devolve `[]`.

    `_e_constante` trata o vazio como NÃO constante de propósito — por isso a
    regra marca em vez de calar diante do que não conseguiu interpretar. Isto
    pina esse comportamento: se `_e_constante` fosse simplificada um dia para
    um `not any(...)` ingênuo, `[]` passaria a ser vacuamente constante e a
    regra cegaria em silêncio, sem que nenhum outro teste quebrasse.
    """
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Pendurada", "[a] /")])])

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.detalhe["ocorrencias"] == 1


def test_dax001_pula_comentario_entre_a_barra_e_o_denominador(ler):
    """Comentário não é o denominador: pular `//` e `/* */` para achar o real.

    Medido: `[Total] / // o denominador\\n[Qtd]` e `[Total] / /* nota */ [Qtd]`
    tinham `_denominador` devolvendo o próprio token COMENTARIO, que
    `_e_constante` lia como "sem referência nem identificador" — logo
    constante — e a regra se calava. 92 das 128 expressões do P8 têm `//`,
    então um comentário logo depois da barra, em DAX formatado em várias
    linhas, é plausível. O erro era silêncio não declarado: a regra marca por
    presença, e esta é a forma de "/" que ela deixava passar sem dizer.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[
                    medida("Barra", "[Total] / // o denominador\n[Qtd]"),
                    medida("Bloco", "[Total] / /* nota */ [Qtd]"),
                ],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert sorted(a.evidencia.objeto for a in achados) == [
        "Vendas[Barra]",
        "Vendas[Bloco]",
    ]


def test_dax001_marca_divisao_em_role(ler):
    """O sítio `role` mapeia para `tipo_objeto='modelo'` — `TipoObjeto` não tem
    um valor dedicado a RLS. Sem este teste, um erro na chave `"role"` de
    `TIPO_DE_OBJETO` só apareceria ao auditar um PBIP real com segurança de
    linha definida.
    """
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao"), coluna("Meta")])],
        roles=[role("Gerente", tabela="Vendas", filtro="[Regiao] / [Meta] > 1")],
    )

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.objeto == "Gerente:Vendas"
    assert achados[0].evidencia.tipo_objeto == "modelo"
