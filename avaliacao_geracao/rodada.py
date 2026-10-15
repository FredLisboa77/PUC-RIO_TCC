"""A rodada avaliada: a auditoria completa de P1–P7 cujas explicações são julgadas.

Fica fora do git (`eval/geracao/`): o contexto de cada achado traz seções do Learn,
cuja cópia é local e não redistribuível. O id do achado é estável entre rodadas, e a
impressão digital liga cada veredito ao texto que foi julgado: explicação, recomendação,
a lista de citações e, para cada citação, o link e o texto do trecho citado.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from avaliacao_geracao import ErroDeAvaliacao
from core.analise.base import AchadoEnriquecido
from core.apresentacao import ErroDeLeitura, ler_resultado
from core.auditoria import run_audit
from rag.avaliacao import RAIZ_REPO

PASTA_RODADA = RAIZ_REPO / "eval" / "geracao" / "auditorias"
PASTA_PBIP = RAIZ_REPO / "data" / "pbip"
PADRAO_PROJETOS = re.compile(r"^P[1-7]_")


def id_do_achado(projeto: str, item: AchadoEnriquecido) -> str:
    return f"{projeto}|{item.achado.id_regra}|{item.achado.evidencia.objeto}"


def impressao(item: AchadoEnriquecido) -> str | None:
    if item.geracao is None:
        return None
    por_numero = {t.numero: t for t in item.contexto}
    partes = [item.geracao.explicacao, item.geracao.recomendacao, str(item.geracao.citacoes)]
    for n in item.geracao.citacoes:
        trecho = por_numero.get(n)
        partes.append(f"{trecho.url}#{trecho.ancora}" if trecho else f"[{n}] ausente")
        partes.append(trecho.texto if trecho else "")
    texto = "\n".join(partes)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ItemDaRodada:
    projeto: str
    item: AchadoEnriquecido


Rodada = dict[str, ItemDaRodada]


def projetos_da_avaliacao(pasta: Path = PASTA_PBIP) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.is_dir() and PADRAO_PROJETOS.match(p.name))


@dataclass
class ResumoDaRodada:
    projetos: int
    achados: int
    gerados: int
    fora_do_cache: int
    """Respostas que não vieram do cache: o texto pode ter mudado desde a última rodada."""


def auditar(pastas: list[Path], destino: Path, *, llm, base, **kwargs) -> ResumoDaRodada:
    destino.mkdir(parents=True, exist_ok=True)
    resumo = ResumoDaRodada(projetos=0, achados=0, gerados=0, fora_do_cache=0)
    for pasta in pastas:
        resultado = run_audit(pasta, llm=llm, base=base, **kwargs)
        (destino / f"{resultado.projeto}.json").write_text(
            resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        resumo.projetos += 1
        resumo.achados += len(resultado.achados)
        resumo.gerados += sum(1 for a in resultado.achados if a.situacao == "gerado")
        resumo.fora_do_cache += sum(1 for a in resultado.achados if a.segundos is not None and not a.do_cache)
    return resumo


def carregar_rodada(pasta: Path = PASTA_RODADA) -> Rodada:
    arquivos = sorted(pasta.glob("*.json")) if pasta.is_dir() else []
    if not arquivos:
        raise ErroDeAvaliacao(f"nenhuma auditoria em {pasta} — rode `python -m avaliacao_geracao auditar`")
    rodada: Rodada = {}
    for arquivo in arquivos:
        try:
            resultado = ler_resultado(arquivo.read_bytes())
        except (OSError, ErroDeLeitura) as erro:
            raise ErroDeAvaliacao(f"{arquivo.name}: {erro}") from erro
        for item in resultado.achados:
            chave = id_do_achado(resultado.projeto, item)
            if chave in rodada:
                raise ErroDeAvaliacao(f"id duplicado na rodada: {chave}")
            rodada[chave] = ItemDaRodada(resultado.projeto, item)
    return rodada
