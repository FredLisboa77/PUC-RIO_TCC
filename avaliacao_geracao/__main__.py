"""`python -m avaliacao_geracao auditar|gerar|importar|medir|consolidar`."""

import argparse
import json
import subprocess
import sys
from datetime import date
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.consolidacao import PASTA_RESULTADOS, consolidar
from avaliacao_geracao.glossario import (
    CHAVE, CSV_GLOSSARIO, CSV_SENSIBILIDADE, PASTA_REEXECUCAO, PASTA_RODADA_GLOSSARIO, PLANILHA_CEGA, SISTEMA_COM_GLOSSARIO,
    ClienteComInstrucao, aplicar_correcoes, gerar_planilha_cega, ler_correcoes, indicador_lexico, medir_glossario, montar_amostra, rodada_da_chave,
)
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


def _descrever(p) -> str:
    return f"linha {'-' if p.linha is None else p.linha} ({p.id}): {p.motivo}"


def _auditar() -> int:
    pastas = projetos_da_avaliacao(PASTA_PBIP)
    if not pastas:
        raise ErroDeAvaliacao(f"nenhum projeto P1-P7 em {PASTA_PBIP}")
    resumo = auditar(pastas, PASTA_RODADA, llm=criar_llm(), base=carregar_base())
    print(_ascii(f"Projetos: {resumo.projetos} | achados: {resumo.achados} | gerados: {resumo.gerados} "
                 f"| fora do cache: {resumo.fora_do_cache}"))
    if len(pastas) < 7:
        print(_ascii(f"Aviso: so {len(pastas)} projeto(s) de P1-P7 encontrados."))
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
            print(_ascii(_descrever(p)), file=sys.stderr)
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
            print(_ascii(_descrever(p)), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s) no CSV; nada medido"), file=sys.stderr)
        return 1
    resultado = medir(linhas, rodada, commit=commit_atual())
    print(_ascii(f"Resultado em {_gravar_json(resultado, 'geracao')}"))
    return 0


def _auditar_em(destino, llm) -> int:
    pastas = projetos_da_avaliacao(PASTA_PBIP)
    if not pastas:
        raise ErroDeAvaliacao(f"nenhum projeto P1-P7 em {PASTA_PBIP}")
    resumo = auditar(pastas, destino, llm=llm, base=carregar_base())
    print(_ascii(f"Projetos: {resumo.projetos} | achados: {resumo.achados} | gerados: {resumo.gerados} "
                 f"| fora do cache: {resumo.fora_do_cache} | em {destino}"))
    return 0


