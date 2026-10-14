"""`python -m avaliacao_geracao auditar|gerar|importar|medir|consolidar`."""

import argparse
import json
import subprocess
import sys
from datetime import date

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.consolidacao import PASTA_RESULTADOS, consolidar
from avaliacao_geracao.metricas import medir
from avaliacao_geracao.planilha import CSV_OFICIAL, PLANILHA, gerar_planilha, gravar_csv, ler_csv, ler_planilha, validar
from avaliacao_geracao.rodada import PASTA_PBIP, PASTA_RODADA, auditar, carregar_rodada, projetos_da_avaliacao
from core.analise.cache import PASTA_CACHE, ClienteComCache
from core.analise.contexto import ErroDeContexto
from core.analise.llm import MODELO_PADRAO, ClienteOllama
from core.auditoria import ErroDeAuditoria
from core.ingest import ErroEstruturaPbip
from core.rules.todas import REGISTRO
from rag.avaliacao import RAIZ_REPO
from rag.indice import BaseRag, ErroDeIndice

REGISTRO_DA_PLANILHA = REGISTRO


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def criar_llm():
    return ClienteComCache(ClienteOllama(MODELO_PADRAO), PASTA_CACHE)


def carregar_base():
    return BaseRag.carregar()


def commit_atual() -> str | None:
    try:
        saida = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ_REPO,
                               capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return saida.stdout.strip() or None


def _gravar_json(dados: dict, prefixo: str) -> str:
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"{prefixo}-{date.today().isoformat()}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return str(destino)


def _auditar() -> int:
    pastas = projetos_da_avaliacao(PASTA_PBIP)
    resumo = auditar(pastas, PASTA_RODADA, llm=criar_llm(), base=carregar_base())
    print(_ascii(f"Projetos: {resumo.projetos} | achados: {resumo.achados} | gerados: {resumo.gerados} "
                 f"| fora do cache: {resumo.fora_do_cache}"))
    if resumo.fora_do_cache:
        print("Aviso: respostas fora do cache podem ter mudado o texto de uma rodada anterior.")
    return 0


def _gerar(forcar: bool) -> int:
    linhas = gerar_planilha(carregar_rodada(PASTA_RODADA), PLANILHA, forcar=forcar, registro=REGISTRO_DA_PLANILHA)
    print(_ascii(f"Planilha com {linhas} linha(s): {PLANILHA}"))
    return 0


def _importar(parcial: bool) -> int:
    rodada = carregar_rodada(PASTA_RODADA)
    lidas = ler_planilha(PLANILHA)
    problemas = validar(lidas, rodada, parcial)
    if problemas:
        for p in problemas:
            print(_ascii(f"linha {p.linha} ({p.id}): {p.motivo}"), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s); nada gravado"), file=sys.stderr)
        return 1
    completas = [l for _, l in lidas if l.pertinente and l.fiel and l.recomendacao_correta]
    gravar_csv(completas, CSV_OFICIAL)
    print(_ascii(f"Importadas {len(completas)} de {len(lidas)} linha(s) em {CSV_OFICIAL}"))
    return 0


def _medir() -> int:
    rodada = carregar_rodada(PASTA_RODADA)
    linhas = ler_csv(CSV_OFICIAL)
    problemas = validar(list(enumerate(linhas, start=2)), rodada, parcial=False)
    if problemas:
        for p in problemas:
            print(_ascii(f"linha {p.linha} ({p.id}): {p.motivo}"), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s) no CSV; nada medido"), file=sys.stderr)
        return 1
    resultado = medir(linhas, rodada, commit=commit_atual())
    print(_ascii(f"Resultado em {_gravar_json(resultado, 'geracao')}"))
    return 0


def _consolidar() -> int:
    print(_ascii(f"Consolidado em {_gravar_json(consolidar(PASTA_RESULTADOS), 'consolidado')}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m avaliacao_geracao")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("auditar", help="auditoria completa de P1-P7, com cache")
    gerar = sub.add_parser("gerar", help="gera a planilha cega da rubrica")
    gerar.add_argument("--forcar", action="store_true")
    importar = sub.add_parser("importar", help="valida a planilha e grava o CSV oficial")
    importar.add_argument("--parcial", action="store_true")
    sub.add_parser("medir", help="mede a rubrica")
    sub.add_parser("consolidar", help="junta todos os resultados")
    args = parser.parse_args(argv)
    try:
        if args.comando == "auditar":
            return _auditar()
        if args.comando == "gerar":
            return _gerar(args.forcar)
        if args.comando == "importar":
            return _importar(args.parcial)
        if args.comando == "medir":
            return _medir()
        return _consolidar()
    except (ErroDeAvaliacao, ErroDeAuditoria, ErroDeContexto, ErroDeIndice, ErroEstruturaPbip) as erro:
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1
    except KeyError as erro:
        print(_ascii(f"erro: formato inesperado: {erro}"), file=sys.stderr)
        return 1
    except (ValueError, OSError) as erro:
        print(_ascii(f"erro: {type(erro).__name__}: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
