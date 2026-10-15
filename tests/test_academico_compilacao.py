"""Compilação da monografia pelo Typst do pip."""

from pathlib import Path

import pytest

from academico.__main__ import main
from academico.compilacao import PRINCIPAL, ErroDeCompilacao, compilar, paginas_textuais

DOC_COM_MARCADORES = """
#set page(paper: "a4")
Capa
#pagebreak()
#context [#metadata(here().page()) <inicio-textual>]
Primeira página textual
#pagebreak()
Segunda
#pagebreak()
Terceira
#context [#metadata(here().page()) <fim-textual>]
"""


def _escrever(pasta: Path, texto: str) -> Path:
    arquivo = pasta / "doc.typ"
    arquivo.write_text(texto, encoding="utf-8")
    return arquivo


def test_compilar_devolve_pdf(tmp_path):
    pdf = compilar(_escrever(tmp_path, "Olá"))
    assert pdf.startswith(b"%PDF")


def test_compilar_converte_erro_do_typst(tmp_path):
    with pytest.raises(ErroDeCompilacao, match="nao-existe.typ"):
        compilar(_escrever(tmp_path, '#include "nao-existe.typ"'))


def test_paginas_textuais_conta_do_inicio_ao_fim(tmp_path):
    assert paginas_textuais(_escrever(tmp_path, DOC_COM_MARCADORES)) == 3


def test_paginas_textuais_sem_marcador_e_erro(tmp_path):
    with pytest.raises(ErroDeCompilacao, match="inicio-textual"):
        paginas_textuais(_escrever(tmp_path, "Sem marcadores"))


def test_monografia_compila():
    assert compilar(PRINCIPAL).startswith(b"%PDF")


def test_cli_erro_de_compilacao_sai_com_1_sem_traceback(tmp_path, capsys):
    codigo = main(["pdf", "--principal", str(_escrever(tmp_path, '#include "nao-existe.typ"')), "--saida", str(tmp_path / "x.pdf")])
    assert codigo == 1
    saida = capsys.readouterr()
    assert "Traceback" not in saida.err
    assert "nao-existe.typ" in saida.err


def test_cli_pdf_grava_arquivo_e_informa_paginas(tmp_path, capsys):
    destino = tmp_path / "saida.pdf"
    codigo = main(["pdf", "--principal", str(_escrever(tmp_path, DOC_COM_MARCADORES)), "--saida", str(destino)])
    assert codigo == 0
    assert destino.read_bytes().startswith(b"%PDF")
    assert "3 paginas textuais" in capsys.readouterr().out
