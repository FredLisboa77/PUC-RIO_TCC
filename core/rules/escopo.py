"""Quem entra na auditoria.

Princípio único: **auditar o que o autor escreveu.** O Power BI gera objetos por
conta própria — tabelas de data automáticas, tabelas de mapeamento de cluster,
colunas de agrupamento — e marcá-los como defeito do autor é falso positivo.
Alguns padrões legítimos também precisam de exceção: a tabela que só carrega
medidas e a tabela de parâmetro hipotético não têm relacionamento por natureza.

Cada exclusão aqui é um predicado explícito em TMSL. Nenhuma é por nome de
objeto: nome é convenção, annotation é fato.

Este módulo é a única casa desse julgamento. Nenhuma regra o reimplementa.
"""

from core.model import Coluna, ModeloSemantico, Relacionamento, Tabela

ANOTACOES_DATA_AUTOMATICA = ("__PBI_TemplateDateTable", "__PBI_LocalDateTable")
ANOTACAO_ANALISE_GERADA = "ClusterMappingTable"
ANOTACAO_COLUNA_GERADA = "GroupingDesignState"
FUNCAO_PARAMETRO_HIPOTETICO = "GENERATESERIES"
FUNCAO_TABELA_DE_DATA = "CALENDAR"
"""Cobre `CALENDAR` e `CALENDARAUTO`, as duas funções que a documentação
recomenda para gerar a tabela de data do modelo."""


def anotacoes(bruto: dict) -> dict[str, str]:
    """As annotations do objeto TMSL, como nome → valor.

    O parser guarda o TMSL de origem em `bruto` justamente para isto: a
    annotation não foi normalizada, mas está acessível sem reabrir o arquivo.
    """
    # `or []` em vez de valor padrão: `annotations` pode existir com valor nulo
    # num `model.bim` editado à mão, e iterar `None` levantaria `TypeError` aqui
    # — em `fora_de_escopo`, o que derrubaria todas as regras de uma vez e
    # entregaria auditoria vazia.
    return {
        item.get("name", ""): item.get("value", "")
        for item in (bruto.get("annotations") or [])
        if isinstance(item, dict)
    }


def _primeira_linha_util(expressao: str | None) -> str:
    """A primeira linha que não é vazia nem comentário `//`."""
    for linha in (expressao or "").splitlines():
        limpa = linha.strip()
        if limpa and not limpa.startswith("//"):
            return limpa
    return ""


def tabela_automatica_de_data(t: Tabela) -> bool:
    """Tabela de data gerada pelo Tempo automático de data/hora (MOD-001)."""
    marcas = anotacoes(t.bruto)
    return any(marca in marcas for marca in ANOTACOES_DATA_AUTOMATICA)


def tabela_apenas_de_medidas(t: Tabela) -> bool:
    """Tabela que só carrega medidas: nenhuma coluna de dados.

    Numa tabela dessas todas as colunas são `calculatedTableColumn` — a coluna
    fictícia que o Power BI cria para a tabela existir. É padrão consagrado para
    organizar medidas, não defeito.

    O limite de uma coluna é o que separa esse padrão de uma dimensão calculada
    de verdade: *toda* coluna de tabela calculada é `calculatedTableColumn`, de
    modo que sem ele bastaria o autor pendurar uma medida numa dimensão
    calculada para a tabela inteira sair da auditoria, em silêncio.
    """
    if not t.medidas or len(t.colunas) > 1:
        return False
    return all(c.tipo == "calculatedTableColumn" for c in t.colunas)


def tabela_de_parametro_hipotetico(t: Tabela) -> bool:
    """Tabela de parâmetro hipotético: tabela calculada com `GENERATESERIES`.

    É a assinatura canónica desse objeto, e ele não tem relacionamento por
    natureza. A detecção tolera caixa, espaço e linha de comentário porque o
    predicado é o que separa um achado de um falso positivo.
    """
    for p in t.particoes:
        if p.tipo_origem != "calculated":
            continue
        if _primeira_linha_util(p.origem).upper().startswith(FUNCAO_PARAMETRO_HIPOTETICO):
            return True
    return False


def tabela_gerada_por_analise(t: Tabela) -> bool:
    """Tabela criada pelos recursos de agrupamento e clustering do Power BI."""
    return ANOTACAO_ANALISE_GERADA in anotacoes(t.bruto)


def fora_de_escopo(t: Tabela) -> bool:
    return (
        tabela_automatica_de_data(t)
        or tabela_apenas_de_medidas(t)
        or tabela_de_parametro_hipotetico(t)
        or tabela_gerada_por_analise(t)
    )


def tabelas_em_escopo(modelo: ModeloSemantico) -> list[Tabela]:
    return [t for t in modelo.tabelas if not fora_de_escopo(t)]


def nomes_em_escopo(modelo: ModeloSemantico) -> set[str]:
    return {t.nome for t in tabelas_em_escopo(modelo)}


def relacionamentos_em_escopo(modelo: ModeloSemantico) -> list[Relacionamento]:
    """Relacionamentos cujas duas pontas estão em escopo.

    Sem isto, MOD-005 marcaria as tabelas de data automáticas — elas são alvo de
    relacionamento `dateTime → dateTime` e não têm `dataCategory: "Time"`.
    """
    nomes = nomes_em_escopo(modelo)
    return [
        r
        for r in modelo.relacionamentos
        if r.tabela_origem in nomes and r.tabela_destino in nomes
    ]


def coluna_gerada_por_analise(c: Coluna) -> bool:
    """Coluna cujo DAX foi escrito pela interface de grupos e clusters."""
    return ANOTACAO_COLUNA_GERADA in anotacoes(c.bruto)


