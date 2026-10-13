"""CLI do relatório: grava ao lado do JSON; falha do PDF deixa o HTML e sai com 1."""

import shutil
from pathlib import Path

from reports import comando
from reports.pdf import ErroDePdf

FIXTURE = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def _json(tmp_path) -> Path:
    destino = tmp_path / "P8-2026-10-11T214012.json"
    shutil.copy(FIXTURE, destino)
    return destino


def test_grava_html_ao_lado_do_json(tmp_path, capsys):
    origem = _json(tmp_path)
    assert comando.main([str(origem)]) == 0
    html = (tmp_path / "P8-2026-10-11T214012.html").read_text(encoding="utf-8")
    assert "Formato-antigo" in html and "Seção técnica" not in html
    assert "P8-2026-10-11T214012.html" in capsys.readouterr().out


def test_tecnico_leva_sufixo(tmp_path):
    assert comando.main([str(_json(tmp_path)), "--tecnico"]) == 0
    assert "Seção técnica" in (tmp_path / "P8-2026-10-11T214012-tecnico.html").read_text(encoding="utf-8")


def test_pdf_grava_ao_lado(tmp_path, monkeypatch):
    def falso(html, destino, **kwargs):
        destino.write_bytes(b"%PDF-falso")
        return destino

    monkeypatch.setattr(comando, "gerar_pdf", falso)
    assert comando.main([str(_json(tmp_path)), "--pdf"]) == 0
    assert (tmp_path / "P8-2026-10-11T214012.pdf").read_bytes().startswith(b"%PDF")


def test_falha_do_pdf_deixa_o_html_e_sai_com_1(tmp_path, monkeypatch, capsys):
    def falha(html, destino, **kwargs):
        raise ErroDePdf("PDF indisponível: Edge ausente")

    monkeypatch.setattr(comando, "gerar_pdf", falha)
    assert comando.main([str(_json(tmp_path)), "--pdf"]) == 1
    assert (tmp_path / "P8-2026-10-11T214012.html").is_file()
    assert "Edge ausente" in capsys.readouterr().err


def test_json_invalido_ou_ausente_sai_com_mensagem(tmp_path, capsys):
    """Review Focus 5."""
    quebrado = tmp_path / "x.json"
    quebrado.write_text("{ quebrado", encoding="utf-8")
    assert comando.main([str(quebrado)]) == 1
    assert comando.main([str(tmp_path / "nao-existe.json")]) == 1
    erro = capsys.readouterr().err
    assert "não é um resultado de auditoria" in erro and "nao-existe.json" in erro
