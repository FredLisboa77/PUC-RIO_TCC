"""Auditoria de ponta a ponta (ADR-003): ingestão → parsing → regras →
recuperação → geração → validação da citação.

`python -m core.auditoria <pasta-pbip>` grava os achados enriquecidos em
`outputs/` e imprime um resumo. Desenho:
`docs/superpowers/specs/2026-10-11-geracao-com-citacao-design.md`, seção 9.
"""

import argparse
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

from core.analise.base import AchadoEnriquecido
from core.analise.contexto import ErroDeContexto, carregar_gabaritos, verificar_ancoras
from core.analise.enriquecimento import enriquecer
from core.analise.llm import MODELO_PADRAO, ClienteOllama, ErroDeLLM, LLMClient
from core.ingest import ErroEstruturaPbip, abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.registry import Registro
from core.rules.runner import ResultadoRegras, avaliar
from core.rules.todas import REGISTRO
from rag.avaliacao import RAIZ_REPO, Gabarito
from rag.indice import BaseRag, ErroDeIndice

PASTA_SAIDA = RAIZ_REPO / "outputs"


class ErroDeAuditoria(Exception):
    """A auditoria não pode seguir sem produzir um resultado enganoso."""


ModoAuditoria = Literal["completo", "so_regras"]


class ResultadoAuditoria(BaseModel):
    projeto: str
    modo: ModoAuditoria = "completo"
    """O padrão lê como completos os JSONs gravados antes de existir o modo só regras."""
    modelo_llm: str | None
    gerado_em: str
    regras: ResultadoRegras
    """Sem os achados, que estão enriquecidos em `achados`: falhas de regra,
    lacunas de DAX e cobertura continuam visíveis."""
    achados: list[AchadoEnriquecido]
    segundos_total: float

    @model_validator(mode="after")
    def _modo_coerente(self) -> "ResultadoAuditoria":
        so_regras = self.modo == "so_regras"
        coerente = (self.modelo_llm is None) == so_regras and all(
            (a.situacao == "so_regras") == so_regras for a in self.achados
        )
        if not coerente:
            raise ValueError(
                f"resultado incoerente: modo {self.modo} com modelo_llm e situações dos achados que não batem"
            )
        return self


def nome_do_projeto(caminho: str | Path) -> str:
    caminho = Path(caminho)
    return caminho.stem if caminho.suffix.lower() == ".zip" else caminho.name


def run_audit(
    pasta_pbip: str | Path,
    *,
    llm: LLMClient,
    base: BaseRag,
    registro: Registro | None = None,
    gabaritos: dict[str, Gabarito] | None = None,
) -> ResultadoAuditoria:
    inicio = time.perf_counter()
    registro = REGISTRO if registro is None else registro
    gabaritos = carregar_gabaritos() if gabaritos is None else gabaritos
    # Partida: nenhuma chamada ao LLM se alguma regra não tiver âncora.
    verificar_ancoras(registro.ids(), gabaritos, base)

    projeto = abrir_pbip(pasta_pbip)
    resultado = avaliar(ler_modelo(projeto.model_bim), registro)
    if resultado.achados:
        try:
            llm.aquecer()
        except ErroDeLLM as erro:
            # Abortar aqui, e não marcar cada achado com `erro_llm`: um relatório
            # com tudo "sem fundamentação" pareceria resultado, e é falha de ambiente.
            raise ErroDeAuditoria(f"o LLM não respondeu no aquecimento: {erro}") from erro

    enriquecidos = [
        enriquecer(a, registro.meta(a.id_regra), base=base, gabarito=gabaritos[a.id_regra], llm=llm)
        for a in resultado.achados
    ]
    return ResultadoAuditoria(
        projeto=nome_do_projeto(pasta_pbip),
        modelo_llm=llm.nome,
        gerado_em=datetime.now().isoformat(timespec="seconds"),
        regras=resultado.model_copy(update={"achados": []}),
        achados=enriquecidos,
        segundos_total=round(time.perf_counter() - inicio, 1),
    )


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def resumir(resultado: ResultadoAuditoria) -> str:
    achados = resultado.achados
    gerados = [a for a in achados if a.situacao == "gerado"]
    motivos = Counter(a.motivo_descarte for a in achados if a.motivo_descarte)
    tempos = [a.segundos for a in achados if a.segundos is not None]
    linhas = [
        f"Projeto {resultado.projeto} - modelo {resultado.modelo_llm}",
        f"Achados: {len(achados)} | gerados: {len(gerados)} | sem fundamentacao: {len(achados) - len(gerados)}",
    ]
    if motivos:
        linhas.append("Motivos de descarte: " + ", ".join(f"{m}={n}" for m, n in sorted(motivos.items())))
    if gerados:
        citam = sum(1 for a in gerados if a.cita_ancora)
        divergem = sum(1 for a in gerados if a.fidelidade.divergencias)
        linhas.append(f"Citam a ancora: {citam}/{len(gerados)} | com divergencia de fidelidade: {divergem}")
    reduzidos = sum(1 for a in achados if a.reducoes_de_contexto)
    if reduzidos:
        linhas.append(f"Contexto reduzido para caber: {reduzidos}")
    if tempos:
        linhas.append(f"Tempo por achado: medio {sum(tempos) / len(tempos):.1f}s, pior {max(tempos):.1f}s")
    linhas.append(f"Tempo total: {resultado.segundos_total:.1f}s")
    return _ascii("\n".join(linhas))


def gravar(resultado: ResultadoAuditoria, pasta: Path | None = None) -> Path:
    pasta = PASTA_SAIDA if pasta is None else pasta
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{resultado.projeto}-{resultado.gerado_em[:10]}.json"
    caminho.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return caminho


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m core.auditoria", description="Audita um projeto PBIP.")
    parser.add_argument("pasta_pbip", help="pasta do projeto PBIP ou arquivo .zip")
    parser.add_argument("--modelo", default=MODELO_PADRAO, help="modelo do Ollama")
    args = parser.parse_args(argv)
    try:
        resultado = run_audit(args.pasta_pbip, llm=ClienteOllama(args.modelo), base=BaseRag.carregar())
    except (ErroDeAuditoria, ErroDeContexto, ErroDeIndice, ErroEstruturaPbip) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    except (ValueError, OSError) as erro:
        # `model.bim` corrompido (JSONDecodeError) ou arquivo do índice ausente: a
        # spec pede mensagem e código 1, não traceback.
        print(f"erro: {type(erro).__name__}: {erro}", file=sys.stderr)
        return 1
    print(resumir(resultado))
    try:
        caminho = gravar(resultado)
    except OSError as erro:
        # Arquivo aberto em outro programa, pasta sem permissão: a geração já
        # custou minutos, então o resumo sai antes e a falha vira mensagem.
        print(_ascii(f"erro: nao foi possivel gravar o resultado: {erro}"), file=sys.stderr)
        return 1
    print(_ascii(f"Gravado em {caminho}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
