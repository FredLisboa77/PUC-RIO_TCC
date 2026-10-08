"""Testes do lexer de DAX.

O lexer existe por medição: 92 das 128 expressões de medida e coluna do P8 têm
comentário `//`. Regex sobre texto bruto casaria o comentário como divisão.
"""

from core.dax import TipoToken, tokenizar


def _tipos(expressao: str) -> list[TipoToken]:
    return [t.tipo for t in tokenizar(expressao)]


def _de(expressao: str, tipo: TipoToken) -> list[str]:
    return [t.texto for t in tokenizar(expressao) if t.tipo == tipo]


def test_divisao_e_operador():
    assert _de("[a] / [b]", TipoToken.OPERADOR) == ["/"]


def test_comentario_de_duas_barras_nao_e_divisao():
    """O sósia medido: 92 das 128 expressões do P8 têm `//`."""
    assert _de("[a] // isto / aquilo", TipoToken.OPERADOR) == []
    assert _de("[a] // isto / aquilo", TipoToken.COMENTARIO) == ["// isto / aquilo"]


def test_comentario_de_dois_tracos():
    assert _de("[a] -- nota", TipoToken.COMENTARIO) == ["-- nota"]
    assert _de("[a] -- nota", TipoToken.OPERADOR) == []


def test_comentario_em_bloco():
    assert _de("[a] /* nota / com barra */ + [b]", TipoToken.COMENTARIO) == [
        "/* nota / com barra */"
    ]
    assert _de("[a] /* nota */ + [b]", TipoToken.OPERADOR) == ["+"]


def test_comentario_de_linha_termina_na_quebra():
    """A divisão da linha seguinte precisa sobreviver ao comentário da primeira."""
    assert _de("// nota\n[a] / [b]", TipoToken.OPERADOR) == ["/"]


def test_string_com_aspas_literais():
    """`""` dentro de string é uma aspa, não o fim dela."""
    assert _de('"a""b"', TipoToken.STRING) == ['"a""b"']


def test_barra_dentro_de_string_nao_e_divisao():
    assert _de('"km/h"', TipoToken.OPERADOR) == []
    assert _de('"km/h"', TipoToken.STRING) == ['"km/h"']


def test_numero_inteiro_e_decimal():
    assert _de("1 + 2.5", TipoToken.NUMERO) == ["1", "2.5"]


def test_chamada_de_funcao():
    assert _tipos("SUM([a])") == [
        TipoToken.IDENTIFICADOR,
        TipoToken.PARENTESE_ABRE,
        TipoToken.REFERENCIA,
        TipoToken.PARENTESE_FECHA,
    ]


def test_virgula_separa_argumentos():
    assert _de("DIVIDE([a], [b])", TipoToken.VIRGULA) == [","]


def test_expressao_vazia_ou_so_comentario():
    """`Medida.expressao` tem default "" e uma medida pode ser só um comentário."""
    assert tokenizar("") == []
    assert tokenizar(None) == []
    assert tokenizar("   \n  ") == []
    assert _tipos("// só um comentário") == [TipoToken.COMENTARIO]


def test_referencia_de_coluna_qualificada():
    t = tokenizar("Vendas[Total]")[0]
    assert (t.tipo, t.tabela, t.coluna) == (TipoToken.REFERENCIA, "Vendas", "Total")


def test_referencia_de_medida_nao_tem_tabela():
    """É assim que medida se distingue de coluna sem consultar o modelo."""
    t = tokenizar("[Receita Total]")[0]
    assert (t.tipo, t.tabela, t.coluna) == (TipoToken.REFERENCIA, None, "Receita Total")


def test_tabela_com_espaco_entre_apostrofos():
    t = tokenizar("'Tabela de Regressão Linear'[Previsao]")[0]
    assert (t.tabela, t.coluna) == ("Tabela de Regressão Linear", "Previsao")


def test_apostrofo_literal_no_nome_da_tabela():
    t = tokenizar("'O''Brien'[Coluna]")[0]
    assert t.tabela == "O'Brien"


def test_barra_dentro_de_colchete_nao_e_divisao():
    """`[Receita/Custo]` é um nome, não uma divisão."""
    assert _de("[Receita/Custo]", TipoToken.OPERADOR) == []
    assert tokenizar("[Receita/Custo]")[0].coluna == "Receita/Custo"


def test_comentario_em_bloco_sem_fechar_nao_entra_em_laco():
    """DAX inválido num arquivo salvo com erro. O lexer consome até o fim."""
    tokens = tokenizar("[a] + /* sem fechar")
    assert tokens[-1].tipo is TipoToken.COMENTARIO
    assert tokens[-1].texto == "/* sem fechar"


def test_string_sem_fechar_nao_estoura_indice():
    tokens = tokenizar('[a] + "sem fechar')
    assert tokens[-1].tipo is TipoToken.STRING
    assert tokens[-1].texto == '"sem fechar'


def test_colchete_sem_fechar_vira_desconhecido():
    """Nome truncado em silêncio seria pior que lacuna declarada.

    A PERF-005 afirma por ausência: se o lexer cortasse `Tabela[Coluna` em
    `Coluna`, ela concluiria ausência de referência a partir de um nome que ela
    própria mutilou. `DESCONHECIDO` faz a expressão virar lacuna, e a regra se
    cala sobre ela.
    """
    from core.dax import tem_desconhecido

    assert tem_desconhecido(tokenizar("Vendas[Total")) is True
    assert tem_desconhecido(tokenizar("[Total")) is True
    assert tem_desconhecido(tokenizar("'Tabela[Coluna]")) is True
    assert tem_desconhecido(tokenizar("Vendas[Total]")) is False


