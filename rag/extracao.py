"""Extração do texto estruturado das páginas coletadas (Fase 3).

`python -m rag.extracao` lê o HTML bruto de `rag/store/raw/paginas/` e grava em
`rag/store/textos/` um JSON por página: título real, seções com âncora, nível
e caminho, e blocos tipados. Offline: mudou o extrator, reprocessa-se em
segundos (R-13). Desenho: `docs/superpowers/specs/
2026-10-09-coleta-da-base-rag-design.md`, seção 3.
"""

from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel

VERSAO_EXTRATOR = 1

SECOES_EXCLUIDAS = frozenset({"related-content", "next-steps", "see-also"})
"""Seções do corpo que são só listas de links. "In this article", "Feedback" e
"Additional resources" já ficam fora do corpo do artigo."""

_ROTULOS_DE_NOTA = {
    "NOTE": "Note",
    "TIP": "Tip",
    "IMPORTANT": "Important",
    "WARNING": "Warning",
    "CAUTION": "Caution",
}
_NIVEIS = {"h2": 2, "h3": 3, "h4": 4}
_IGNORADOS = frozenset({"img", "script", "style", "nav", "svg"})


class ErroDeExtracao(Exception):
    """Uma página não pôde ser extraída; as demais seguem."""


class Bloco(BaseModel):
    tipo: Literal["paragrafo", "lista", "tabela", "codigo", "nota"]
    texto: str
    linguagem: str | None = None
    rotulo: str | None = None


class Secao(BaseModel):
    ancora: str
    titulo: str
    nivel: int
    caminho: str
    blocos: list[Bloco]


class PaginaExtraida(BaseModel):
    versao_extrator: int
    id: str
    url: str
    titulo: str
    secoes: list[Secao]
    secoes_excluidas: list[str]
    metadados: dict[str, str | None] = {}


def _texto(no: Tag) -> str:
    return " ".join(no.get_text(" ", strip=True).split())


def _blocos(no: Tag) -> list[Bloco]:
    nome = no.name
    if nome in _IGNORADOS:
        return []
    if nome == "p":
        texto = _texto(no)
        return [Bloco(tipo="paragrafo", texto=texto)] if texto else []
    if nome in ("ul", "ol"):
        itens = [t for li in no.find_all("li", recursive=False) if (t := _texto(li))]
        return [Bloco(tipo="lista", texto="\n".join(f"- {i}" for i in itens))] if itens else []
    if nome == "table":
        linhas = []
        for tr in no.find_all("tr"):
            celulas = [_texto(c) for c in tr.find_all(["th", "td"])]
            if any(celulas):
                linhas.append(" | ".join(celulas))
        return [Bloco(tipo="tabela", texto="\n".join(linhas))] if linhas else []
    if nome == "pre":
        codigo = no.find("code") or no
        classes = codigo.get("class") or []
        linguagem = next((c.removeprefix("lang-") for c in classes if c.startswith("lang-")), None)
        texto = codigo.get_text().strip("\n")
        return [Bloco(tipo="codigo", texto=texto, linguagem=linguagem)] if texto.strip() else []
    if nome == "div":
        classes = no.get("class") or []
        rotulo = next((_ROTULOS_DE_NOTA[c] for c in classes if c in _ROTULOS_DE_NOTA), None)
        if rotulo is not None:
            texto = _texto(no)
            if texto.startswith(rotulo):
                texto = texto[len(rotulo):].strip()
            return [Bloco(tipo="nota", texto=texto, rotulo=rotulo)] if texto else []
        blocos = [b for filho in no.find_all(recursive=False) for b in _blocos(filho)]
        if blocos:
            return blocos
    texto = _texto(no)
    return [Bloco(tipo="paragrafo", texto=texto)] if texto else []


def extrair(html: str, id_fonte: str, url: str) -> PaginaExtraida:
    """A página como seções e blocos. Função pura."""
    sopa = BeautifulSoup(html, "html.parser")
    principal = sopa.find("main", id="main") or sopa
    h1 = principal.find("h1")
    if h1 is None:
        raise ErroDeExtracao(f"{id_fonte}: página sem H1")
    caixa = h1.find_parent("div", class_="content")
    corpo = caixa.find_next_sibling("div", class_="content") if caixa is not None else None
    if corpo is None:
        raise ErroDeExtracao(f"{id_fonte}: corpo do artigo não encontrado")

    titulo = _texto(h1)
    secoes = [Secao(ancora=h1.get("id") or "", titulo=titulo, nivel=1, caminho=titulo, blocos=[])]
    pilha: list[tuple[int, str]] = []
    excluidas: list[str] = []
    excluindo_ate: int | None = None

    for no in corpo.find_all(recursive=False):
        nivel = _NIVEIS.get(no.name)
        if nivel is not None:
            if excluindo_ate is not None and nivel <= excluindo_ate:
                excluindo_ate = None
            if excluindo_ate is not None:
                continue
            ancora = no.get("id") or ""
            if ancora in SECOES_EXCLUIDAS:
                excluidas.append(ancora)
                excluindo_ate = nivel
                continue
            titulo_secao = _texto(no)
            while pilha and pilha[-1][0] >= nivel:
                pilha.pop()
            pilha.append((nivel, titulo_secao))
            secoes.append(
                Secao(
                    ancora=ancora,
                    titulo=titulo_secao,
                    nivel=nivel,
                    caminho=" › ".join(t for _, t in pilha),
                    blocos=[],
                )
            )
            continue
        if excluindo_ate is not None:
            continue
        secoes[-1].blocos.extend(_blocos(no))

    com_texto = [s for s in secoes if s.blocos]
    if not com_texto:
        raise ErroDeExtracao(f"{id_fonte}: página sem texto")
    return PaginaExtraida(
        versao_extrator=VERSAO_EXTRATOR,
        id=id_fonte,
        url=url,
        titulo=titulo,
        secoes=com_texto,
        secoes_excluidas=excluidas,
    )