def _glossario_gerar(forcar: bool) -> int:
    if CHAVE.exists() and not forcar:
        raise ErroDeAvaliacao(f"{CHAVE} ja existe - o sorteio e fixo; use --forcar so antes de anotar")
    original, nova = carregar_rodada(PASTA_RODADA), carregar_rodada(PASTA_RODADA_GLOSSARIO)
    chave = montar_amostra(original, nova)
    linhas = gerar_planilha_cega(chave, original, nova, PLANILHA_CEGA, forcar=forcar)
    CHAVE.parent.mkdir(parents=True, exist_ok=True)
    CHAVE.write_text(json.dumps(chave, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(_ascii(f"Planilha cega com {linhas} linha(s): {PLANILHA_CEGA} (chave em {CHAVE} - nao abrir antes de anotar)"))
    return 0


def _ler_chave() -> dict:
    if not CHAVE.is_file():
        raise ErroDeAvaliacao(f"falta {CHAVE} - rode `python -m avaliacao_geracao glossario-gerar`")
    return json.loads(CHAVE.read_text(encoding="utf-8"))


def _glossario_importar(parcial: bool) -> int:
    combinada = rodada_da_chave(_ler_chave(), carregar_rodada(PASTA_RODADA), carregar_rodada(PASTA_RODADA_GLOSSARIO))
    lidas = ler_planilha(PLANILHA_CEGA)
    problemas = validar(lidas, combinada, parcial)
    if problemas:
        for p in problemas:
            print(_ascii(_descrever(p)), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s); nada gravado"), file=sys.stderr)
        return 1
    completas = [l for _, l in lidas if l.pertinente and l.fiel and l.recomendacao_correta]
    if parcial:
        print(_ascii(f"Anotadas: {len(completas)} de {len(lidas)}"))
        return 0
    gravar_csv(completas, CSV_GLOSSARIO)
    print(_ascii(f"Importadas {len(completas)} de {len(lidas)} linha(s) em {CSV_GLOSSARIO}"))
    return 0


def _glossario_medir() -> int:
    chave = _ler_chave()
    original = carregar_rodada(PASTA_RODADA)
    nova = carregar_rodada(PASTA_RODADA_GLOSSARIO)
    combinada = rodada_da_chave(chave, original, nova)
    novas = ler_csv(CSV_GLOSSARIO)
    problemas = validar(list(enumerate(novas, start=2)), combinada, parcial=False)
    if problemas:
        for p in problemas:
            print(_ascii(_descrever(p)), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s) no CSV; nada medido"), file=sys.stderr)
        return 1
    achados = sorted(k for k, r in original.items() if r.item.situacao == "gerado")
    resultado = medir_glossario(ler_csv(CSV_OFICIAL), novas, chave, achados=achados)
    if CSV_SENSIBILIDADE.is_file():
        # Fora do protocolo: a planilha não mostrava a expressão DAX do achado, que o
        # modelo recebia; só vereditos cuja única razão dependia dela são revistos.
        correcoes = ler_correcoes()
        sensivel = medir_glossario(ler_csv(CSV_OFICIAL), aplicar_correcoes(novas, correcoes), chave, achados=achados)
        resultado["sensibilidade_expressao_oculta"] = {
            "nota": "análise de sensibilidade, fora do protocolo: vereditos da nova sessão cuja única razão era um "
                    "nome ou fórmula presente na expressão do achado, que a planilha não exibia",
            "correcoes": [c.model_dump() for c in correcoes],
            **{k: sensivel[k] for k in ("itens", "consistencia", "exploratoria_mesma_sessao", "decisao")},
        }
    resultado["indicador_lexico"] = {
        "original": indicador_lexico(original),
        "reexecucao_sem_cache": indicador_lexico(carregar_rodada(PASTA_REEXECUCAO)),
        "glossario": indicador_lexico(nova),
    }
    resultado["chave"] = chave
    resultado["commit"] = commit_atual()
    print(_ascii(f"Resultado em {_gravar_json(resultado, 'glossario')}"))
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
    sub.add_parser("glossario-auditar", help="rodada P1-P7 com o glossario na instrucao (com cache)")
    sub.add_parser("glossario-reexecutar", help="rodada P1-P7 com a instrucao original, sem cache")
    g_gerar = sub.add_parser("glossario-gerar", help="sorteio e planilha cega do teste do glossario")
    g_gerar.add_argument("--forcar", action="store_true")
    g_importar = sub.add_parser("glossario-importar", help="valida a planilha cega e grava o CSV")
    g_importar.add_argument("--parcial", action="store_true")
    sub.add_parser("glossario-medir", help="comparacao pareada e indicador lexico")
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
        if args.comando == "glossario-auditar":
            return _auditar_em(PASTA_RODADA_GLOSSARIO, ClienteComInstrucao(criar_llm(), SISTEMA_COM_GLOSSARIO))
        if args.comando == "glossario-reexecutar":
            return _auditar_em(PASTA_REEXECUCAO, ClienteOllama(MODELO_PADRAO))
        if args.comando == "glossario-gerar":
            return _glossario_gerar(args.forcar)
        if args.comando == "glossario-importar":
            return _glossario_importar(args.parcial)
        if args.comando == "glossario-medir":
            return _glossario_medir()
        return _consolidar()
    except (ErroDeAvaliacao, ErroDeAuditoria, ErroDeContexto, ErroDeIndice, ErroEstruturaPbip) as erro:
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1
    except KeyError as erro:
        print(_ascii(f"erro: formato inesperado: {erro}"), file=sys.stderr)
        return 1
    except (ValueError, OSError, TypeError, IndexError, BadZipFile, InvalidFileException) as erro:
        print(_ascii(f"erro: {type(erro).__name__}: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
