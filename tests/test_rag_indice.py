"""Índice do vencedor: arquivos e falhas, sem modelo nem base real."""

import pytest

from rag.indice import ErroDeIndice, carregar_buscador, construir, resultado_mais_recente


def test_resultado_mais_recente_pega_o_ultimo_por_data(tmp_path):
    (tmp_path / "recuperacao-2026-10-11.json").write_text("{}", encoding="utf-8")
    (tmp_path / "recuperacao-2026-10-12.json").write_text("{}", encoding="utf-8")
    (tmp_path / "spike_llm.json").write_text("{}", encoding="utf-8")
    assert resultado_mais_recente(tmp_path).name == "recuperacao-2026-10-12.json"


def test_sem_resultado_de_medicao_falha_indicando_a_medicao(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.medicao"):
        resultado_mais_recente(tmp_path)


def test_construir_sem_resultado_falha(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.medicao"):
        construir(pasta_resultados=tmp_path, pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")


def test_carregar_sem_indice_falha_indicando_construir(tmp_path):
    with pytest.raises(ErroDeIndice, match="rag.indice construir"):
        carregar_buscador(pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")
