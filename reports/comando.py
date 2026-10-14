"""`python -m reports <resultado.json> [--pdf] [--tecnico]`: grava o relatório ao
lado do JSON, com o mesmo nome (sufixo `-tecnico` com a seção técnica)."""

import argparse
import sys
from pathlib import Path

from core.apresentacao import ErroDeLeitura, ler_resultado
from reports.html import gerar_html
from reports.pdf import ErroDePdf, gerar_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m reports", description="Gera o relatorio de uma auditoria.")
    parser.add_argument("resultado", help="JSON gravado por python -m core.auditoria ou pela interface")
    parser.add_argument("--pdf", action="store_true", help="gera tambem o PDF (Edge do sistema)")
    parser.add_argument("--tecnico", action="store_true", help="inclui a secao tecnica")
    args = parser.parse_args(argv)

    origem = Path(args.resultado)
    try:
        resultado = ler_resultado(origem.read_bytes())
    except OSError as erro:
        print(f"erro: nao consegui abrir {origem.name}: {erro}", file=sys.stderr)
        return 1
    except ErroDeLeitura as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    nome = origem.stem + ("-tecnico" if args.tecnico else "")
    html = gerar_html(resultado, tecnico=args.tecnico)
    destino_html = origem.with_name(f"{nome}.html")
    try:
        destino_html.write_text(html, encoding="utf-8")
    except OSError as erro:
        print(f"erro: nao consegui gravar {destino_html.name}: {erro}", file=sys.stderr)
        return 1
    print(f"HTML: {destino_html}")
    if args.pdf:
        try:
            print(f"PDF: {gerar_pdf(html, origem.with_name(f'{nome}.pdf'))}")
        except ErroDePdf as erro:
            print(f"erro: {erro}", file=sys.stderr)
            return 1
    return 0
