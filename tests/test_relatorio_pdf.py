"""PDF pelo Edge do sistema: real quando possível, e os caminhos de erro simulados."""

import asyncio

import pytest

from reports import pdf
from reports.pdf import ErroDePdf, gerar_pdf

HTML = "<!doctype html><html><body><h1>Relatório</h1><p>Olá, ação.</p></body></html>"


def _gerar_ou_pular(destino):
    if pdf.sync_playwright is None:
        pytest.skip("pacote playwright não instalado")
    try:
        return gerar_pdf(HTML, destino)
    except ErroDePdf as erro:
        if "is not found" in str(erro) or "não encontrado" in str(erro):
            pytest.skip(f"Edge indisponível: {erro}")
        raise


@pytest.mark.pdf
def test_pdf_real_pelo_edge(tmp_path):
    caminho = _gerar_ou_pular(tmp_path / "saida" / "r.pdf")
    assert caminho.read_bytes()[:4] == b"%PDF"


@pytest.mark.pdf
def test_pdf_real_de_dentro_de_um_loop_asyncio(tmp_path):
    """Review Focus 1: a API síncrona do Playwright recusa rodar dentro de um loop."""
    async def dentro_do_loop():
        return _gerar_ou_pular(tmp_path / "r.pdf")

    assert asyncio.run(dentro_do_loop()).read_bytes()[:4] == b"%PDF"


def test_pacote_ausente_vira_erro_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf, "sync_playwright", None)
    with pytest.raises(ErroDePdf, match="playwright não está instalado"):
        gerar_pdf(HTML, tmp_path / "r.pdf")


def test_falha_ao_abrir_o_edge_vira_erro_claro(tmp_path, monkeypatch):
    class Falha(Exception):
        pass

    class Chromium:
        def launch(self, **kwargs):
            assert kwargs["channel"] == "msedge"
            raise Falha("Chromium distribution 'msedge' is not found")

    class Contexto:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(pdf, "ErroPlaywright", Falha)
    monkeypatch.setattr(pdf, "sync_playwright", lambda: Contexto())
    with pytest.raises(ErroDePdf, match="PDF indisponível.*msedge"):
        gerar_pdf(HTML, tmp_path / "r.pdf")


def test_falha_ao_gravar_o_pdf_vira_erro_claro(tmp_path, monkeypatch):
    """Revisão final: PDF anterior aberto no leitor (bloqueado) dava traceback."""
    class Pagina:
        def set_default_timeout(self, ms):
            pass

        def set_content(self, html, **kwargs):
            pass

        def pdf(self, **kwargs):
            raise PermissionError(13, "Permission denied", kwargs["path"])

    class Navegador:
        def new_page(self):
            return Pagina()

        def close(self):
            pass

    class Chromium:
        def launch(self, **kwargs):
            return Navegador()

    class Contexto:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(pdf, "sync_playwright", lambda: Contexto())
    with pytest.raises(ErroDePdf, match="PDF indisponível.*Permission denied"):
        gerar_pdf(HTML, tmp_path / "r.pdf")