def test_delimitador_sem_fechar_consome_o_resto_como_desconhecido():
    """Nada descartado, nada fabricado.

    O defeito que isto fixa: `'Tabela[Coluna]` produzia uma REFERENCIA a
    Tabela[Coluna] a partir de um nome citado que nunca fechou, indistinguivel
    de uma referencia legitima; e `Vendas[Total` descartava "Vendas" sem emitir
    token nenhum. A regra de coluna sem uso decide ausencia de referencia lendo
    estes tokens, e referencia fabricada ali vira recomendacao de apagar coluna
    em uso.
    """
    tokens = tokenizar("Vendas[Total")
    assert [(t.tipo, t.texto, t.posicao) for t in tokens] == [
        (TipoToken.DESCONHECIDO, "Vendas[Total", 0)
    ]

    tokens = tokenizar("'Tabela[Coluna]")
    assert [(t.tipo, t.texto, t.posicao) for t in tokens] == [
        (TipoToken.DESCONHECIDO, "'Tabela[Coluna]", 0)
    ]
    assert all(t.tabela is None and t.coluna is None for t in tokens)

    tokens = tokenizar("[Total")
    assert [(t.tipo, t.texto, t.posicao) for t in tokens] == [
        (TipoToken.DESCONHECIDO, "[Total", 0)
    ]


def test_delimitador_sem_fechar_preserva_os_tokens_validos_que_vieram_antes():
    """O defeito era só no que vem depois do delimitador quebrado."""
    tokens = tokenizar("SUM([a]) + Vendas[Total")
    tipos_e_textos = [(t.tipo, t.texto) for t in tokens]

    assert tipos_e_textos == [
        (TipoToken.IDENTIFICADOR, "SUM"),
        (TipoToken.PARENTESE_ABRE, "("),
        (TipoToken.REFERENCIA, "[a]"),
        (TipoToken.PARENTESE_FECHA, ")"),
        (TipoToken.OPERADOR, "+"),
        (TipoToken.DESCONHECIDO, "Vendas[Total"),
    ]


def test_caractere_estranho_vira_desconhecido():
    from core.dax import tem_desconhecido

    assert tem_desconhecido(tokenizar("[a] § [b]")) is True


def test_chaves_do_construtor_de_tabela():
    """`IN {"a", "b"}` é sintaxe de conjunto do DAX, não um par desconhecido."""
    from core.dax import tem_desconhecido

    expressao = '[a] IN {"No Discount", "b"}'
    assert _tipos(expressao)[-5:] == [
        TipoToken.CHAVE_ABRE,
        TipoToken.STRING,
        TipoToken.VIRGULA,
        TipoToken.STRING,
        TipoToken.CHAVE_FECHA,
    ]
    assert tem_desconhecido(tokenizar(expressao)) is False


def test_referencias_ignora_comentario_e_string():
    from core.dax import referencias

    tokens = tokenizar('Vendas[Total] // Vendas[Oculto]\n+ "Vendas[Falso]"')
    assert [(t.tabela, t.coluna) for t in referencias(tokens)] == [("Vendas", "Total")]


def test_operadores_conta_so_o_simbolo_pedido():
    from core.dax import operadores

    tokens = tokenizar("[a] / [b] + [c] / [d]")
    assert len(operadores(tokens, "/")) == 2
    assert len(operadores(tokens, "+")) == 1


def test_chamadas_separa_os_argumentos():
    from core.dax import chamadas

    args = chamadas(tokenizar("DIVIDE([a], [b])"), "DIVIDE")
    assert len(args) == 1
    assert [len(a) for a in args[0]] == [1, 1]


def test_chamadas_respeita_parenteses_aninhados():
    """A vírgula de dentro pertence ao argumento, não à chamada de fora."""
    from core.dax import chamadas

    args = chamadas(tokenizar("SUMX(Vendas, DIVIDE([a], [b]))"), "SUMX")
    assert len(args[0]) == 2
    assert args[0][0][0].texto == "Vendas"


def test_chamadas_e_insensivel_a_caixa():
    from core.dax import chamadas

    assert len(chamadas(tokenizar("divide([a],[b])"), "DIVIDE")) == 1


def test_chamadas_sem_a_funcao_devolve_vazio():
    from core.dax import chamadas

    assert chamadas(tokenizar("SUM([a])"), "FILTER") == []


def test_chamadas_sem_argumento_devolve_um_argumento_vazio():
    """`NOW()` devolve um argumento vazio, não zero argumentos.

    Comportamento deliberado e fixado aqui porque é surpreendente: uma regra
    que perguntasse `len(args) == 0` para detectar chamada sem argumento
    receberia 1 e concluiria o contrário.
    """
    from core.dax import chamadas

    args = chamadas(tokenizar("NOW()"), "NOW")

    assert len(args) == 1
    assert args == [[[]]]


def test_chamadas_com_parentese_sem_fechar_nao_fabrica_argumento():
    """Chamada que nunca fecha não é chamada: nada a afirmar sobre ela."""
    from core.dax import chamadas

    assert chamadas(tokenizar("SUM([a]"), "SUM") == []


def test_chamadas_ignora_o_nome_sem_parentese():
    """O nome existe na expressão, mas não é uma chamada."""
    from core.dax import chamadas

    assert chamadas(tokenizar("SUM + 1"), "SUM") == []
