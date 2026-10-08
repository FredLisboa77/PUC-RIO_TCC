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
