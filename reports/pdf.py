"""PDF do relatório (F14; spec de 13/10/2026, seção 3.2).

Playwright controlando o Edge do sistema (`channel="msedge"`): sem baixar o
Chromium do Playwright (~150 MB, atrás do Norton). Roda numa thread própria
porque a API síncrona do Playwright recusa rodar dentro de um loop asyncio.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from playwright.sync_api import Error as ErroPlaywright
    from playwright.sync_api import sync_playwright
except ImportError:  # dependência opcional em tempo de execução: o HTML não precisa dela
    ErroPlaywright = Exception
    sync_playwright = None

CANAL = "msedge"
MARGENS = {"top": "18mm", "bottom": "18mm", "left": "15mm", "right": "15mm"}
RODAPE = (
    '<div style="font-size:8px;width:100%;text-align:center;color:#59636e;">'
    'página <span class="pageNumber"></span> de <span class="totalPages"></span></div>'
)


class ErroDePdf(Exception):
    """O PDF não pôde ser gerado; o HTML continua disponível."""


def _imprimir(html: str, destino: Path, timeout_s: float) -> None:
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel=CANAL)
        try:
            pagina = navegador.new_page()
            pagina.set_default_timeout(timeout_s * 1000)
            pagina.set_content(html, wait_until="load")
            pagina.pdf(
                path=str(destino), format="A4", print_background=True, margin=MARGENS,
                display_header_footer=True, header_template="<div></div>", footer_template=RODAPE,
            )
        finally:
            navegador.close()


def gerar_pdf(html: str, destino: Path, *, timeout_s: float = 60) -> Path:
    if sync_playwright is None:
        raise ErroDePdf(
            "PDF indisponível: o pacote playwright não está instalado (pip install -r requirements.txt)."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_imprimir, html, destino, timeout_s).result()
    except ErroPlaywright as erro:
        raise ErroDePdf(f"PDF indisponível: {erro}") from erro
    return destino
