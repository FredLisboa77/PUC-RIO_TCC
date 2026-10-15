"""Compilação da monografia com o Typst instalado pelo pip.

O Typst vem embutido na roda `typst`, sem instalação no sistema. As páginas
textuais (da Introdução ao fim da Conclusão) são medidas por dois marcadores
que `main.typ` grava com o número da página em que caem.
"""

import json
from pathlib import Path

import typst

RAIZ_REPO = Path(__file__).resolve().parent.parent
PASTA_MONOGRAFIA = RAIZ_REPO / "docs" / "academic" / "monografia"
PRINCIPAL = PASTA_MONOGRAFIA / "main.typ"
PDF = RAIZ_REPO / "docs" / "academic" / "monografia.pdf"

_ERROS_DO_TYPST = tuple({RuntimeError, getattr(typst, "TypstError", RuntimeError)})


class ErroDeCompilacao(Exception):
    """O Typst recusou o documento; a mensagem é a dele."""


def compilar(principal: Path = PRINCIPAL) -> bytes:
    """Compila `principal` e devolve o PDF."""
    try:
        return typst.compile(str(principal), root=str(principal.parent))
    except _ERROS_DO_TYPST as erro:
        raise ErroDeCompilacao(str(erro)) from erro


def _pagina_do_marcador(principal: Path, rotulo: str) -> int:
    try:
        bruto = typst.query(str(principal), f"<{rotulo}>", field="value", one=True, root=str(principal.parent))
    except _ERROS_DO_TYPST as erro:
        raise ErroDeCompilacao(f"marcador <{rotulo}>: {erro}") from erro
    return int(json.loads(bruto))


def paginas_textuais(principal: Path = PRINCIPAL) -> int:
    """Páginas da Introdução ao fim da Conclusão, contando as duas."""
    inicio = _pagina_do_marcador(principal, "inicio-textual")
    return _pagina_do_marcador(principal, "fim-textual") - inicio + 1
