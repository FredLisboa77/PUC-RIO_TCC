"""Catálogo de fontes da RAG (`rag/sources.yaml`).

`python -m rag.catalogo gerar` monta o catálogo, offline, a partir dos retratos
em `rag/tocs/`, das âncoras das regras, das notas de `rag/observacoes.yaml` e da
curadoria de `rag/leituras_sqlbi.yaml`. `python -m rag.catalogo atualizar`
baixa os retratos antes. Desenho: `docs/superpowers/specs/
2026-10-09-catalogo-de-fontes-rag-design.md`.
"""

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ValidationError

from rag import tocs
from rag.tocs import IDIOMAS, SECOES, Retrato
from rag.urls import (
    caminho_sem_idioma,
    em_outro_idioma,
    motivo_de_exclusao,
    normalizar_url,
    resolver_href,
    secao_propria,
)

LICENCA_LEARN = (
    "Termos de uso do Microsoft Learn — uso pessoal e não comercial; cópia local "
    "não redistribuída (https://learn.microsoft.com/en-us/legal/termsofuse)"
)
LICENCA_SQLBI = (
    "© SQLBI, todos os direitos reservados — somente referência bibliográfica; "
    "conteúdo não coletado"
)

RAIZ = Path(__file__).resolve().parent
PASTA_TOCS = RAIZ / "tocs"
PASTA_BRUTA = RAIZ / "store" / "raw" / "tocs"
ARQUIVO_FONTES = RAIZ / "sources.yaml"
ARQUIVO_OBSERVACOES = RAIZ / "observacoes.yaml"
ARQUIVO_LEITURAS = RAIZ / "leituras_sqlbi.yaml"

CABECALHO_YAML = (
    "# Gerado por `python -m rag.catalogo gerar` — não editar à mão.\n"
    "# Notas: rag/observacoes.yaml. Leituras do SQLBI: rag/leituras_sqlbi.yaml.\n"
)

Retratos = dict[tuple[str, str], Retrato]
"""Chave `(idioma, secao)`."""


class ErroDeCatalogo(Exception):
    """O catálogo não pode ser gerado sem perder algo em silêncio."""


class Fonte(BaseModel):
    """Uma entrada do `sources.yaml`. A ordem dos campos é a ordem no arquivo."""

    id: str
    url: str
    url_pt_br: str | None
    titulo: str
    organizacao: str
    data_acesso: str
    licenca: str
    origem: list[str]
    indexar: bool
    regras: list[str]
    observacao: str | None = None


class LeituraSqlbi(BaseModel):
    """Uma entrada de `rag/leituras_sqlbi.yaml`, mantido à mão."""

    url: str
    titulo: str
    regras: list[str]
    verificado_em: date


@dataclass
class ResultadoCatalogo:
    fontes: list[Fonte]
    exclusoes: Counter = field(default_factory=Counter)


def _retrato(retratos: Retratos, idioma: str, secao: str) -> Retrato:
    try:
        return retratos[(idioma, secao)]
    except KeyError:
        raise ErroDeCatalogo(
            f"falta o retrato {idioma}/{secao} — rode `python -m rag.catalogo atualizar`"
        ) from None


