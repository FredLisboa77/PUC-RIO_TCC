"""Fumaça da interface com o AppTest do Streamlit: LLM falso, PBIP sintético."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app import execucao
from conftest import coluna, escrever_pbip, modelo_tmsl, relacionamento, tabela
from core import auditoria
from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.registry import Registro
from core.rules.runner import avaliar
from core.rules.todas import REGISTRO
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta

ARQUIVO_APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(execucao, "carregar_base", base_padrao)
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: LLMFalso())
    st.cache_resource.clear()
    return AppTest.from_file(ARQUIVO_APP, default_timeout=60)


def _pbip_bidirecional(raiz):
    """MOD-002 marca o relacionamento bidirecional com as regras reais."""
    return escrever_pbip(raiz, model_bim=modelo_tmsl(
        tabelas=[
            tabela("DimProduct", colunas=[coluna("SubKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey", bidirecional=True)],
    ))


def _gravar_resultado_salvo(raiz) -> Path:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    pbip = escrever_pbip(raiz / "origem", model_bim=modelo_tmsl([tabela("LocalDateTable_1")]))
    resultado = auditoria.run_audit(
        pbip, llm=LLMFalso(), base=base_padrao(), registro=registro, gabaritos={"MOD-001": gabarito()},
    )
    return auditoria.gravar(resultado)


def test_abre_sem_resultado_e_sem_erro(app):
    app.run()
    assert not app.exception
    assert app.session_state["resultado"] is None


def test_abrir_resultado_salvo_mostra_painel_e_tabela(app, tmp_path):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()
    assert not app.exception
    assert app.session_state["resultado"].projeto == "Minimal"
    textos = " ".join(m.value for m in app.markdown)
    assert "1 de 1 regras executadas" in textos
    assert len(app.dataframe) == 1


def test_so_regras_roda_ponta_a_ponta(app, tmp_path):
    pbip = _pbip_bidirecional(tmp_path)
    esperados = len(avaliar(ler_modelo(abrir_pbip(pbip).model_bim), REGISTRO).achados)
    assert esperados >= 1
    app.run()
    app.text_input(key="pasta").input(str(pbip)).run()
    app.radio(key="modo").set_value("so_regras").run()
    app.button(key="auditar").click().run()
    assert not app.exception
    resultado = app.session_state["resultado"]
    assert (resultado.modo, len(resultado.achados)) == ("so_regras", esperados)
    assert app.session_state["executando"] is False
    assert list((tmp_path / "saida").glob("*-so-regras.json"))


def test_erro_de_pbip_vira_mensagem(app, tmp_path):
    app.run()
    app.text_input(key="pasta").input(str(tmp_path / "nao-existe")).run()
    app.radio(key="modo").set_value("so_regras").run()
    app.button(key="auditar").click().run()
    assert not app.exception
    assert any("não é um projeto PBIP válido" in e.value for e in app.error)
    assert app.session_state["executando"] is False


def test_erro_inesperado_vira_mensagem_e_destrava(app, tmp_path, monkeypatch):
    """Review Focus 1: um bug no pipeline não pode travar os controles."""
    def quebra(*args, **kwargs):
        raise KeyError("bug")

    monkeypatch.setattr(execucao, "executar", quebra)
    app.run()
    app.text_input(key="pasta").input(str(tmp_path)).run()
    app.button(key="auditar").click().run()
    assert not app.exception
    assert any("Erro inesperado" in e.value for e in app.error)
    assert app.session_state["executando"] is False


def test_json_invalido_mantem_o_resultado_anterior(app, tmp_path):
    """Review Focus 4."""
    caminho = _gravar_resultado_salvo(tmp_path)
    (caminho.parent / "quebrado.json").write_text("{ quebrado", encoding="utf-8")
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()
    app.selectbox(key="salvo").set_value(str(caminho.parent / "quebrado.json")).run()
    app.button(key="abrir").click().run()
    assert not app.exception
    assert any("não é um resultado de auditoria" in e.value for e in app.error)
    assert app.session_state["resultado"].projeto == "Minimal"


def test_durante_a_auditoria_o_resultado_anterior_fica_desabilitado(app, tmp_path, monkeypatch):
    """Revisão final: um clique num filtro do resultado anterior durante a auditoria
    reexecutaria o script e mataria a auditoria em silêncio (spec 3.1)."""
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()

    def falha(*args, **kwargs):
        raise execucao.ErroParaUsuario("parou")

    # Sem o rerun, o run de execução termina com a tela que o usuário vê durante a auditoria.
    monkeypatch.setattr(st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(execucao, "executar", falha)
    app.text_input(key="pasta").input(str(tmp_path)).run()
    app.button(key="auditar").click().run()
    assert not app.exception
    assert app.multiselect and all(m.disabled for m in app.multiselect)
    traducao = [b for b in app.button if (b.key or "").startswith("traduzir")]
    assert traducao and all(b.disabled for b in traducao)


def test_resultado_aberto_oferece_html_e_pdf(app, tmp_path, monkeypatch):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()
    assert not app.exception
    assert app.get("download_button")  # "Baixar relatório HTML"
    monkeypatch.setattr(execucao, "relatorio_pdf", lambda resultado, tecnico: b"%PDF-ok")
    app.button(key="gerar_pdf").click().run()
    assert not app.exception
    assert app.session_state["pdf"][1] == b"%PDF-ok"


def test_falha_do_pdf_vira_mensagem(app, tmp_path, monkeypatch):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()

    def falha(resultado, tecnico):
        raise execucao.ErroParaUsuario("PDF indisponível: Edge ausente")

    monkeypatch.setattr(execucao, "relatorio_pdf", falha)
    app.button(key="gerar_pdf").click().run()
    assert not app.exception
    assert any("Edge ausente" in e.value for e in app.error)


def _gravar_resultado(raiz, objetos) -> Path:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=o) for o in objetos])
    pbip = escrever_pbip(raiz / "origem", model_bim=modelo_tmsl([tabela("T")]))
    resultado = auditoria.run_audit(
        pbip, llm=LLMFalso(), base=base_padrao(), registro=registro, gabaritos={"MOD-001": gabarito()},
    )
    return auditoria.gravar(resultado)


def _abrir_salvo(app, caminho):
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()


def test_traducao_usa_o_modelo_do_resultado(app, tmp_path, monkeypatch):
    usados = []
    monkeypatch.setattr(execucao, "traduzir", lambda texto, modelo, cache=False: usados.append(modelo) or "ok")
    _abrir_salvo(app, _gravar_resultado_salvo(tmp_path))
    app.text_input(key="modelo").input("outro-modelo").run()
    next(b for b in app.button if (b.key or "").startswith("traduzir")).click().run()
    assert usados == ["llm-falso"]


def test_objeto_com_markdown_aparece_escapado(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado(tmp_path, ["Tabela_*a*"]))
    assert any("Tabela\_\*a\*" in c.value for c in app.caption)


def test_resultado_sem_achados_diz_nenhum_achado(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado(tmp_path, []))
    assert any(i.value == "Nenhum achado." for i in app.info)


def test_filtros_com_placeholder_em_portugues(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado_salvo(tmp_path))
    assert app.multiselect and all(m.placeholder == "todas" for m in app.multiselect)


def test_detalhe_do_achado_do_cache_diz_que_veio_do_cache(app, tmp_path):
    caminho = _gravar_resultado_salvo(tmp_path)
    resultado = auditoria.ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8"))
    do_cache = resultado.model_copy(update={"achados": [a.model_copy(update={"do_cache": True}) for a in resultado.achados]})
    caminho.write_text(do_cache.model_dump_json(), encoding="utf-8")
    _abrir_salvo(app, caminho)
    textos = " ".join(m.value for m in app.markdown) + " ".join(c.value for c in app.caption)
    assert "resposta guardada no cache" in textos
