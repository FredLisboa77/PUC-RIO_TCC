"""Extração do texto estruturado. HTML sintético, escrito à mão imitando a
estrutura medida no Learn; nenhuma página real entra no repositório."""

import hashlib
from datetime import UTC, datetime

import pytest

from rag import extracao as modulo_extracao
from rag.coleta import RegistroColeta, anexar_registro, caminho_da_pagina
from rag.extracao import (
    VERSAO_EXTRATOR,
    Bloco,
    ErroDeExtracao,
    PaginaExtraida,
    caminho_do_texto,
    extrair,
    extrair_tudo,
    main,
    resumo_extracao,
)

URL = "https://learn.microsoft.com/en-us/dax/calculate-function-dax"


def pagina(corpo: str, h1: str = '<h1 id="calculate">CALCULATE</h1>') -> str:
    return f"""<html><body><main id="main" class="layout-body-main">
<nav id="center-doc-outline"><h2 id="ms--in-this-article">In this article</h2></nav>
<div><div class="content">{h1}</div>
<div id="article-metadata">metadados</div>
<div class="content">{corpo}</div></div>
<h2 id="ms--feedback">Feedback</h2>
<h2 id="ms--additional-resources-mobile-heading">Additional resources</h2>
</main></body></html>"""


CORPO = """
<p>Evaluates an expression in a modified <a href="x">filter context</a>.</p>
<div class="NOTE"><p>Note</p><p>There's also the CALCULATETABLE function.</p></div>
<h2 id="syntax">Syntax</h2>
<pre><code class="lang-dax">CALCULATE(&lt;expression&gt;[, &lt;filter1&gt;])
  -- indentação preservada</code></pre>
<h3 id="parameters">Parameters</h3>
<table><tr><th>Term</th><th>Definition</th></tr><tr><td>expression</td><td>The expression to be evaluated.</td></tr></table>
<ul><li>Boolean filter expressions</li><li>Table filter expression</li></ul>
<p><img src="x.png" alt="diagrama"></p>
<h2 id="related-content">Related content</h2>
<ul><li><a href="y">CALCULATETABLE</a></li></ul>
<h3 id="mais-links">Mais links</h3>
<p>também fora</p>
<h2 id="remarks">Remarks</h2>
<p>Remarks text.</p>
"""


def test_identificacao_e_titulo_real():
    resultado = extrair(pagina(CORPO), "learn:dax/calculate-function-dax", URL)
    assert resultado.versao_extrator == VERSAO_EXTRATOR
    assert (resultado.id, resultado.url, resultado.titulo) == (
        "learn:dax/calculate-function-dax",
        URL,
        "CALCULATE",
    )


def test_secoes_com_ancora_nivel_e_caminho():
    secoes = extrair(pagina(CORPO), "x:y", URL).secoes
    assert [(s.ancora, s.nivel, s.caminho) for s in secoes] == [
        ("calculate", 1, "CALCULATE"),
        ("syntax", 2, "Syntax"),
        ("parameters", 3, "Syntax › Parameters"),
        ("remarks", 2, "Remarks"),
    ]


def test_cada_tipo_de_bloco():
    secoes = {s.ancora: s for s in extrair(pagina(CORPO), "x:y", URL).secoes}
    assert secoes["calculate"].blocos == [
        Bloco(tipo="paragrafo", texto="Evaluates an expression in a modified filter context ."),
        Bloco(tipo="nota", texto="There's also the CALCULATETABLE function.", rotulo="Note"),
    ]
    assert secoes["parameters"].blocos == [
        Bloco(tipo="tabela", texto="Term | Definition\nexpression | The expression to be evaluated."),
        Bloco(tipo="lista", texto="- Boolean filter expressions\n- Table filter expression"),
    ]


def test_codigo_e_preservado_verbatim_com_linguagem():
    (bloco,) = {s.ancora: s for s in extrair(pagina(CORPO), "x:y", URL).secoes}["syntax"].blocos
    assert bloco.tipo == "codigo"
    assert bloco.linguagem == "dax"
    assert bloco.texto == "CALCULATE(<expression>[, <filter1>])\n  -- indentação preservada"


def test_secao_de_navegacao_sai_com_as_subsecoes_e_a_seguinte_volta():
    resultado = extrair(pagina(CORPO), "x:y", URL)
    ancoras = [s.ancora for s in resultado.secoes]
    assert "related-content" not in ancoras and "mais-links" not in ancoras
    assert "remarks" in ancoras
    assert resultado.secoes_excluidas == ["related-content"]
    texto = " ".join(b.texto for s in resultado.secoes for b in s.blocos)
    assert "também fora" not in texto
    assert "In this article" not in texto and "Feedback" not in texto