def tabela_por_nome(modelo: ModeloSemantico, nome: str) -> Tabela | None:
    for t in modelo.tabelas:
        if t.nome == nome:
            return t
    return None


def tipo_da_coluna(modelo: ModeloSemantico, tabela: str, coluna: str) -> str | None:
    """Tipo de dado de uma coluna, ou `None` se a referência não existir.

    Relacionamento apontando para objeto inexistente é modelo inconsistente, não
    motivo para a auditoria falhar.
    """
    alvo = tabela_por_nome(modelo, tabela)
    if alvo is None:
        return None
    for c in alvo.colunas:
        if c.nome == coluna:
            return c.tipo_dado
    return None


def um_para_um(r: Relacionamento) -> bool:
    return r.cardinalidade_origem == "um" and r.cardinalidade_destino == "um"


def lado_um(r: Relacionamento) -> set[str]:
    """Tabelas no lado "um" — as duas, se o relacionamento for um-para-um."""
    lados = set()
    if r.cardinalidade_origem == "um":
        lados.add(r.tabela_origem)
    if r.cardinalidade_destino == "um":
        lados.add(r.tabela_destino)
    return lados


def lado_muitos(r: Relacionamento) -> set[str]:
    lados = set()
    if r.cardinalidade_origem == "muitos":
        lados.add(r.tabela_origem)
    if r.cardinalidade_destino == "muitos":
        lados.add(r.tabela_destino)
    return lados


def tabela_de_data_marcada(t: Tabela) -> bool:
    """A tabela traz a marcação de tabela de data na propriedade do TMSL.

    **O Power BI Desktop não escreve esta propriedade.** Verificado em
    06/10/2026 contra um PBIP salvo pelo Desktop: `dataCategory` aparece só em
    coluna, nunca em tabela, e `isDateTable` não aparece em lugar nenhum. O TOM,
    por outro lado, representa a marcação assim — então um modelo editado pelo
    Tabular Editor ou pelo endpoint XMLA pode trazê-la aqui.

    Serve, portanto, como marcação **explícita** quando existe, e nunca como
    prova de ausência: para isso usa-se `colunas_com_data_automatica`.
    """
    return t.data_category == "Time"


def tabelas_de_data_automaticas(modelo: ModeloSemantico) -> set[str]:
    return {t.nome for t in modelo.tabelas if tabela_automatica_de_data(t)}


def colunas_com_data_automatica(modelo: ModeloSemantico, t: Tabela) -> list[str]:
    """Colunas da tabela que têm uma tabela de data automática pendurada.

    O vínculo está em `variations`, na coluna: o Tempo automático de data/hora
    liga a coluna de data à tabela que ele gerou, pelo `defaultHierarchy.table`.

    É a prova, no arquivo, de que a tabela **não** está marcada como tabela de
    data — porque marcar faz o Power BI remover a tabela automática que havia
    criado. Sem ela não há como saber, e a regra que depende disso precisa calar.
    """
    automaticas = tabelas_de_data_automaticas(modelo)
    com_automatica: list[str] = []

    for c in t.colunas:
        for v in c.bruto.get("variations") or []:
            if not isinstance(v, dict):
                continue
            alvo = (v.get("defaultHierarchy") or {}).get("table")
            if alvo in automaticas:
                com_automatica.append(c.nome)
                break

    return com_automatica


def tabela_de_data_em_dax(t: Tabela) -> bool:
    """Tabela de data construída em DAX com `CALENDAR` ou `CALENDARAUTO`.

    A página de orientação sobre tempo automático recomenda essas duas funções
    para gerar a tabela de data do modelo, então a expressão é assinatura de
    dimensão de data. `startswith("CALENDAR")` cobre as duas.
    """
    for p in t.particoes:
        if p.tipo_origem != "calculated":
            continue
        if _primeira_linha_util(p.origem).upper().startswith(FUNCAO_TABELA_DE_DATA):
            return True
    return False


def dimensao_de_data(modelo: ModeloSemantico) -> set[str]:
    """Tabelas que servem de dimensão de data no modelo.

    Três sinais estruturais, qualquer um deles bastando:

    1. estar no lado "um" de um relacionamento cujas duas pontas são `dateTime`;
    2. estar marcada como tabela de data (`dataCategory: "Time"`);
    3. ser tabela calculada com `CALENDAR` ou `CALENDARAUTO`.

    O primeiro sozinho deixava invisível a dimensão de data da convenção de data
    warehouse, cuja chave é um inteiro no formato aaaammdd — justamente o caso em
    que a documentação diz que marcar a tabela é necessário. E com ela invisível,
    PERF-001 voltava a marcar as colunas de calendário que a mesma documentação
    recomenda acrescentar.

    Serve a dois propósitos opostos — é o alvo de MOD-005 e a exclusão de
    PERF-001 —, e é por isso que mora aqui.
    """
    dimensoes: set[str] = set()

    for r in relacionamentos_em_escopo(modelo):
        tipo_origem = tipo_da_coluna(modelo, r.tabela_origem, r.coluna_origem)
        tipo_destino = tipo_da_coluna(modelo, r.tabela_destino, r.coluna_destino)
        if tipo_origem == "dateTime" and tipo_destino == "dateTime":
            dimensoes |= lado_um(r)

    for t in tabelas_em_escopo(modelo):
        if tabela_de_data_marcada(t) or tabela_de_data_em_dax(t):
            dimensoes.add(t.nome)

    return dimensoes
