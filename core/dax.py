"""Lexer de DAX.

Texto entra, tokens saem. Não conhece modelo, tabela nem regra.

**Nunca levanta exceção.** Caractere que não reconhece vira `DESCONHECIDO`, e é
a varredura (`core/rules/expressoes.py`) que decide o que fazer com isso. Essa
escolha é o terceiro teste do critério de detectabilidade em tempo de execução:
uma regra que afirma por ausência não pode alegar varredura exaustiva sobre uma
expressão que não foi tokenizada por completo.

Não constrói AST, não conhece precedência e não valida. Parser sintático é F18,
Trabalhos Futuros — e é o que mantém o grupo 3 de regras fora do MVP.
"""

from enum import StrEnum

from pydantic import BaseModel


class TipoToken(StrEnum):
    COMENTARIO = "comentario"
    STRING = "string"
    NUMERO = "numero"
    REFERENCIA = "referencia"
    IDENTIFICADOR = "identificador"
    OPERADOR = "operador"
    PARENTESE_ABRE = "parentese_abre"
    PARENTESE_FECHA = "parentese_fecha"
    VIRGULA = "virgula"
    DESCONHECIDO = "desconhecido"


class Token(BaseModel):
    tipo: TipoToken
    texto: str
    posicao: int
    tabela: str | None = None
    """Só em `REFERENCIA`, e `None` quando a referência é uma medida."""
    coluna: str | None = None
    """Só em `REFERENCIA`: o nome dentro dos colchetes."""


OPERADORES = ("<>", "<=", ">=", "||", "&&", "+", "-", "*", "/", "^", "&", "=", "<", ">")
"""Os de dois caracteres vêm primeiro: a busca é por prefixo, e `<=` precisa
ganhar de `<`."""


def tokenizar(expressao: str | None) -> list[Token]:
    """Quebra uma expressão DAX em tokens. Nunca levanta exceção."""
    texto = expressao or ""
    tokens: list[Token] = []
    i = 0

    while i < len(texto):
        c = texto[i]

        if c in " \t\r\n":
            i += 1
            continue

        if c == "/" and texto.startswith("//", i):
            fim = texto.find("\n", i)
            fim = len(texto) if fim == -1 else fim
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue

        if texto.startswith("--", i):
            fim = texto.find("\n", i)
            fim = len(texto) if fim == -1 else fim
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue

        if texto.startswith("/*", i):
            fechamento = texto.find("*/", i + 2)
            # Bloco sem fechar: consome até o fim. É DAX inválido, mas o lexer
            # não valida — e não pode ler além do fim nem repetir a posição.
            fim = len(texto) if fechamento == -1 else fechamento + 2
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue

        for simbolo in OPERADORES:
            if texto.startswith(simbolo, i):
                tokens.append(Token(tipo=TipoToken.OPERADOR, texto=simbolo, posicao=i))
                i += len(simbolo)
                break
        else:
            tokens.append(Token(tipo=TipoToken.DESCONHECIDO, texto=c, posicao=i))
            i += 1

    return tokens
