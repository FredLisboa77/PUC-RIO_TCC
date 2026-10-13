"""Consultas sobre um resultado de auditoria para a interface — sem Streamlit.

Tudo aqui é puro e testável: avisos de confiança de um achado, linhas da tabela,
filtros, resumo e o painel "o que foi examinado". Desenho:
`docs/superpowers/specs/2026-10-13-interface-streamlit-design.md`, seção 3.
"""

from collections import Counter
from dataclasses import dataclass

from core.analise.base import AchadoEnriquecido
from core.auditoria import ResultadoAuditoria
from core.rules.base import ORDEM_SEVERIDADE
from core.rules.registry import Registro

SEM_TABELA = "—"

MOTIVOS = {
    "json_invalido": "o LLM não devolveu JSON válido",
    "campo_vazio": "o LLM devolveu explicação ou recomendação vazia",
    "citacoes_fora_do_limite": "o LLM citou trechos demais, nenhum, ou repetidos",
    "citacao_inexistente": "o LLM citou um trecho que não estava no contexto",
    "erro_llm": "o LLM não respondeu",
    "contexto_excedido": "nem o trecho âncora coube no contexto do modelo",
}


@dataclass(frozen=True)
class Aviso:
    titulo: str
    explicacao: str


def avisos(item: AchadoEnriquecido) -> list[Aviso]:
    """Sinais de confiança que o analista precisa ver no achado (seção 3.3)."""
    if item.situacao == "so_regras":
        return [Aviso(
            "Só regras — sem explicação do LLM",
            "A auditoria rodou sem o LLM: a recomendação é a padrão da regra e não há trechos citados.",
        )]
    lista = []
    if item.situacao == "sem_fundamentacao":
        lista.append(Aviso(
            "Sem fundamentação — recomendação padrão da regra",
            f"A resposta do LLM foi descartada ({MOTIVOS[item.motivo_descarte]}); "
            "o texto mostrado é a recomendação padrão do catálogo de regras.",
        ))
    if item.fidelidade is not None and item.fidelidade.divergencias:
        lista.append(Aviso(
            "Divergência de fidelidade",
            "A resposta menciona termos que não aparecem no achado nem nos trechos: "
            f"{', '.join(item.fidelidade.divergencias)}. Confira antes de agir.",
        ))
    if item.cita_ancora is False:
        lista.append(Aviso(
            "Não cita a seção âncora da regra",
            "A explicação se apoia em outros trechos, não na passagem da documentação que sustenta a regra.",
        ))
    if item.reducoes_de_contexto:
        lista.append(Aviso(
            "Contexto reduzido para caber",
            f"{item.reducoes_de_contexto} trecho(s) complementar(es) saíram para o prompt caber no contexto do modelo.",
        ))
    return lista


@dataclass(frozen=True)
class Linha:
    indice: int
    """Posição do achado em `resultado.achados`."""
    severidade: str
    regra: str
    titulo: str
    categoria: str
    objeto: str
    tabela: str
    aviso: bool


def linhas(resultado: ResultadoAuditoria, registro: Registro) -> list[Linha]:
    todas = []
    for indice, item in enumerate(resultado.achados):
        meta = registro.meta(item.achado.id_regra)
        evidencia = item.achado.evidencia
        todas.append(Linha(
            indice=indice, severidade=meta.severidade, regra=meta.id, titulo=meta.titulo,
            categoria=meta.categoria, objeto=evidencia.objeto, tabela=evidencia.tabela or SEM_TABELA,
            aviso=bool(avisos(item)),
        ))
    return sorted(todas, key=lambda l: (ORDEM_SEVERIDADE[l.severidade], l.regra, l.objeto))


@dataclass(frozen=True)
class Filtro:
    """Conjunto vazio = sem restrição naquela dimensão."""

    severidades: frozenset[str] = frozenset()
    categorias: frozenset[str] = frozenset()
    regras: frozenset[str] = frozenset()
    tabelas: frozenset[str] = frozenset()
    so_com_aviso: bool = False


def filtrar(todas: list[Linha], filtro: Filtro) -> list[Linha]:
    def passa(l: Linha) -> bool:
        return (
            (not filtro.severidades or l.severidade in filtro.severidades)
            and (not filtro.categorias or l.categoria in filtro.categorias)
            and (not filtro.regras or l.regra in filtro.regras)
            and (not filtro.tabelas or l.tabela in filtro.tabelas)
            and (not filtro.so_com_aviso or l.aviso)
        )

    return [l for l in todas if passa(l)]


def opcoes_de_filtro(todas: list[Linha]) -> dict[str, list[str]]:
    return {
        "severidades": sorted({l.severidade for l in todas}, key=ORDEM_SEVERIDADE.__getitem__),
        "categorias": sorted({l.categoria for l in todas}),
        "regras": sorted({l.regra for l in todas}),
        "tabelas": sorted({l.tabela for l in todas}),
    }


@dataclass(frozen=True)
class Resumo:
    total: int
    por_severidade: dict[str, int]
    """Sempre as três severidades, em ordem, mesmo com zero."""
    por_categoria: dict[str, int]
    com_aviso: int


def resumir(todas: list[Linha]) -> Resumo:
    severidades = Counter(l.severidade for l in todas)
    return Resumo(
        total=len(todas),
        por_severidade={s: severidades[s] for s in sorted(ORDEM_SEVERIDADE, key=ORDEM_SEVERIDADE.__getitem__)},
        por_categoria=dict(sorted(Counter(l.categoria for l in todas).items())),
        com_aviso=sum(1 for l in todas if l.aviso),
    )


@dataclass(frozen=True)
class Examinado:
    regras: str
    expressoes: str
    falhas: list[str]
    lacunas: list[str]


def examinado(resultado: ResultadoAuditoria) -> Examinado:
    """O que a auditoria leu, para ser visto junto da contagem de achados
    (docstring de `ResultadoRegras`): "15 achados" e "105 de 105 expressões"
    na mesma olhada."""
    r = resultado.regras
    analisadas, total = r.cobertura_de_expressoes
    if r.falha_na_varredura:
        expressoes = f"A varredura de DAX falhou ({r.falha_na_varredura}): as regras de texto não rodaram."
    elif total == 0:
        expressoes = "Nenhuma expressão DAX em escopo."
    else:
        expressoes = f"{analisadas} de {total} expressões DAX analisadas"
    return Examinado(
        regras=f"{r.regras_executadas} de {r.total_de_regras} regras executadas",
        expressoes=expressoes,
        falhas=[f"{f.id_regra}: {f.erro}" for f in r.regras_com_falha],
        lacunas=[f"{l.objeto} ({l.sitio}, posição {l.posicao}): {l.motivo}" for l in r.lacunas_de_expressao],
    )


def escolher(visiveis: list[Linha], selecionadas: list[int]) -> Linha | None:
    """A linha do detalhe. Uma seleção que sobrou de antes do filtro (índice
    fora da lista) cai no primeiro achado visível, nunca em erro."""
    if not visiveis:
        return None
    if selecionadas and 0 <= selecionadas[0] < len(visiveis):
        return visiveis[selecionadas[0]]
    return visiveis[0]
