"""Retratos dos `toc.json` do Learn.

O retrato versionado é uma listagem normalizada (caminho e título), não o
arquivo bruto: os termos de uso do Learn não permitem publicar cópia literal
num repositório público (spec, seção 5.2).
"""

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import pytest

from rag import tocs
from rag.tocs import (
    IDIOMAS,
    SECOES,
    ErroDeRetrato,
    ItemToc,
    Retrato,
    achatar_toc,
    baixar_retratos,
    buscar_padrao,
    caminho_do_retrato,
    serializar_retrato,
    url_do_toc,
)

HOJE = date(2026, 10, 9)

TOC = {
    "items": [
        {"href": "./", "toc_title": "Guidance"},
        {
            "toc_title": "Grupo sem href",
            "children": [
                {"href": "star-schema", "toc_title": "Star schema"},
                {"href": "auto-date-time"},
            ],
        },
    ]
}


def test_secoes_e_idiomas_da_spec():
    assert [(s.caminho, s.papel) for s in SECOES] == [
        ("power-bi/guidance", "origem"),
        ("dax", "origem"),
        ("powerquery-m", "origem"),
        ("power-bi/connect-data", "ancora"),
        ("power-bi/transform-model", "ancora"),
    ]
    assert IDIOMAS == ("en-us", "pt-br")


def test_achatar_toc_em_ordem_e_so_com_href():
    assert achatar_toc(TOC, "x") == [
        ItemToc(href="./", titulo="Guidance"),
        ItemToc(href="star-schema", titulo="Star schema"),
        ItemToc(href="auto-date-time", titulo=None),
    ]


@pytest.mark.parametrize("bruto", [{}, {"items": None}, [], "texto"])
def test_achatar_toc_recusa_estrutura_inesperada(bruto):
    with pytest.raises(ErroDeRetrato, match="items"):
        achatar_toc(bruto, "origem.json")


def test_url_do_toc():
    assert url_do_toc("power-bi/guidance", "pt-br") == (
        "https://learn.microsoft.com/pt-br/power-bi/guidance/toc.json"
    )


def test_caminho_do_retrato_aninha_a_secao():
    assert caminho_do_retrato(Path("r"), "en-us", "power-bi/guidance") == Path(
        "r/en-us/power-bi/guidance.json"
    )


def test_serializacao_tem_ordem_e_indentacao_fixas_e_volta_igual():
    retrato = Retrato(
        secao="dax",
        idioma="en-us",
        url="u",
        baixado_em=HOJE,
        itens=[ItemToc(href="a", titulo="Á")],
    )
    texto = serializar_retrato(retrato)
    assert texto == (
        '{\n  "secao": "dax",\n  "idioma": "en-us",\n  "url": "u",\n'
        '  "baixado_em": "2026-10-09",\n  "itens": [\n    {\n'
        '      "href": "a",\n      "titulo": "Á"\n    }\n  ]\n}\n'
    )
    assert Retrato.model_validate_json(texto) == retrato


TOC_MINIMO = {"items": [{"href": "pagina", "toc_title": "Página"}]}


def _buscador(falhar_em=None, respostas=None):
    chamadas = []

    def buscar(url):
        chamadas.append(url)
        if url == falhar_em:
            raise ErroDeRetrato(f"{url}: HTTP 500")
        if respostas and url in respostas:
            return respostas[url]
        return json.dumps(TOC_MINIMO).encode("utf-8")

    return buscar, chamadas


def test_baixa_os_dez_retratos_e_grava_listagem_e_bruto(tmp_path):
    buscar, _ = _buscador()
    retratos = baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert len(retratos) == len(SECOES) * len(IDIOMAS) == 10
    for secao in SECOES:
        for idioma in IDIOMAS:
            versionado = caminho_do_retrato(tmp_path / "tocs", idioma, secao.caminho)
            retrato = Retrato.model_validate_json(versionado.read_text(encoding="utf-8"))
            assert retrato.baixado_em == HOJE
            assert retrato.url == url_do_toc(secao.caminho, idioma)
            assert retrato.itens == [ItemToc(href="pagina", titulo="Página")]
            bruto = caminho_do_retrato(tmp_path / "bruto", idioma, secao.caminho)
            assert json.loads(bruto.read_bytes()) == TOC_MINIMO


def test_retrato_versionado_tem_fim_de_linha_lf(tmp_path):
    buscar, _ = _buscador()
    baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    arquivo = caminho_do_retrato(tmp_path / "tocs", "en-us", "dax")
    assert b"\r\n" not in arquivo.read_bytes()


def test_falha_no_meio_preserva_os_retratos_antigos(tmp_path):
    pasta = tmp_path / "tocs"
    antigo = caminho_do_retrato(pasta, "en-us", "dax")
    antigo.parent.mkdir(parents=True)
    antigo.write_text("ANTIGO", encoding="utf-8")
    buscar, _ = _buscador(falhar_em=url_do_toc("powerquery-m", "pt-br"))

    with pytest.raises(ErroDeRetrato, match="powerquery-m"):
        baixar_retratos(buscar, HOJE, pasta, tmp_path / "bruto")

    assert antigo.read_text(encoding="utf-8") == "ANTIGO"
    assert [p.name for p in pasta.rglob("*.json")] == ["dax.json"]
    assert not (tmp_path / "bruto").exists()


def test_json_invalido_aborta_nomeando_a_url(tmp_path):
    url = url_do_toc("dax", "en-us")
    buscar, _ = _buscador(respostas={url: b"<html>erro</html>"})
    with pytest.raises(ErroDeRetrato, match="JSON inválido") as erro:
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert url in str(erro.value)
    assert not (tmp_path / "tocs").exists()


def test_toc_sem_items_aborta(tmp_path):
    url = url_do_toc("dax", "pt-br")
    buscar, _ = _buscador(respostas={url: b'{"outra": 1}'})
    with pytest.raises(ErroDeRetrato, match="items"):
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto")
    assert not (tmp_path / "tocs").exists()


def test_links_do_sqlbi_sao_verificados_sem_gravar_nada(tmp_path):
    link = "https://www.sqlbi.com/articles/mark-as-date-table/"
    buscar, chamadas = _buscador()
    baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto", [link])
    assert link in chamadas
    assert not any("sqlbi" in str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))


def test_link_do_sqlbi_morto_aborta_antes_de_gravar(tmp_path):
    link = "https://www.sqlbi.com/articles/morto/"
    buscar, _ = _buscador(falhar_em=link)
    with pytest.raises(ErroDeRetrato, match="morto"):
        baixar_retratos(buscar, HOJE, tmp_path / "tocs", tmp_path / "bruto", [link])
    assert not (tmp_path / "tocs").exists()


def test_buscar_padrao_identifica_o_projeto_e_converte_erro_http(monkeypatch):
    pedidos = []

    def urlopen_falso(pedido, timeout):
        pedidos.append((pedido, timeout))
        raise urllib.error.HTTPError(pedido.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato, match="HTTP 404"):
        buscar_padrao("https://learn.microsoft.com/en-us/dax/toc.json")

    pedido, timeout = pedidos[0]
    assert pedido.get_header("User-agent") == tocs.USER_AGENT
    assert tocs.USER_AGENT == "powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)"
    assert timeout == 30


def test_buscar_padrao_converte_erro_de_rede(monkeypatch):
    def urlopen_falso(pedido, timeout):
        raise urllib.error.URLError("sem rota")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
    with pytest.raises(ErroDeRetrato, match="sem rota"):
        buscar_padrao("https://learn.microsoft.com/en-us/dax/toc.json")
