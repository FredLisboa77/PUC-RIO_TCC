"""`python -m academico tabelas|pdf|paginas`."""

import argparse
import sys
from pathlib import Path

from academico.compilacao import PDF, PRINCIPAL, ErroDeCompilacao, compilar, paginas_textuais


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pdf(principal: Path, saida: Path) -> int:
    conteudo = compilar(principal)
    saida.write_bytes(conteudo)
    print(f"{_ascii(saida.name)}: {paginas_textuais(principal)} paginas textuais")
    return 0


def _paginas(principal: Path) -> int:
    print(f"{paginas_textuais(principal)} paginas textuais (alvo 42, limite 30 a 50)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m academico")
    sub = parser.add_subparsers(dest="comando", required=True)
    p_pdf = sub.add_parser("pdf", help="compila a monografia em PDF")
    p_pdf.add_argument("--principal", type=Path, default=PRINCIPAL)
    p_pdf.add_argument("--saida", type=Path, default=PDF)
    p_pag = sub.add_parser("paginas", help="conta as paginas textuais")
    p_pag.add_argument("--principal", type=Path, default=PRINCIPAL)
    args = parser.parse_args(argv)
    try:
        if args.comando == "pdf":
            return _pdf(args.principal, args.saida)
        return _paginas(args.principal)
    except ErroDeCompilacao as erro:
        print(_ascii(f"erro de compilacao: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
