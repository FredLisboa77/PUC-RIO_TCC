"""Coleta das páginas do catálogo (Fase 3).

`python -m rag.coleta` baixa o HTML de cada página com `indexar: true` para
`rag/store/raw/paginas/` e acrescenta uma linha por tentativa em
`rag/store/coleta.jsonl`. É retomável: pula o que já está `ok` com o mesmo
`sha256`. Tudo fica fora do Git — termos de uso do Learn. Desenho:
`docs/superpowers/specs/2026-10-09-coleta-da-base-rag-design.md`.
"""

import argparse
import hashlib
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

from rag import tocs
from rag.catalogo import ARQUIVO_FONTES, RAIZ

PASTA_STORE = RAIZ / "store"
PASTA_PAGINAS = PASTA_STORE / "raw" / "paginas"
ARQUIVO_REGISTRO = PASTA_STORE / "coleta.jsonl"

PAUSA_PADRAO_S = 1.0
FALHAS_SEGUIDAS_MAX = 5
STATUS_PARAR = frozenset({429, 503})
"""O servidor pedindo para parar: a coleta interrompe na hora."""

_METAS = {
    "updated_at": "updated_at",
    "ms.date": "ms_date",
    "git_commit_id": "git_commit_id",
    "document_id": "document_id",
}


class ErroDeColeta(Exception):
    """A coleta não pode seguir sem perder algo em silêncio."""


class PaginaAColetar(BaseModel):
    id: str
    url: str


class RegistroColeta(BaseModel):
    """Uma linha de `coleta.jsonl`: uma tentativa de baixar uma página."""

    id: str
    url: str
    situacao: Literal["ok", "erro"]
    acessado_em: datetime
    motivo: str | None = None
    tamanho: int | None = None
    sha256: str | None = None
    updated_at: str | None = None
    ms_date: str | None = None
    git_commit_id: str | None = None
    document_id: str | None = None


def caminho_da_pagina(pasta: Path, id_fonte: str) -> Path:
    """`learn:dax/calculate-function-dax` → `<pasta>/learn/dax/calculate-function-dax.html`."""
    organizacao, _, caminho = id_fonte.partition(":")
    partes = caminho.split("/")
    if not organizacao or not caminho or ".." in partes or "" in partes:
        raise ErroDeColeta(f"id inválido: {id_fonte!r}")
    return pasta / organizacao / f"{caminho}.html"


def metadados_da_pagina(html: str) -> dict[str, str | None]:
    """Os metadados de versão que o Learn publica em `<meta>`; ausente vira `None`."""
    sopa = BeautifulSoup(html, "html.parser")
    saida: dict[str, str | None] = {}
    for nome, campo in _METAS.items():
        tag = sopa.find("meta", attrs={"name": nome})
        saida[campo] = tag.get("content") if tag is not None else None
    return saida


def paginas_do_catalogo(caminho: Path) -> list[PaginaAColetar]:
    if not caminho.is_file():
        raise ErroDeColeta(f"{caminho} não existe — rode `python -m rag.catalogo`")
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8")) or []
    paginas = sorted(
        (PaginaAColetar(id=f["id"], url=f["url"]) for f in dados if f.get("indexar")),
        key=lambda p: p.id,
    )
    if not paginas:
        raise ErroDeColeta(f"{caminho}: nenhuma entrada com indexar: true")
    return paginas


def ler_registro(caminho: Path) -> dict[str, RegistroColeta]:
    """A última linha de cada id. Uma última linha cortada por desligamento no
    meio da escrita é ignorada; linha inválida em qualquer outro lugar é erro."""
    if not caminho.is_file():
        return {}
    # `errors="replace"`: um corte no meio de um caractere acentuado (o `motivo`
    # pode trazer mensagem do Windows em português) vira linha inválida, não exceção.
    linhas = caminho.read_bytes().decode("utf-8", errors="replace").splitlines()
    ultimos: dict[str, RegistroColeta] = {}
    for numero, linha in enumerate(linhas, 1):
        if not linha.strip():
            continue
        try:
            registro = RegistroColeta.model_validate_json(linha)
        except ValidationError as erro:
            if numero == len(linhas):
                break
            raise ErroDeColeta(f"{caminho.name}:{numero}: linha inválida — {erro}") from erro
        ultimos[registro.id] = registro
    return ultimos


def ja_coletada(registro: RegistroColeta | None, pasta_paginas: Path) -> bool:
    if registro is None or registro.situacao != "ok":
        return False
    arquivo = caminho_da_pagina(pasta_paginas, registro.id)
    if not arquivo.is_file():
        return False
    return hashlib.sha256(arquivo.read_bytes()).hexdigest() == registro.sha256


def _descartar_linha_cortada(caminho: Path) -> None:
    """Corta o resto de uma última linha sem quebra (desligamento no meio da
    escrita). Sem isso, a próxima linha se colaria nela e viraria linha inválida
    no meio do registro."""
    if not caminho.is_file():
        return
    with open(caminho, "rb+") as arquivo:
        conteudo = arquivo.read()
        if conteudo and not conteudo.endswith(b"\n"):
            arquivo.truncate(conteudo.rfind(b"\n") + 1)


