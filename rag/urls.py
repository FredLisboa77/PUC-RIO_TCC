"""Regras de URL do catálogo de fontes.

Funções puras: nenhuma faz rede. O `toc.json` do Learn usa quatro formas de
link — relativo, relativo com `../`, relativo à raiz e absoluto —, e a relativa
à raiz não traz o idioma (`/dax/best-practices/...`). Resolvida sem prefixá-lo,
ela apontaria para fora do Learn em inglês e seria descartada.
"""

import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit

HOST_LEARN = "learn.microsoft.com"

FORA_DO_LEARN = "fora do learn"
NAO_DOCUMENTAL = "entrada de seção ou área não documental"

PREFIXOS_NAO_DOCUMENTAIS = ("contribute/", "answers/", "training/")
"""Áreas do Learn que aparecem na navegação mas não são documentação. Segunda
barreira: as páginas de entrada delas já terminam em `/`."""

_IDIOMA = re.compile(r"^/[a-z]{2}(?:-[a-z0-9]{2,4}){1,2}(?=/|$)", re.IGNORECASE)
"""Segmento de idioma no início do caminho: `/en-us`, `/pt-br`, `/sr-latn-rs` —
com ou sem barra depois, para que a raiz `/en-us` também seja reconhecida."""


def _com_idioma(caminho: str, idioma: str) -> str:
    if _IDIOMA.match(caminho):
        return _IDIOMA.sub(f"/{idioma}", caminho, count=1)
    return f"/{idioma}{caminho}"


def resolver_href(href: str, secao: str, idioma: str = "en-us") -> str:
    """URL absoluta de um `href` do `toc.json` da `secao`, no `idioma` dado."""
    if href.startswith(("http://", "https://")):
        partes = urlsplit(href)
        if partes.netloc.lower() != HOST_LEARN:
            return href
        return f"https://{HOST_LEARN}{_com_idioma(partes.path, idioma)}"
    if href.startswith("/"):
        return f"https://{HOST_LEARN}{_com_idioma(href, idioma)}"
    return urljoin(f"https://{HOST_LEARN}/{idioma}/{secao}/", href)


def motivo_de_exclusao(url: str) -> str | None:
    """Por que a URL resolvida não entra no catálogo; `None` se entra."""
    partes = urlsplit(url)
    if partes.netloc.lower() != HOST_LEARN:
        return FORA_DO_LEARN
    caminho = _IDIOMA.sub("", partes.path, count=1).lstrip("/").lower()
    if (
        partes.path.endswith("/")
        or not caminho
        or caminho.startswith(PREFIXOS_NAO_DOCUMENTAIS)
    ):
        return NAO_DOCUMENTAL
    return None


def normalizar_url(url: str) -> str:
    """Forma canônica para comparar e para gravar.

    Sem `?query`, sem `#fragmento`, sem barra final; esquema e host em
    minúsculas. No Learn o caminho também vai para minúsculas, porque o site
    não diferencia caixa e uma âncora escrita com `/DAX/` precisa casar com o
    `toc.json`, que é todo minúsculo.
    """
    partes = urlsplit(url.strip())
    host = partes.netloc.lower()
    caminho = partes.path.rstrip("/")
    if host == HOST_LEARN:
        caminho = caminho.lower()
    return urlunsplit((partes.scheme.lower(), host, caminho, "", ""))


def caminho_sem_idioma(url: str) -> str:
    """`https://learn.microsoft.com/en-us/dax/x` → `dax/x`."""
    return _IDIOMA.sub("", urlsplit(url).path, count=1).lstrip("/")


def em_outro_idioma(url: str, idioma: str) -> str:
    """A mesma página do Learn em outro idioma."""
    partes = urlsplit(url)
    return urlunsplit(
        (partes.scheme, partes.netloc, _com_idioma(partes.path, idioma), "", "")
    )


def secao_propria(url: str, secoes: Iterable[str]) -> str | None:
    """A seção à qual a página pertence pelo caminho — a mais longa que casar."""
    caminho = caminho_sem_idioma(url) + "/"
    candidatas = [s for s in secoes if caminho.startswith(s + "/")]
    return max(candidatas, key=len) if candidatas else None
