"""Consultas sobre um resultado de auditoria, para a interface e o relatório — sem Streamlit.

Tudo aqui é puro e testável: avisos de confiança de um achado, linhas da tabela,
filtros, resumo e o painel "o que foi examinado". Desenho:
`docs/superpowers/specs/2026-10-13-interface-streamlit-design.md`, seção 3.
"""

from collections import Counter
from dataclasses import dataclass

from pydantic import ValidationError

from core.analise.base import AchadoEnriquecido
from core.auditoria import ResultadoAuditoria
from core.rules.base import ORDEM_SEVERIDADE
from core.rules.registry import Registro
from core.rules.todas import REGISTRO

SEM_TABELA = "—"

NOTA_EXPLICACAO = (
    "Texto gerado pelo modelo de linguagem. A conferência automática só verifica números e nomes, "
    "não o sentido: a ausência de aviso não garante que a explicação esteja correta. "
    "O achado e a recomendação padrão da regra não dependem do modelo."
)
"""Medido em 14/10/2026: contra a leitura humana de 61 explicações, a conferência automática teve
kappa −0,08 (progress-log). Daí o rótulo honesto em vez de "fidelidade"."""

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
            "Números ou nomes sem origem nos trechos",
            "A resposta menciona termos que não aparecem no achado nem nos trechos: "
            f"{', '.join(item.fidelidade.divergencias)}. A conferência só confere números e nomes; "
            "confira antes de agir.",
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
    do_cache: bool = False


def linhas(resultado: ResultadoAuditoria, registro: Registro) -> list[Linha]:
    todas = []
    for indice, item in enumerate(resultado.achados):
        meta = registro.meta(item.achado.id_regra)
        evidencia = item.achado.evidencia
        todas.append(Linha(
            indice=indice, severidade=meta.severidade, regra=meta.id, titulo=meta.titulo,
            categoria=meta.categoria, objeto=evidencia.objeto, tabela=evidencia.tabela or SEM_TABELA,
            aviso=bool(avisos(item)),
            do_cache=item.do_cache,
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
    do_cache: int = 0


def resumir(todas: list[Linha]) -> Resumo:
    severidades = Counter(l.severidade for l in todas)
    return Resumo(
        total=len(todas),
        por_severidade={s: severidades[s] for s in sorted(ORDEM_SEVERIDADE, key=ORDEM_SEVERIDADE.__getitem__)},
        por_categoria=dict(sorted(Counter(l.categoria for l in todas).items())),
        com_aviso=sum(1 for l in todas if l.aviso),
        do_cache=sum(1 for l in todas if l.do_cache),
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


BOM = "﻿"


class ErroDeLeitura(Exception):
    """O conteúdo não é um resultado que esta versão da ferramenta saiba mostrar."""


def ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria:
    """Mesma leitura para a interface e para a CLI do relatório. Aceita o BOM que o
    Bloco de Notas põe ao salvar de novo um JSON."""
    if isinstance(conteudo, bytes) and conteudo.startswith(BOM.encode("utf-8")):
        conteudo = conteudo[len(BOM.encode("utf-8")):]
    elif isinstance(conteudo, str) and conteudo.startswith(BOM):
        conteudo = conteudo[len(BOM):]
    try:
        resultado = ResultadoAuditoria.model_validate_json(conteudo)
    except ValidationError as erro:
        raise ErroDeLeitura(
            "O arquivo não é um resultado de auditoria desta ferramenta "
            f"({erro.error_count()} problema(s) no formato)."
        ) from erro
    registro = REGISTRO if registro is None else registro
    desconhecidas = sorted({a.achado.id_regra for a in resultado.achados} - set(registro.ids()))
    if desconhecidas:
        raise ErroDeLeitura(
            f"O resultado tem regras que esta versão da ferramenta não conhece: {', '.join(desconhecidas)}."
        )
    return resultado