def anexar_registro(caminho: Path, registro: RegistroColeta) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    _descartar_linha_cortada(caminho)
    with open(caminho, "a", encoding="utf-8", newline="\n") as arquivo:
        arquivo.write(registro.model_dump_json() + "\n")


@dataclass
class ResumoColeta:
    coletadas: list[str] = field(default_factory=list)
    ja_existentes: int = 0
    erros: list[RegistroColeta] = field(default_factory=list)
    interrompida: str | None = None
    total_ok: int = 0
    total: int = 0


def _gravar_atomico(caminho: Path, conteudo: bytes) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(caminho)


def _parece_queda(erro: tocs.ErroDeRetrato) -> bool:
    """Falha que sugere rede ou servidor fora do ar — a que conta para as
    `FALHAS_SEGUIDAS_MAX`. Página inexistente (4xx) ou redirecionada é o catálogo
    envelhecendo: registra e segue, sem travar as páginas seguintes."""
    if erro.status is not None:
        return erro.status >= 500
    return not erro.redirecionada


def coletar(
    paginas: list[PaginaAColetar],
    *,
    buscar: Callable[[str], bytes],
    dormir: Callable[[float], None],
    agora: Callable[[], datetime],
    pasta_paginas: Path,
    arquivo_registro: Path,
    pausa: float = PAUSA_PADRAO_S,
    limite: int | None = None,
) -> ResumoColeta:
    """Baixa as páginas pendentes, uma por vez, com pausa entre requisições.

    O arquivo é gravado antes da linha do registro: uma interrupção em qualquer
    ponto deixa, no pior caso, um arquivo sem linha `ok`, que a próxima execução
    baixa de novo.
    """
    anteriores = ler_registro(arquivo_registro)
    pendentes = [p for p in paginas if not ja_coletada(anteriores.get(p.id), pasta_paginas)]
    resumo = ResumoColeta(ja_existentes=len(paginas) - len(pendentes), total=len(paginas))
    if limite is not None:
        pendentes = pendentes[:limite]

    falhas_seguidas = 0
    for indice, pagina in enumerate(pendentes):
        if indice > 0:
            dormir(pausa)
        try:
            conteudo = buscar(pagina.url)
        except tocs.ErroDeRetrato as erro:
            registro = RegistroColeta(
                id=pagina.id, url=pagina.url, situacao="erro", acessado_em=agora(), motivo=str(erro)
            )
            anexar_registro(arquivo_registro, registro)
            resumo.erros.append(registro)
            if _parece_queda(erro):
                falhas_seguidas += 1
            if erro.status in STATUS_PARAR:
                resumo.interrompida = (
                    f"o servidor pediu para parar (HTTP {erro.status}) em {pagina.url}"
                )
                break
            if falhas_seguidas >= FALHAS_SEGUIDAS_MAX:
                resumo.interrompida = f"{FALHAS_SEGUIDAS_MAX} falhas seguidas; a última: {erro}"
                break
            continue

        falhas_seguidas = 0
        _gravar_atomico(caminho_da_pagina(pasta_paginas, pagina.id), conteudo)
        registro = RegistroColeta(
            id=pagina.id,
            url=pagina.url,
            situacao="ok",
            acessado_em=agora(),
            tamanho=len(conteudo),
            sha256=hashlib.sha256(conteudo).hexdigest(),
            **metadados_da_pagina(conteudo.decode("utf-8", errors="replace")),
        )
        anexar_registro(arquivo_registro, registro)
        resumo.coletadas.append(pagina.id)

    finais = ler_registro(arquivo_registro)
    resumo.total_ok = sum(1 for p in paginas if ja_coletada(finais.get(p.id), pasta_paginas))
    return resumo


def resumo_coleta(resumo: ResumoColeta) -> str:
    linhas = [
        f"Coletadas nesta execução: {len(resumo.coletadas)}",
        f"Já existentes: {resumo.ja_existentes}",
        f"Erros nesta execução: {len(resumo.erros)}",
        *(f"  {r.id}: {r.motivo}" for r in resumo.erros),
        f"Total ok: {resumo.total_ok} de {resumo.total}",
    ]
    if resumo.interrompida:
        linhas.append(f"INTERROMPIDA: {resumo.interrompida} — rode de novo para retomar")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.coleta",
        description="Baixa as páginas do catálogo (indexar: true) para rag/store/.",
    )
    parser.add_argument("--limite", type=int, default=None, help="coleta só as N primeiras pendentes")
    parser.add_argument("--pausa", type=float, default=PAUSA_PADRAO_S, help="segundos entre requisições")
    args = parser.parse_args(argv)
    try:
        resumo = coletar(
            paginas_do_catalogo(ARQUIVO_FONTES),
            buscar=tocs.buscar_padrao,
            dormir=time.sleep,
            agora=lambda: datetime.now(UTC),
            pasta_paginas=PASTA_PAGINAS,
            arquivo_registro=ARQUIVO_REGISTRO,
            pausa=args.pausa,
            limite=args.limite,
        )
    except ErroDeColeta as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(resumo_coleta(resumo))
    return 1 if resumo.interrompida else 0


if __name__ == "__main__":
    sys.exit(main())