def test_imagem_some_e_texto_de_link_fica():
    texto = " ".join(b.texto for s in extrair(pagina(CORPO), "x:y", URL).secoes for b in s.blocos)
    assert "diagrama" not in texto
    assert "filter context" in texto


def test_secao_sem_bloco_nao_entra():
    corpo = '<h2 id="vazia">Vazia</h2><h3 id="filha">Filha</h3><p>texto</p>'
    secoes = extrair(pagina(corpo), "x:y", URL).secoes
    assert [(s.ancora, s.caminho) for s in secoes] == [("filha", "Vazia › Filha")]


def test_pagina_sem_h1_e_erro_nomeado():
    with pytest.raises(ErroDeExtracao, match="learn:dax/x.*H1"):
        extrair("<html><body><main id='main'><p>x</p></main></body></html>", "learn:dax/x", URL)


def test_pagina_sem_texto_e_erro_nomeado():
    with pytest.raises(ErroDeExtracao, match="sem texto"):
        extrair(pagina('<h2 id="a">A</h2>', h1='<h1 id="t">T</h1>'), "learn:dax/x", URL)


def test_mesma_entrada_mesma_saida():
    assert extrair(pagina(CORPO), "x:y", URL) == extrair(pagina(CORPO), "x:y", URL)


AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


def _coletada(tmp_path, id_fonte, html, **meta):
    arquivo = caminho_da_pagina(tmp_path / "paginas", id_fonte)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(html, encoding="utf-8")
    anexar_registro(
        tmp_path / "coleta.jsonl",
        RegistroColeta(
            id=id_fonte,
            url=URL,
            situacao="ok",
            acessado_em=AGORA,
            tamanho=len(html),
            sha256=hashlib.sha256(html.encode()).hexdigest(),
            **meta,
        ),
    )


def _extrair_tudo(tmp_path, titulos=None):
    return extrair_tudo(
        arquivo_registro=tmp_path / "coleta.jsonl",
        pasta_paginas=tmp_path / "paginas",
        pasta_textos=tmp_path / "textos",
        titulos_do_catalogo=titulos or {},
    )


def test_extrai_toda_pagina_ok_com_metadados(tmp_path):
    _coletada(tmp_path, "learn:dax/calculate-function-dax", pagina(CORPO), updated_at="2026-08-04T22:03:00Z")
    resumo = _extrair_tudo(tmp_path, {"learn:dax/calculate-function-dax": "CALCULATE"})
    assert resumo.extraidas == 1 and resumo.erros == [] and resumo.titulos_diferentes == 0
    destino = caminho_do_texto(tmp_path / "textos", "learn:dax/calculate-function-dax")
    assert destino.suffix == ".json"
    salvo = PaginaExtraida.model_validate_json(destino.read_text(encoding="utf-8"))
    assert salvo.metadados["updated_at"] == "2026-08-04T22:03:00Z"
    assert salvo.metadados["acessado_em"] == AGORA.isoformat()
    assert resumo.excluidas["related-content"] == 1


def test_erro_de_uma_pagina_nao_para_as_outras(tmp_path):
    _coletada(tmp_path, "learn:dax/sem-h1", "<html><body><main id='main'><p>x</p></main></body></html>")
    _coletada(tmp_path, "learn:dax/boa", pagina(CORPO))
    resumo = _extrair_tudo(tmp_path)
    assert resumo.extraidas == 1
    assert len(resumo.erros) == 1 and "learn:dax/sem-h1" in resumo.erros[0]


def test_html_apagado_depois_da_coleta_vira_erro_nomeado(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/a").unlink()
    resumo = _extrair_tudo(tmp_path)
    assert resumo.extraidas == 0
    assert "rag.coleta" in resumo.erros[0]


def test_titulo_diferente_do_catalogo_e_contado_nao_e_erro(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    resumo = _extrair_tudo(tmp_path, {"learn:dax/a": "Introduction"})
    assert resumo.extraidas == 1 and resumo.titulos_diferentes == 1


def test_sem_nada_coletado_falha_indicando_a_coleta(tmp_path):
    with pytest.raises(ErroDeExtracao, match="rag.coleta"):
        _extrair_tudo(tmp_path)


def test_resumo_da_extracao(tmp_path):
    _coletada(tmp_path, "learn:dax/a", pagina(CORPO))
    texto = resumo_extracao(_extrair_tudo(tmp_path))
    assert "Extraídas: 1" in texto
    assert "related-content: 1" in texto


def test_main_sem_coleta_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_extracao, "ARQUIVO_REGISTRO", tmp_path / "nao-existe.jsonl")
    monkeypatch.setattr(modulo_extracao, "ARQUIVO_FONTES", tmp_path / "nao-existe.yaml")
    assert main([]) == 1
    assert "rag.coleta" in capsys.readouterr().err
