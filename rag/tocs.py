"""Retratos dos `toc.json` do Microsoft Learn.

Único módulo do catálogo que faz rede. Um retrato é a listagem normalizada de
um `toc.json` — caminho e título de cada item, em ordem —, datada e gravada em
`rag/tocs/`, que é versionado. O arquivo bruto vai para `rag/store/raw/tocs/`,
fora do Git: os termos de uso do Learn permitem uso pessoal e não comercial,
não a republicação de cópia literal (spec, seção 5.2).
"""

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Literal, NamedTuple

from pydantic import BaseModel

from rag.urls import normalizar_url


class Secao(NamedTuple):
    caminho: str
    papel: Literal["origem", "ancora"]
    """`origem`: a seção inteira entra no catálogo. `ancora`: só serve para
    achar o título da âncora de uma regra que mora fora das origens."""


SECOES: tuple[Secao, ...] = (
    Secao("power-bi/guidance", "origem"),
    Secao("dax", "origem"),
    Secao("powerquery-m", "origem"),
    Secao("power-bi/connect-data", "ancora"),
    Secao("power-bi/transform-model", "ancora"),
)
"""Âncora de regra futura fora destas cinco faz `gerar` falhar nomeando a URL;
a correção é uma linha aqui e um `atualizar` (spec, seção 3.5)."""

IDIOMAS: tuple[str, ...] = ("en-us", "pt-br")


class ErroDeRetrato(Exception):
    """Falha ao obter ou interpretar um `toc.json`."""


class ItemToc(BaseModel):
    href: str
    titulo: str | None = None


class Retrato(BaseModel):
    secao: str
    idioma: str
    url: str
    baixado_em: date
    itens: list[ItemToc]


def url_do_toc(secao: str, idioma: str) -> str:
    return f"https://learn.microsoft.com/{idioma}/{secao}/toc.json"


def caminho_do_retrato(pasta: Path, idioma: str, secao: str) -> Path:
    return pasta / idioma / f"{secao}.json"


def achatar_toc(bruto: object, origem: str) -> list[ItemToc]:
    """Os itens com `href`, na ordem em que aparecem na árvore."""
    if not isinstance(bruto, dict) or not isinstance(bruto.get("items"), list):
        raise ErroDeRetrato(f"{origem}: estrutura inesperada — falta a lista 'items'")
    itens: list[ItemToc] = []

    def visitar(nos: list) -> None:
        for no in nos:
            if not isinstance(no, dict):
                continue
            if no.get("href"):
                itens.append(ItemToc(href=no["href"], titulo=no.get("toc_title")))
            visitar(no.get("children") or [])

    visitar(bruto["items"])
    return itens


def serializar_retrato(retrato: Retrato) -> str:
    """JSON com ordem de chaves e indentação fixas: o `git diff` entre dois
    retratos mostra exatamente o que a Microsoft mudou."""
    return json.dumps(retrato.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"


USER_AGENT = "powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)"
"""Identifica o projeto e o repositório. Sem e-mail: o cabeçalho viaja para
cada servidor consultado."""

TIMEOUT_S = 30

Buscador = Callable[[str], bytes]


def buscar_padrao(url: str) -> bytes:
    """GET com `urllib`. Sem repetição automática: falha é falha, e o comando é
    rodado de novo."""
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
            if resposta.status != 200:
                raise ErroDeRetrato(f"{url}: HTTP {resposta.status}")
            # `urlopen` segue 301/302 sozinho: sem esta checagem, um artigo removido
            # e redirecionado para a home passaria como "respondeu 200".
            final = resposta.geturl()
            if normalizar_url(final) != normalizar_url(url):
                raise ErroDeRetrato(f"{url}: redirecionado para {final}")
            return resposta.read()
    except urllib.error.HTTPError as erro:
        raise ErroDeRetrato(f"{url}: HTTP {erro.code}") from erro
    except (urllib.error.URLError, TimeoutError) as erro:
        raise ErroDeRetrato(f"{url}: {erro}") from erro


def _gravar_texto(caminho: Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(texto, encoding="utf-8", newline="\n")
    temporario.replace(caminho)


def baixar_retratos(
    buscar: Buscador,
    hoje: date,
    pasta_versionada: Path,
    pasta_bruta: Path,
    links_a_verificar: Sequence[str] = (),
) -> list[Retrato]:
    """Baixa os dez `toc.json` e confere os links de `links_a_verificar`.

    Nada é gravado antes de tudo dar certo: uma falha no meio deixa os retratos
    antigos intactos. Dos links a verificar só importa a resposta 200; o corpo
    é descartado — é assim que o SQLBI é conferido sem ser copiado.
    """
    baixados: list[tuple[Retrato, bytes]] = []
    for secao in SECOES:
        for idioma in IDIOMAS:
            url = url_do_toc(secao.caminho, idioma)
            conteudo = buscar(url)
            try:
                bruto = json.loads(conteudo)
            except (UnicodeDecodeError, json.JSONDecodeError) as erro:
                raise ErroDeRetrato(f"{url}: JSON inválido ({erro})") from erro
            retrato = Retrato(
                secao=secao.caminho,
                idioma=idioma,
                url=url,
                baixado_em=hoje,
                itens=achatar_toc(bruto, url),
            )
            baixados.append((retrato, conteudo))

    for link in links_a_verificar:
        buscar(link)

    for retrato, conteudo in baixados:
        _gravar_texto(
            caminho_do_retrato(pasta_versionada, retrato.idioma, retrato.secao),
            serializar_retrato(retrato),
        )
        destino_bruto = caminho_do_retrato(pasta_bruta, retrato.idioma, retrato.secao)
        destino_bruto.parent.mkdir(parents=True, exist_ok=True)
        destino_bruto.write_bytes(conteudo)
    return [retrato for retrato, _ in baixados]
