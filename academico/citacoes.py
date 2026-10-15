"""Conferência das citações da monografia contra `referencias.bib`.

No Typst, `@chave` serve tanto para citar quanto para referenciar um rótulo
do próprio texto (`@tab-regras`, `@sec-metodo`). É citação o que não for
rótulo definido em algum `.typ` da monografia.
"""

import re
from pathlib import Path
from typing import NamedTuple

from academico.compilacao import PASTA_MONOGRAFIA

BIB = PASTA_MONOGRAFIA / "referencias.bib"

_REFERENCIA = re.compile(r"(?<![\w\\])@([A-Za-z][\w:-]*[\w])")
_CITE = re.compile(r"cite\(<([A-Za-z][\w:.-]*)>")
_ROTULO = re.compile(r"(?<!cite\()<([A-Za-z][\w:.-]*)>")
_CHAVE_BIB = re.compile(r"^\s*@\w+\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


class Verificacao(NamedTuple):
    sem_entrada: list[str]
    nao_citadas: list[str]


def chaves_do_bib(texto: str) -> set[str]:
    return set(_CHAVE_BIB.findall(texto))


def citacoes(textos: list[str]) -> set[str]:
    rotulos = {r for t in textos for r in _ROTULO.findall(t)}
    referencias = {r for t in textos for r in _REFERENCIA.findall(t)}
    explicitas = {c for t in textos for c in _CITE.findall(t)}
    return (referencias - rotulos) | explicitas


def verificar(pasta: Path = PASTA_MONOGRAFIA) -> Verificacao:
    textos = [p.read_text(encoding="utf-8") for p in sorted(pasta.rglob("*.typ"))]
    bib = pasta / "referencias.bib"
    chaves = chaves_do_bib(bib.read_text(encoding="utf-8")) if bib.exists() else set()
    citadas = citacoes(textos)
    return Verificacao(sorted(citadas - chaves), sorted(chaves - citadas))
