"""Regras de performance estática.

Estática porque lê o modelo, não a execução: nada de VertiPaq, DAX Studio ou
XMLA (F23, Trabalhos Futuros). O que se afirma aqui é o que o `model.bim`
sustenta.
"""

from collections.abc import Iterator

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.escopo import (
    coluna_gerada_por_analise,
    dimensao_de_data,
    tabelas_em_escopo,
)
from core.rules.registry import regra


@regra(
    id="PERF-001",
    titulo="Coluna calculada em DAX",
    categoria="performance",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction",
    termos_consulta=[
        "preference for custom columns",
        "calculated column versus Power Query computed column",
        "VertiPaq compression calculated columns",
        "data refresh time model size",
    ],
    recomendacao_padrao=(
        "Prefira criar a coluna no Power Query, ou na origem dos dados. O mecanismo "
        "VertiPaq armazena a coluna calculada em DAX como qualquer outra, mas em "
        "estruturas internas que normalmente comprimem menos, e que são construídas "
        "depois de carregadas todas as consultas do Power Query — o que estende o "
        "tempo de atualização. Quando a origem é um banco, o cálculo pode ir para a "
        "consulta SQL ou ser materializado como coluna na origem. Há exceções "
        "legítimas: a coluna calculada em DAX é a melhor escolha quando a fórmula "
        "avalia medidas ou exige funcionalidade que só existe em DAX, como as funções "
        "de hierarquia pai-filho."
    ),
)
def coluna_calculada_em_dax(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por coluna com `type: calculated`.

    Duas exclusões, ambas pelo princípio de auditar o que o autor escreveu: as
    colunas de agrupamento e cluster, cujo DAX é escrito pela interface, e as
    colunas da dimensão de data — a documentação recomenda acrescentá-las a uma
    tabela de data construída em DAX.
    """
    dimensoes_de_data = dimensao_de_data(modelo)

    for t in tabelas_em_escopo(modelo):
        if t.nome in dimensoes_de_data:
            continue
        for c in t.colunas:
            if c.tipo != "calculated" or coluna_gerada_por_analise(c):
                continue
            yield Achado(
                id_regra="PERF-001",
                evidencia=Evidencia(
                    tipo_objeto="coluna",
                    objeto=f"{t.nome}[{c.nome}]",
                    tabela=t.nome,
                    trecho=c.expressao,
                    detalhe={"type": c.tipo, "dataType": c.tipo_dado},
                ),
                mensagem=(
                    f"A coluna '{c.nome}' da tabela '{t.nome}' é calculada em DAX."
                ),
            )


@regra(
    id="PERF-003",
    titulo="Coluna de ponto flutuante somada",
    categoria="performance",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-data-types",
    termos_consulta=[
        "decimal number floating point imprecision",
        "fixed decimal number data type",
        "accuracy of number type calculations",
        "sum unexpected results",
    ],
    recomendacao_padrao=(
        "Avalie trocar o tipo da coluna de Número decimal para Número decimal fixo ou "
        "Número inteiro. O Número decimal é armazenado como ponto flutuante conforme o "
        "padrão IEEE 754, isto é, de forma aproximada, com precisão de até 15 dígitos. "
        "Raramente, somar os valores de uma coluna desse tipo devolve resultado "
        "inesperado; o caso mais provável é a coluna ter muitos valores positivos e "
        "negativos, porque o resultado passa a depender da distribuição das linhas. "
        "Comparações de igualdade também podem surpreender, o que fica evidente em "
        "expressões com RANKX. O Número decimal fixo tem precisão maior, com quatro "
        "dígitos fixos à direita do separador decimal."
    ),
)
def ponto_flutuante_somado(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por coluna `double` com agregação implícita de soma."""
    for t in tabelas_em_escopo(modelo):
        for c in t.colunas:
            if c.tipo_dado != "double" or c.resumir_por != "sum":
                continue
            yield Achado(
                id_regra="PERF-003",
                evidencia=Evidencia(
                    tipo_objeto="coluna",
                    objeto=f"{t.nome}[{c.nome}]",
                    tabela=t.nome,
                    detalhe={"dataType": "double", "summarizeBy": "sum"},
                ),
                mensagem=(
                    f"A coluna '{c.nome}' da tabela '{t.nome}' é de ponto flutuante e "
                    "é somada por padrão."
                ),
            )
