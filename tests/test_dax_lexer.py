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
