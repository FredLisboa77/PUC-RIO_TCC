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
    dimensao_de_data,
    lado_muitos,
    lado_um,
    relacionamentos_em_escopo,
    tabela_automatica_de_data,
    tabela_por_nome,
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

    Relacionamento inativo também fica fora: a página argumenta a partir de
    desempenho de consulta e de ambiguidade de filtro, e nenhum dos dois existe
    enquanto o relacionamento não é ativado por `USERELATIONSHIP`. Dizer que ele
    "filtra nos dois sentidos" seria afirmar o que não acontece.
    """
    for r in relacionamentos_em_escopo(modelo):
        if r.direcao_filtro != "ambos_sentidos" or um_para_um(r) or not r.ativo:
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


@regra(
    id="MOD-005",
    titulo="Dimensão de data não está marcada como tabela de data",
    categoria="modelagem",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-date-tables",
    termos_consulta=[
        "mark as date table",
        "set and use date tables",
        "date table validation unique contiguous",
        "classic time intelligence functions",
    ],
    recomendacao_padrao=(
        "Marque a tabela como tabela de data (Mark as date table) e indique a coluna "
        "de data. Com as funções clássicas de inteligência temporal, a marcação é "
        "obrigatória; ela também é necessária quando os relacionamentos com a tabela "
        "de data usam colunas de outro tipo, como chaves substitutas inteiras no "
        "formato aaaammdd. Ao marcar, o Power BI remove as tabelas de data "
        "automáticas que havia criado — então visuais e expressões apoiados nelas "
        "precisam ser revisados. A coluna de data precisa ter valores únicos, sem "
        "nulos, contíguos e com o mesmo horário em todos os valores, e ser do tipo "
        "Data ou Data/hora. Se o modelo usa a inteligência temporal baseada em "
        "calendário, a marcação pode não ser necessária."
    ),
    nota_de_verificacao=(
        "A detecção assume que a marcação aparece no TMSL como dataCategory=\"Time\" "
        "na tabela, consistente com Table.DataCategory do TOM e com o P8, onde "
        "nenhuma tabela está marcada e nenhuma tem dataCategory. Pendente de "
        "confirmação empírica: marcar a DimCalendar no Desktop, salvar o PBIP e "
        "comparar o model.bim."
    ),
)
def dimensao_de_data_nao_marcada(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por dimensão de data em escopo sem `dataCategory: "Time"`.

    A dimensão é identificada estruturalmente (`escopo.dimensao_de_data`), e não
    por nome: é o lado "um" de um relacionamento entre duas colunas `dateTime`.
    """
    for nome in sorted(dimensao_de_data(modelo)):
        t = tabela_por_nome(modelo, nome)
        if t is None or t.data_category == "Time":
            continue
        yield Achado(
            id_regra="MOD-005",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={
                    "dataCategory": t.data_category,
                    "colunas_de_data": [
                        c.nome for c in t.colunas if c.tipo_dado == "dateTime"
                    ],
                },
            ),
            mensagem=(
                f"A tabela '{t.nome}' funciona como dimensão de data do modelo, mas "
                "não está marcada como tabela de data."
            ),
        )


