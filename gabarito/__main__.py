"""python -m gabarito gerar | importar [--parcial] | medir

Desenho: `docs/superpowers/specs/2026-10-11-gabarito-das-regras-design.md`.
"""

import argparse
import sys
from datetime import date

from gabarito.candidatos import ErroDeGabarito, candidatos_do_dataset
from gabarito.metricas import ResultadoMedicao, medir
from gabarito.planilha import gerar_planilha, gravar_csv, ler_csv, ler_planilha, progresso, validar
from rag.avaliacao import PASTA_PBIP, RAIZ_REPO, ErroDeAvaliacao, achados_dos_projetos

ARQUIVO_PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "anotacao-P1-P7.xlsx"
ARQUIVO_CSV = RAIZ_REPO / "eval" / "ground_truth.csv"
PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.2f}"


def formatar(r: ResultadoMedicao) -> str:
    linhas = ["regra      VP  FP  FN  VN  ind   precisao (piso-teto)   recall (piso-teto)"]
    for id_regra, m in r.por_regra.items():
        x, p, c = m.matriz, m.taxas["precisao"], m.taxas["recall"]
        linhas.append(
            f"{id_regra:<9} {x.vp:>3} {x.fp:>3} {x.fn:>3} {x.vn:>3} {x.ind_marcados + x.ind_nao_marcados:>4}   "
            f"{_pct(p['principal'])} ({_pct(p['piso'])}-{_pct(p['teto'])})        "
            f"{_pct(c['principal'])} ({_pct(c['piso'])}-{_pct(c['teto'])})"
        )
    for categoria, m in r.por_categoria.items():
        linhas.append(
            f"categoria {categoria}: micro precisao {_pct(m.taxas['precisao']['principal'])}, "
            f"recall {_pct(m.taxas['recall']['principal'])} | macro precisao "
            f"{_pct(r.macro_por_categoria[categoria]['precisao'])}, recall {_pct(r.macro_por_categoria[categoria]['recall'])}"
        )
    total = r.total_micro.taxas
    linhas.append(
        f"total micro: precisao {_pct(total['precisao']['principal'])}, recall {_pct(total['recall']['principal'])} | "
        f"macro: precisao {_pct(r.macro['precisao'])}, recall {_pct(r.macro['recall'])}"
    )
    linhas.append(f"R-03 (precisao < 0,7): {', '.join(r.r03) or 'nenhuma regra'}")
    linhas.append(
        f"R-12: {r.r12['vp']} achados confirmados (sem PERF-003: {r.r12['vp_sem_perf003']}) contra o gatilho de {r.r12['gatilho']}"
    )
    linhas.append(f"Divergencias para releitura: {len(r.divergencias)}")
    return _ascii("\n".join(linhas))


def _gerar() -> int:
    gerar_planilha(candidatos_do_dataset(), ARQUIVO_PLANILHA)
    print(_ascii(f"Planilha gerada em {ARQUIVO_PLANILHA}"))
    return 0


def _importar(parcial: bool) -> int:
    lidas = ler_planilha(ARQUIVO_PLANILHA)
    problemas = validar(lidas, candidatos_do_dataset(), parcial=parcial)
    if problemas:
        for p in problemas:
            print(_ascii(f"erro: {p.aba} linha {p.linha} | {p.id} | {p.motivo}"), file=sys.stderr)
        print(f"erro: {len(problemas)} problema(s); nada foi gravado", file=sys.stderr)
        return 1
    if parcial:
        for regra, (julgadas, total) in sorted(progresso(lidas).items()):
            print(f"{regra}: {julgadas}/{total}")
        return 0
    gravar_csv([l for _, _, l in lidas], ARQUIVO_CSV)
    print(_ascii(f"Gabarito gravado em {ARQUIVO_CSV} ({len(lidas)} linhas)"))
    return 0


def _medir() -> int:
    if not ARQUIVO_CSV.is_file():
        print(f"erro: {ARQUIVO_CSV.name} ausente - rode `python -m gabarito importar`", file=sys.stderr)
        return 1
    resultado = medir(ler_csv(ARQUIVO_CSV), achados_dos_projetos(PASTA_PBIP))
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"regras-{date.today().isoformat()}.json"
    destino.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(formatar(resultado))
    print(_ascii(f"Resultado em {destino}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m gabarito", description="Gabarito das regras em P1-P7.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="gera a planilha de anotacao cega")
    importar = sub.add_parser("importar", help="valida a planilha e grava eval/ground_truth.csv")
    importar.add_argument("--parcial", action="store_true", help="so mostra o progresso, aceita linhas em branco")
    sub.add_parser("medir", help="precisao e recall por regra")
    args = parser.parse_args(argv)
    try:
        if args.comando == "gerar":
            return _gerar()
        if args.comando == "importar":
            return _importar(args.parcial)
        return _medir()
    except (ErroDeGabarito, ErroDeAvaliacao, OSError) as erro:
        # OSError cobre a planilha aberta no Excel (PermissionError) e arquivo ausente.
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
