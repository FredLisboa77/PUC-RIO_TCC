"""Regras de modelagem.

Cada regra declara a página do Microsoft Learn que a sustenta, e a recomendação
padrão repete as exceções que essa página declara. Afirmar mais do que a fonte é
o defeito que esta etapa evitou duas vezes ao verificar as âncoras antes de
escrever código (spec, seção 9).
"""

from collections.abc import Iterator

from core.model import ModeloSemantico, Relacionamento
from core.rules.base import Achado, Evidencia
from core.rules.escopo import (
    ANOTACOES_DATA_AUTOMATICA,
    anotacoes,
    relacionamentos_em_escopo,
    tabela_automatica_de_data,
    tabelas_em_escopo,
    um_para_um,
)
from core.rules.registry import regra


def _nome_do_relacionamento(r: Relacionamento) -> str:
    return (
        f"{r.tabela_origem}[{r.coluna_origem}] → "
        f"{r.tabela_destino}[{r.coluna_destino}]"
    )


@regra(
    id="MOD-001",
    titulo="Tempo automático de data/hora está ligado",
    categoria="modelagem",
    severidade="alta",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time",
    termos_consulta=[
        "auto date/time",
        "hidden auto date/time tables",
        "disable auto date time",
        "model size date columns",
    ],
    recomendacao_padrao=(
        "Desligue o Tempo automático de data/hora e use uma tabela de data própria, "
        "marcada como tabela de data. Cada coluna de data do modelo gera uma tabela "
        "oculta, que é uma tabela calculada e aumenta o tamanho do modelo e o tempo "
        "de atualização. Como a opção se aplica a todas as colunas de data ou a "
        "nenhuma, não é possível desligá-la caso a caso. Mantenha-a ligada apenas em "
        "modelos exploratórios, com necessidades simples de tempo em períodos de "
        "calendário."
    ),
)
def tempo_automatico_ligado(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela de data gerada pelo produto.

    É a única regra que olha fora do escopo: estas tabelas são o achado dela, e
    insumo de nenhuma outra.
    """
    for t in modelo.tabelas:
        if not tabela_automatica_de_data(t):
            continue
        marcas = anotacoes(t.bruto)
        annotation = next(m for m in ANOTACOES_DATA_AUTOMATICA if m in marcas)
        yield Achado(
            id_regra="MOD-001",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={"annotation": annotation, "colunas": len(t.colunas)},
            ),
            mensagem=(
                f"A tabela oculta '{t.nome}' foi gerada pelo Tempo automático de "
                "data/hora, não pelo autor do modelo."
            ),
        )


@regra(
    id="MOD-002",
    titulo="Relacionamento com filtro bidirecional",
    categoria="modelagem",
    severidade="alta",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering",
    termos_consulta=[
        "bi-directional relationship",
        "filter both directions",
        "CROSSFILTER function",
        "relationship query performance",
    ],
    recomendacao_padrao=(
        "Minimize o uso de relacionamentos bidirecionais: eles exigem mais "
        "processamento, podem degradar o desempenho das consultas e tornam o "
        "comportamento dos filtros confuso para quem usa o relatório. Há dois "
        "cenários em que a propagação nos dois sentidos é legítima — a tabela-ponte "
        "de uma relação muitos-para-muitos entre dimensões, e a análise de uma "
        "dimensão no contexto de outra —, e nos dois a documentação prefere ativar "
        "o filtro bidirecional dentro da medida, com a função CROSSFILTER, em vez de "
        "na propriedade do relacionamento. Para limitar as opções de um segmentador "
        "ao que tem dados, prefira um filtro de visual sobre a medida."
    ),
)
def relacionamento_bidirecional(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por relacionamento bidirecional, exceto um-para-um.

    Num um-para-um a bidirecionalidade é imposta pelo produto — "it isn't
    possible to configure otherwise" —, então o achado pertence a MOD-007.
    """
    for r in relacionamentos_em_escopo(modelo):
        if r.direcao_filtro != "ambos_sentidos" or um_para_um(r):
            continue
        yield Achado(
            id_regra="MOD-002",
            evidencia=Evidencia(
                tipo_objeto="relacionamento",
                objeto=_nome_do_relacionamento(r),
                tabela=r.tabela_origem,
                detalhe={
                    "crossFilteringBehavior": "bothDirections",
                    "cardinalidade": f"{r.cardinalidade_origem}-para-{r.cardinalidade_destino}",
                },
            ),
            mensagem=(
                f"O relacionamento {_nome_do_relacionamento(r)} filtra nos dois "
                "sentidos."
            ),
        )


@regra(
    id="MOD-003",
    titulo="Tabela sem relacionamento com o resto do modelo",
    categoria="modelagem",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    termos_consulta=[
        "star schema model relationships",
        "dimension table fact table",
        "table not related",
        "filter propagation",
    ],
    recomendacao_padrao=(
        "Verifique se a tabela precisa de um relacionamento. Um modelo bem desenhado "
        "entrega o número certo de tabelas com os relacionamentos devidos no lugar: "
        "sem relacionamento, a tabela não filtra nem é filtrada pelas demais, e um "
        "visual que combine os campos dela com os de outra tabela não produz o "
        "resultado esperado. Se a tabela existe apenas para apoiar a integração de "
        "outras consultas, desabilite a carga dela no Power Query."
    ),
    nota_de_verificacao=(
        "Âncora geral, não artigo dedicado — é a mais fraca do conjunto. Daí a "
        "severidade baixa. Reavaliar na Fase 3, com o trecho recuperado em mãos."
    ),
)
def tabela_sem_relacionamento(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela em escopo ausente de todos os relacionamentos.

    Olha **todos** os relacionamentos, não só os em escopo: uma tabela ligada
    apenas a uma tabela de data automática está relacionada, ainda que a outra
    ponta não seja auditável.
    """
    relacionadas: set[str] = set()
    for r in modelo.relacionamentos:
        relacionadas.add(r.tabela_origem)
        relacionadas.add(r.tabela_destino)

    for t in tabelas_em_escopo(modelo):
        if t.nome in relacionadas:
            continue
        yield Achado(
            id_regra="MOD-003",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={"colunas": len(t.colunas), "medidas": len(t.medidas)},
            ),
            mensagem=(
                f"A tabela '{t.nome}' não participa de nenhum relacionamento do "
                "modelo."
            ),
        )