def _ultimo_segmento(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _secao_do_titulo(url: str, por_secao: dict[str, object]) -> str:
    """A seção própria da página, se ela a retrata; senão, a primeira na ordem
    de `SECOES` que a retrata."""
    propria = secao_propria(url, por_secao)
    if propria is not None:
        return propria
    return next(s.caminho for s in SECOES if s.caminho in por_secao)


def _fontes_do_learn(
    retratos: Retratos, ancoras: dict[str, str]
) -> tuple[dict[str, Fonte], Counter]:
    exclusoes: Counter = Counter()
    titulos: dict[str, dict[str, tuple[str | None, Retrato]]] = {}
    origens: dict[str, set[str]] = {}

    for secao in SECOES:
        retrato = _retrato(retratos, "en-us", secao.caminho)
        for item in retrato.itens:
            url = resolver_href(item.href, secao.caminho, "en-us")
            motivo = motivo_de_exclusao(url)
            if motivo is not None:
                if secao.papel == "origem":
                    exclusoes[motivo] += 1
                continue
            chave = normalizar_url(url)
            titulos.setdefault(chave, {}).setdefault(secao.caminho, (item.titulo, retrato))
            if secao.papel == "origem":
                origens.setdefault(chave, set()).add(f"toc:{secao.caminho}")

    em_pt_br: dict[str, set[str]] = {}
    for secao in SECOES:
        retrato = _retrato(retratos, "pt-br", secao.caminho)
        conjunto: set[str] = set()
        for item in retrato.itens:
            url = resolver_href(item.href, secao.caminho, "pt-br")
            if motivo_de_exclusao(url) is None:
                conjunto.add(normalizar_url(em_outro_idioma(url, "en-us")))
        em_pt_br[secao.caminho] = conjunto

    regras_por_url: dict[str, set[str]] = {}
    faltantes: list[str] = []
    for id_regra, url in sorted(ancoras.items()):
        chave = normalizar_url(url)
        if chave not in titulos:
            faltantes.append(f"{id_regra}: {url}")
            continue
        origens.setdefault(chave, set()).add(f"regra:{id_regra}")
        regras_por_url.setdefault(chave, set()).add(id_regra)
    if faltantes:
        raise ErroDeCatalogo(
            "âncora fora de todos os retratos — acrescente a seção em "
            "`rag.tocs.SECOES` e rode `python -m rag.catalogo atualizar`:\n  "
            + "\n  ".join(faltantes)
        )

    fontes: dict[str, Fonte] = {}
    for chave, conjunto in origens.items():
        secao = _secao_do_titulo(chave, titulos[chave])
        titulo, retrato = titulos[chave][secao]
        identificador = "learn:" + caminho_sem_idioma(chave)
        fontes[identificador] = Fonte(
            id=identificador,
            url=chave,
            url_pt_br=em_outro_idioma(chave, "pt-br") if chave in em_pt_br[secao] else None,
            titulo=titulo or _ultimo_segmento(chave),
            organizacao="Microsoft",
            data_acesso=retrato.baixado_em.isoformat(),
            licenca=LICENCA_LEARN,
            origem=sorted(conjunto),
            indexar=True,
            regras=sorted(regras_por_url.get(chave, set())),
        )
    return fontes, exclusoes


def _fontes_do_sqlbi(
    leituras: list[LeituraSqlbi], ids_de_regras: set[str]
) -> list[Fonte]:
    """Referências curadas: entram com `indexar: false` e nunca são baixadas.

    O conteúdo do SQLBI é de todos os direitos reservados, sem permissão de uso
    nos termos do site (spec, seção 5.3); link e título são referência
    bibliográfica.
    """
    fontes: list[Fonte] = []
    vistas: set[str] = set()
    for leitura in leituras:
        partes = urlsplit(leitura.url)
        if (
            partes.scheme != "https"
            or partes.netloc.lower() != "www.sqlbi.com"
            or not partes.path.startswith("/articles/")
            or partes.path.rstrip("/") == "/articles"
        ):
            raise ErroDeCatalogo(
                f"leitura do SQLBI fora de https://www.sqlbi.com/articles/: {leitura.url}"
            )
        if not leitura.regras:
            raise ErroDeCatalogo(f"leitura do SQLBI sem regra: {leitura.url}")
        desconhecidas = sorted(set(leitura.regras) - ids_de_regras)
        if desconhecidas:
            raise ErroDeCatalogo(
                f"leitura do SQLBI com regra inexistente {', '.join(desconhecidas)}: "
                f"{leitura.url}"
            )
        chave = normalizar_url(leitura.url)
        if chave in vistas:
            raise ErroDeCatalogo(f"leitura do SQLBI repetida: {leitura.url}")
        vistas.add(chave)
        fontes.append(
            Fonte(
                id="sqlbi:" + _ultimo_segmento(chave),
                url=leitura.url,
                url_pt_br=None,
                titulo=leitura.titulo,
                organizacao="SQLBI",
                data_acesso=leitura.verificado_em.isoformat(),
                licenca=LICENCA_SQLBI,
                origem=["curadoria:sqlbi"],
                indexar=False,
                regras=sorted(set(leitura.regras)),
            )
        )
    return fontes


def montar_catalogo(
    retratos: Retratos,
    ancoras: dict[str, str],
    observacoes: dict[str, str],
    leituras_sqlbi: list[LeituraSqlbi],
) -> ResultadoCatalogo:
    """O catálogo, ordenado por `id`. Função pura: sem rede e sem arquivo.
    As leituras do SQLBI entram como referência (`indexar: false`).

    Falha alto — `ErroDeCatalogo` — quando produzir o catálogo perderia algo em
    silêncio: retrato ausente, âncora de regra fora de todos os retratos, nota
    para uma página que saiu do catálogo.
    """
    fontes, exclusoes = _fontes_do_learn(retratos, ancoras)
    for fonte in _fontes_do_sqlbi(leituras_sqlbi, set(ancoras)):
        fontes[fonte.id] = fonte

    orfas = sorted(set(observacoes) - set(fontes))
    if orfas:
        raise ErroDeCatalogo(
            "nota em rag/observacoes.yaml para id fora do catálogo: " + ", ".join(orfas)
        )
    for identificador, texto in observacoes.items():
        fontes[identificador] = fontes[identificador].model_copy(update={"observacao": texto})

    return ResultadoCatalogo(
        fontes=[fontes[i] for i in sorted(fontes)], exclusoes=exclusoes
    )


def ler_retratos(pasta: Path) -> Retratos:
    retratos: Retratos = {}
    for secao in SECOES:
        for idioma in IDIOMAS:
            caminho = tocs.caminho_do_retrato(pasta, idioma, secao.caminho)
            if not caminho.is_file():
                raise ErroDeCatalogo(
                    f"falta o retrato {caminho} — rode `python -m rag.catalogo atualizar`"
                )
            try:
                retratos[(idioma, secao.caminho)] = Retrato.model_validate_json(
                    caminho.read_text(encoding="utf-8")
                )
            except ValidationError as erro:
                raise ErroDeCatalogo(
                    f"retrato com estrutura inesperada: {caminho}\n{erro}"
                ) from erro
    return retratos


def _ler_yaml(caminho: Path) -> object:
    if not caminho.is_file():
        return None
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def ler_observacoes(caminho: Path) -> dict[str, str]:
    dados = _ler_yaml(caminho) or {}
    if not isinstance(dados, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in dados.items()
    ):
        raise ErroDeCatalogo(f"{caminho}: esperado um mapeamento id -> texto")
    return dados


def ler_leituras_sqlbi(caminho: Path) -> list[LeituraSqlbi]:
    dados = _ler_yaml(caminho) or []
    if not isinstance(dados, list):
        raise ErroDeCatalogo(f"{caminho}: esperada uma lista de leituras")
    try:
        return [LeituraSqlbi.model_validate(item) for item in dados]
    except ValidationError as erro:
        raise ErroDeCatalogo(f"{caminho}: entrada inválida\n{erro}") from erro


def como_yaml(fontes: list[Fonte]) -> str:
    corpo = yaml.safe_dump(
        [f.model_dump() for f in fontes],
        sort_keys=False,
        allow_unicode=True,
        width=10_000,
        default_flow_style=False,
    )
    return CABECALHO_YAML + corpo


def escrever_yaml(fontes: list[Fonte], caminho: Path) -> None:
    """LF sempre: com `core.autocrlf` o Git converte no checkout, e o teste de
    arquivo gerado compara texto, não bytes."""
    caminho.write_text(como_yaml(fontes), encoding="utf-8", newline="\n")


def ancoras_do_registro() -> dict[str, str]:
    """`{id_regra: url_canonica}`. Importa o registro aqui, na camada de
    comando, para que a montagem não dependa de `core/`."""
    from core.rules.todas import REGISTRO

    return {meta.id: meta.url_canonica for meta in REGISTRO.metas()}


def gerar(
    *,
    pasta_tocs: Path | None = None,
    destino: Path | None = None,
    observacoes: Path | None = None,
    leituras: Path | None = None,
    ancoras: dict[str, str] | None = None,
) -> ResultadoCatalogo:
    resultado = montar_catalogo(
        ler_retratos(pasta_tocs or PASTA_TOCS),
        ancoras_do_registro() if ancoras is None else ancoras,
        ler_observacoes(observacoes or ARQUIVO_OBSERVACOES),
        ler_leituras_sqlbi(leituras or ARQUIVO_LEITURAS),
    )
    escrever_yaml(resultado.fontes, destino or ARQUIVO_FONTES)
    return resultado


def atualizar(
    *,
    buscar: tocs.Buscador | None = None,
    hoje: date | None = None,
    pasta_tocs: Path | None = None,
    pasta_bruta: Path | None = None,
    destino: Path | None = None,
    observacoes: Path | None = None,
    leituras: Path | None = None,
    ancoras: dict[str, str] | None = None,
) -> ResultadoCatalogo:
    arquivo_leituras = leituras or ARQUIVO_LEITURAS
    tocs.baixar_retratos(
        buscar or tocs.buscar_padrao,
        hoje or date.today(),
        pasta_tocs or PASTA_TOCS,
        pasta_bruta or PASTA_BRUTA,
        [leitura.url for leitura in ler_leituras_sqlbi(arquivo_leituras)],
    )
    return gerar(
        pasta_tocs=pasta_tocs,
        destino=destino,
        observacoes=observacoes,
        leituras=arquivo_leituras,
        ancoras=ancoras,
    )


def resumo(resultado: ResultadoCatalogo, ancoras: dict[str, str]) -> str:
    fontes = resultado.fontes
    indexadas = [f for f in fontes if f.indexar]
    # Conta entradas, não origens: uma página âncora de duas regras conta 1 em "regra".
    por_origem: Counter = Counter()
    for f in fontes:
        por_origem.update({"regra" if o.startswith("regra:") else o for o in f.origem})
    linhas = [
        f"Catálogo: {len(fontes)} entradas — {len(indexadas)} indexadas, "
        f"{len(fontes) - len(indexadas)} só referência",
        "Por origem:",
        *(f"  {origem}: {n}" for origem, n in sorted(por_origem.items())),
        "Excluídos:",
        *(f"  {motivo}: {n}" for motivo, n in sorted(resultado.exclusoes.items())),
        f"Learn com url_pt_br: {sum(1 for f in indexadas if f.url_pt_br)} de {len(indexadas)}",
        "Âncoras:",
    ]
    for id_regra in sorted(ancoras):
        entrada = next(f.id for f in indexadas if id_regra in f.regras)
        linhas.append(f"  {id_regra} -> {entrada}")
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rag.catalogo",
        description="Gera rag/sources.yaml a partir dos retratos dos toc.json do Learn.",
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=["gerar", "atualizar"],
        default="gerar",
        help="gerar (padrão, offline) ou atualizar (baixa os retratos e gera)",
    )
    args = parser.parse_args(argv)
    try:
        ancoras = ancoras_do_registro()
        if args.comando == "atualizar":
            resultado = atualizar(ancoras=ancoras)
        else:
            resultado = gerar(ancoras=ancoras)
    except (ErroDeCatalogo, tocs.ErroDeRetrato) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    print(resumo(resultado, ancoras))
    return 0


if __name__ == "__main__":
    sys.exit(main())