@regra(
    id="MOD-006",
    titulo="Dimensão em floco de neve",
    categoria="modelagem",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    termos_consulta=[
        "snowflake dimension",
        "normalized dimension tables",
        "denormalize into single table",
        "relationship filter propagation chain",
    ],
    recomendacao_padrao=(
        "Avalie consolidar as tabelas da dimensão numa só. Em geral os benefícios de "
        "uma única tabela superam os de várias: o modelo carrega menos tabelas, o "
        "que é melhor em armazenamento e desempenho; as cadeias de propagação de "
        "filtro ficam mais curtas; o painel de dados apresenta menos tabelas a quem "
        "cria o relatório; e passa a ser possível criar uma hierarquia que atravesse "
        "os níveis da dimensão, o que não se faz com colunas de tabelas diferentes. "
        "O floco de neve pode ser escolha deliberada, por exemplo quando a origem "
        "dos dados já é normalizada — o custo é o acima."
    ),
)
def dimensao_em_floco_de_neve(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela que é lado "um" de um relacionamento e lado
    "muitos" de outro: a intermediária de uma cadeia dimensão-para-dimensão.

    Os lados saem da cardinalidade, nunca de `from`/`to`.

    Dois tipos de relacionamento ficam fora do cálculo da cadeia. O um-para-um,
    porque `lado_um` devolve as duas pontas dele — corretamente, as duas são lado
    "um" — e usar isso aqui faria uma tabela cujo único papel "um" vem de um
    um-para-um passar por elo intermediário de uma cadeia que não existe. E o
    inativo, porque sem propagação de filtro não há cadeia a percorrer.
    """
    relacionamentos = [
        r for r in relacionamentos_em_escopo(modelo) if r.ativo and not um_para_um(r)
    ]
    um: set[str] = set()
    muitos: set[str] = set()
    for r in relacionamentos:
        um |= lado_um(r)
        muitos |= lado_muitos(r)

    for nome in sorted(um & muitos):
        aponta_para = sorted(
            {
                destino
                for r in relacionamentos
                if nome in lado_muitos(r)
                for destino in lado_um(r)
            }
        )
        recebe_de = sorted(
            {
                origem
                for r in relacionamentos
                if nome in lado_um(r)
                for origem in lado_muitos(r)
            }
        )
        if not aponta_para or not recebe_de:
            # Cadeia precisa das duas pontas. Um lado vazio acontece quando o
            # papel vem de um muitos-para-muitos, onde não há lado "um": não é
            # elo intermediário, e a mensagem sairia com um buraco no lugar do
            # nome da tabela.
            continue
        yield Achado(
            id_regra="MOD-006",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=nome,
                tabela=nome,
                detalhe={"aponta_para": aponta_para, "recebe_de": recebe_de},
            ),
            mensagem=(
                f"A tabela '{nome}' é filtrada por {', '.join(recebe_de)} e filtra "
                f"{', '.join(aponta_para)}: é o elo intermediário de uma dimensão "
                "em floco de neve."
            ),
        )


@regra(
    id="MOD-007",
    titulo="Relacionamento um-para-um",
    categoria="modelagem",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/relationships-one-to-one",
    termos_consulta=[
        "one-to-one relationship guidance",
        "row data spans across tables",
        "merge queries consolidate tables",
        "degenerate dimension",
    ],
    recomendacao_padrao=(
        "Quando os dados de uma mesma entidade estão repartidos em duas tabelas, "
        "evite o relacionamento um-para-um e consolide as duas numa só: mescle as "
        "consultas no Power Query com junção externa à esquerda, desabilite a carga "
        "da segunda consulta, substitua os valores ausentes por um valor explícito e "
        "crie as hierarquias cabíveis. Manter as duas tabelas gera excesso de tabelas "
        "no painel de dados, dificulta encontrar campos relacionados, impede "
        "hierarquias entre níveis e produz resultados inesperados quando as linhas "
        "não casam exatamente. Se quiser preservar a organização dos campos, use "
        "pastas de exibição em vez de tabelas separadas. Há um cenário legítimo: a "
        "dimensão degenerada, derivada de uma tabela de fatos para separar as colunas "
        "usadas em filtro e agrupamento das usadas em soma."
    ),
    nota_de_verificacao=(
        "Todo relacionamento um-para-um é obrigatoriamente bidirecional — não é "
        "possível configurar de outro jeito —, por isso MOD-002 o exclui e o achado "
        "pertence a esta regra."
    ),
)
def relacionamento_um_para_um(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por relacionamento com cardinalidade "um" nas duas pontas."""
    for r in relacionamentos_em_escopo(modelo):
        if not um_para_um(r):
            continue
        yield Achado(
            id_regra="MOD-007",
            evidencia=Evidencia(
                tipo_objeto="relacionamento",
                objeto=_nome_do_relacionamento(r),
                tabela=r.tabela_origem,
                detalhe={
                    "cardinalidade": "um-para-um",
                    "crossFilteringBehavior": r.bruto.get("crossFilteringBehavior"),
                },
            ),
            mensagem=(
                f"O relacionamento {_nome_do_relacionamento(r)} é um-para-um: as "
                "duas tabelas descrevem a mesma entidade."
            ),
        )
