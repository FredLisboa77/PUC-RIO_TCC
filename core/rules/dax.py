"""Regras de DAX por padrão textual — o grupo 2 do critério de detectabilidade.

Toda regra aqui lê tokens, nunca a string crua. O motivo é medido: 92 das 128
expressões de medida e coluna do P8 têm comentário `//`, e uma expressão regular
procurando `/` casaria o comentário em todas elas.

As expressões vêm de `core.rules.expressoes.varrer_dax`, que entrega apenas o
que o lexer leu por completo. O que ele não leu é lacuna declarada no resultado
da auditoria, e nenhuma regra daqui o examina.
"""

from collections.abc import Iterator

from core.dax import Token, TipoToken
from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.expressoes import varrer_dax
from core.rules.registry import regra

TIPO_DE_OBJETO = {
    "medida": "medida",
    "coluna calculada": "coluna",
    "particao calculada": "particao",
    "role": "modelo",
}


def _denominador(tokens: list[Token], posicao_da_barra: int) -> list[Token]:
    """O operando mínimo depois do `/`: um número, ou o grupo entre parênteses.

    Mínimo de propósito. Pegar tudo até o fim do argumento incluiria mais
    tokens, acharia referência com mais facilidade e faria a regra marcar
    divisão que a documentação recomenda. Errar para o lado do silêncio é a
    política do projeto: regra com precisão baixa é pior que regra ausente.
    """
    resto = tokens[posicao_da_barra + 1 :]
    if not resto:
        return []

    if resto[0].tipo is not TipoToken.PARENTESE_ABRE:
        return [resto[0]]

    profundidade = 0
    for i, t in enumerate(resto):
        if t.tipo is TipoToken.PARENTESE_ABRE:
            profundidade += 1
        elif t.tipo is TipoToken.PARENTESE_FECHA:
            profundidade -= 1
            if profundidade == 0:
                return resto[: i + 1]
    return resto


def _e_constante(denominador: list[Token]) -> bool:
    """Denominador sem referência e sem identificador é valor constante.

    A documentação recomenda o operador nesse caso, e marcar seria apontar como
    defeito o que a fonte recomenda — o erro que derrubou a PERF-004 em 06/10.
    """
    if not denominador:
        return False
    return not any(
        t.tipo in (TipoToken.REFERENCIA, TipoToken.IDENTIFICADOR) for t in denominador
    )


@regra(
    id="DAX-001",
    titulo="Divisão com o operador onde o denominador pode ser zero",
    categoria="dax",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator",
    termos_consulta=[
        "DIVIDE function versus divide operator",
        "divide by zero DAX blank",
        "safe division DAX alternate result",
        "division operator performance DAX",
    ],
    recomendacao_padrao=(
        "Troque a divisão pela função DIVIDE quando o denominador for uma expressão "
        "que possa retornar zero ou BLANK. A DIVIDE foi desenhada para tratar a "
        "divisão por zero automaticamente: sem o terceiro argumento ela devolve BLANK "
        "quando o denominador é zero ou BLANK, e com ele devolve o valor alternativo "
        "que você indicar. Ela também dispensa testar o denominador antes, e é mais "
        "otimizada para esse teste que a função IF — o ganho é significativo, porque "
        "verificar divisão por zero é caro. Há exceção declarada pela própria "
        "documentação: quando o denominador é um valor constante, o recomendado é usar "
        "o operador, porque a divisão não pode falhar e evitar o teste faz a expressão "
        "ter melhor desempenho. Sobre o valor alternativo, pense duas vezes antes de "
        "usá-lo: em medidas, devolver BLANK costuma ser o melhor desenho, porque os "
        "visuais eliminam por padrão os agrupamentos cujo resultado é BLANK, o que "
        "concentra a atenção nos grupos onde há dados."
    ),
    nota_de_verificacao=(
        "A regra não marca divisão cujo denominador é constante — a documentação "
        "recomenda o operador nesse caso. Denominador é o operando mínimo depois do "
        "'/', e é tido por constante quando não contém referência nem identificador. "
        "Falso positivo declarado: denominador constante escrito de forma que o lexer "
        "não reconheça como tal. Falso negativo declarado: denominador que é expressão "
        "mas nunca retorna zero nem BLANK na prática, como (1 + ABS([x])) — a regra "
        "marca, porque decidir isso exigiria avaliar a expressão, e avaliação de DAX "
        "está fora do MVP."
    ),
)
def divisao_sem_divide(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por expressão com divisão `/` de denominador não constante.

    O achado é a expressão, não cada barra: é na expressão que o autor corrige.
    A contagem de barras marcadas vai no detalhe da evidência.
    """
    for e in varrer_dax(modelo).expressoes:
        barras = [
            t
            for i, t in enumerate(e.tokens)
            if t.tipo is TipoToken.OPERADOR
            and t.texto == "/"
            and not _e_constante(_denominador(e.tokens, i))
        ]
        if not barras:
            continue
        yield Achado(
            id_regra="DAX-001",
            evidencia=Evidencia(
                tipo_objeto=TIPO_DE_OBJETO[e.sitio],
                objeto=e.objeto,
                tabela=e.tabela,
                trecho=e.texto,
                detalhe={
                    "ocorrencias": len(barras),
                    "posicoes": [t.posicao for t in barras],
                    "sitio": e.sitio,
                },
            ),
            mensagem=(
                f"A expressão de '{e.objeto}' divide com o operador '/' em "
                f"{len(barras)} lugar(es) onde o denominador é uma expressão que "
                "pode retornar zero ou BLANK."
            ),
        )
