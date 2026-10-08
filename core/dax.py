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
    CHAVE_ABRE = "chave_abre"
    CHAVE_FECHA = "chave_fecha"
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

        if c == '"':
            j = i + 1
            while j < len(texto):
                if texto[j] == '"':
                    if texto.startswith('""', j):   # aspa literal
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            else:
                # String sem fechar: consome até o fim, sem estourar o índice.
                j = len(texto)
            tokens.append(Token(tipo=TipoToken.STRING, texto=texto[i:j], posicao=i))
            i = j
            continue

        if c.isdigit():
            j = i
            while j < len(texto) and (texto[j].isdigit() or texto[j] == "."):
                j += 1
            tokens.append(Token(tipo=TipoToken.NUMERO, texto=texto[i:j], posicao=i))
            i = j
            continue

        if c == "(":
            tokens.append(Token(tipo=TipoToken.PARENTESE_ABRE, texto=c, posicao=i))
            i += 1
            continue

        if c == ")":
            tokens.append(Token(tipo=TipoToken.PARENTESE_FECHA, texto=c, posicao=i))
            i += 1
            continue

        if c == "{":
            # Construtor de tabela do DAX: `x IN {"a", "b"}`. Sem distinguir de
            # parêntese porque a sintaxe de conjunto não aninha outro par.
            tokens.append(Token(tipo=TipoToken.CHAVE_ABRE, texto=c, posicao=i))
            i += 1
            continue

        if c == "}":
            tokens.append(Token(tipo=TipoToken.CHAVE_FECHA, texto=c, posicao=i))
            i += 1
            continue

        if c == ",":
            tokens.append(Token(tipo=TipoToken.VIRGULA, texto=c, posicao=i))
            i += 1
            continue

        if c == "[" or c == "'" or c.isalpha() or c == "_":
            token, i = _referencia_ou_identificador(texto, i)
            tokens.append(token)
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


def _nome_entre(texto: str, i: int, abre: str, fecha: str) -> tuple[str | None, int]:
    """Lê `[nome]` ou `'nome'`, tratando o fechamento duplicado como literal.

    Devolve `(None, i)` quando o delimitador não fecha — o chamador transforma
    isso em `DESCONHECIDO`, e portanto em lacuna declarada. Nome truncado em
    silêncio seria pior: a PERF-005 concluiria ausência de referência a partir
    de um nome que ela própria cortou.
    """
    j = i + 1
    partes: list[str] = []
    while j < len(texto):
        if texto[j] == fecha:
            if texto.startswith(fecha * 2, j):
                partes.append(fecha)
                j += 2
                continue
            return "".join(partes), j + 1
        partes.append(texto[j])
        j += 1
    return None, i


def _resto_desconhecido(texto: str, inicio: int) -> tuple[Token, int]:
    """Delimitador (`[`, `'`) que nunca fechou: o resto da expressão não é confiável.

    Consome até o fim da expressão, não só o caractere do delimitador. Devolver
    só ele descartaria em silêncio o nome já lido antes (`"Vendas"` cairia do
    chão em `Vendas[Total`), e retomar a varredura depois dele poderia
    fabricar uma `REFERENCIA` de aparência legítima a partir do que sobrou
    (`Coluna]` de `'Tabela[Coluna]`, indistinguível de uma referência real para
    quem só olha esse token). Nenhuma das duas opções serve a uma regra que
    decide ausência de referência lendo estes tokens.
    """
    return Token(tipo=TipoToken.DESCONHECIDO, texto=texto[inicio:], posicao=inicio), len(texto)


def _referencia_ou_identificador(texto: str, i: int) -> tuple[Token, int]:
    """`[Medida]`, `Tabela[Coluna]`, `'Com espaço'[Coluna]` ou nome de função."""
    inicio = i

    if texto[i] == "[":
        coluna, fim = _nome_entre(texto, i, "[", "]")
        if coluna is None:
            return _resto_desconhecido(texto, inicio)
        return (
            Token(
                tipo=TipoToken.REFERENCIA,
                texto=texto[inicio:fim],
                posicao=inicio,
                tabela=None,
                coluna=coluna,
            ),
            fim,
        )

    if texto[i] == "'":
        tabela, fim = _nome_entre(texto, i, "'", "'")
        if tabela is None:
            return _resto_desconhecido(texto, inicio)
    else:
        fim = i
        while fim < len(texto) and (texto[fim].isalnum() or texto[fim] == "_"):
            fim += 1
        tabela = texto[i:fim]

    if fim < len(texto) and texto[fim] == "[":
        coluna, depois = _nome_entre(texto, fim, "[", "]")
        if coluna is None:
            return _resto_desconhecido(texto, inicio)
        return (
            Token(
                tipo=TipoToken.REFERENCIA,
                texto=texto[inicio:depois],
                posicao=inicio,
                tabela=tabela,
                coluna=coluna,
            ),
            depois,
        )

    # Nome nu: função (`SUM`) ou tabela como argumento (`FILTER(Vendas, …)`).
    return (
        Token(tipo=TipoToken.IDENTIFICADOR, texto=texto[inicio:fim], posicao=inicio),
        fim,
    )


def tem_desconhecido(tokens: list[Token]) -> bool:
    """A expressão não foi tokenizada por completo."""
    return any(t.tipo is TipoToken.DESCONHECIDO for t in tokens)


def referencias(tokens: list[Token]) -> list[Token]:
    """Só as referências. Comentário e string já são outros tipos de token."""
    return [t for t in tokens if t.tipo is TipoToken.REFERENCIA]


def operadores(tokens: list[Token], simbolo: str) -> list[Token]:
    return [t for t in tokens if t.tipo is TipoToken.OPERADOR and t.texto == simbolo]


def chamadas(tokens: list[Token], nome: str) -> list[list[list[Token]]]:
    """Para cada chamada de `nome`, a lista dos seus argumentos.

    A fronteira de argumento sai da profundidade de parêntese: uma vírgula só
    separa argumentos desta chamada quando a profundidade é 1. É o que uma
    expressão regular não consegue fazer, e o motivo de a DAX-002 depender do
    lexer.

    Uma chamada sem argumento devolve **um argumento vazio**, não zero
    argumentos: `NOW()` devolve `[[[]]]`. A contagem de argumentos, portanto,
    nunca é zero numa chamada que existe, e uma regra que precise distinguir
    "sem argumento" tem de olhar se o único argumento está vazio.
    """
    alvo = nome.upper()
    resultado: list[list[list[Token]]] = []

    for i, t in enumerate(tokens):
        if t.tipo is not TipoToken.IDENTIFICADOR or t.texto.upper() != alvo:
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].tipo is not TipoToken.PARENTESE_ABRE:
            continue

        argumentos: list[list[Token]] = []
        atual: list[Token] = []
        profundidade = 0

        for u in tokens[i + 1 :]:
            if u.tipo is TipoToken.PARENTESE_ABRE:
                profundidade += 1
                if profundidade == 1:
                    continue
            elif u.tipo is TipoToken.PARENTESE_FECHA:
                profundidade -= 1
                if profundidade == 0:
                    argumentos.append(atual)
                    break
            elif u.tipo is TipoToken.VIRGULA and profundidade == 1:
                argumentos.append(atual)
                atual = []
                continue
            atual.append(u)
        else:
            # Parêntese sem fechar. Não inventa argumento: a expressão terá
            # token DESCONHECIDO ou virará lacuna por outro caminho.
            continue

        resultado.append(argumentos)

    return resultado
