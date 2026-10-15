"""Relatório HTML da auditoria (F13; spec de 13/10/2026, seção 3).

Autocontido: CSS embutido e nenhum recurso externo além dos links para o Learn.
Todo texto passa pelo autoescape do Jinja2. Cita o texto original dos trechos;
tradução automática não entra.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import apresentacao
from core.auditoria import ResultadoAuditoria
from core.rules.registry import Registro
from core.rules.todas import REGISTRO
from rag.catalogo import url_em_portugues

PASTA_TEMPLATES = Path(__file__).resolve().parent / "templates"

_ambiente = Environment(
    loader=FileSystemLoader(PASTA_TEMPLATES),
    autoescape=select_autoescape(["html", "j2"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

ROTULOS_SEVERIDADE = {"alta": "alta", "media": "média", "baixa": "baixa"}
ORIGEM_DOS_LINKS = "https://learn.microsoft.com/"
"""Só vira link o que aponta para o Learn: um JSON aberto de fora pode trazer
`javascript:` na URL de um trecho."""


def _link_seguro(url: str) -> str | None:
    return url if url.startswith(ORIGEM_DOS_LINKS) else None


def _bloco(resultado: ResultadoAuditoria, linha: apresentacao.Linha, numero: int, registro: Registro) -> dict:
    item = resultado.achados[linha.indice]
    meta = registro.meta(item.achado.id_regra)
    por_numero = {t.numero: t for t in item.contexto}
    citacoes = [
        {"trecho": por_numero[n], "url": _link_seguro(f"{por_numero[n].url}#{por_numero[n].ancora}"),
         "url_pt": _link_seguro(url_em_portugues(por_numero[n].url) or "")}
        for n in (item.geracao.citacoes if item.geracao else [])
    ]
    return {
        "numero": numero, "linha": linha, "item": item, "meta": meta,
        "avisos": apresentacao.avisos(item), "citacoes": citacoes,
        "recomendacao": item.recomendacao_final(meta),
    }


def gerar_html(
    resultado: ResultadoAuditoria, *, tecnico: bool = False, registro: Registro | None = None
) -> str:
    registro = REGISTRO if registro is None else registro
    linhas = apresentacao.linhas(resultado, registro)
    regras = [{"meta": m, "url_pt": url_em_portugues(m.url_canonica)} for m in registro.metas()]
    return _ambiente.get_template("relatorio.html.j2").render(
        resultado=resultado,
        examinado=apresentacao.examinado(resultado),
        resumo=apresentacao.resumir(linhas),
        blocos=[_bloco(resultado, l, i, registro) for i, l in enumerate(linhas, start=1)],
        regras=regras,
        tecnico=tecnico,
        severidade=ROTULOS_SEVERIDADE,
        nota_explicacao=apresentacao.NOTA_EXPLICACAO,
    )
