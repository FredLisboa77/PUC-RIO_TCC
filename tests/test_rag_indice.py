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


from rag import indice as modulo_indice
from rag.medicao import Configuracao, Decisao, gravar_resultado


def _decisao(corpus):
    return Decisao(
        vencedora=Configuracao(chunking="secao", cabecalho=False, busca="bm25", corpus=corpus),
        empatadas=[],
        justificativa="x",
    )


def test_construir_recusa_corpus_que_nao_seja_o_completo(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-12.json", [], _decisao("guidance"), {})
    with pytest.raises(ErroDeIndice, match="corpus guidance"):
        construir(pasta_resultados=tmp_path, pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")


def test_carregar_recusa_indice_de_outro_corpus(tmp_path):
    pasta = tmp_path / "i"
    pasta.mkdir()
    (pasta / "config.json").write_text(_decisao("guidance").vencedora.model_dump_json(), encoding="utf-8")
    with pytest.raises(ErroDeIndice, match="corpus guidance"):
        carregar_buscador(pasta_indice=pasta, pasta_chroma=tmp_path / "c")


def test_resumo_do_comando_imprime_no_console_padrao_do_windows(monkeypatch, capsys):
    monkeypatch.setattr(modulo_indice, "construir", lambda: _decisao("completo").vencedora)
    assert modulo_indice.main(["construir"]) == 0
    capsys.readouterr().out.encode("cp1252")


import numpy as np

from rag.busca import IndiceBm25, criar_buscador
from rag.chunking import TrechoIndexado


class EmbedderFixo:
    nome = "fixo"

    def vetores(self, textos):
        raise AssertionError("carregar_buscador não recalcula vetores")

    def vetor_consulta(self, texto):
        return np.array([1.0, 0.2, 0.0], dtype=np.float32) if "date" in texto else np.array(
            [0.0, 0.3, 1.0], dtype=np.float32
        )


def _indice_sintetico(tmp_path, busca):
    """Escreve trechos, config e uma coleção Chroma como `construir` faria."""
    textos = ["auto date time", "divide by zero", "star schema tables", "date table mark", "relationship filter"]
    trechos = [
        TrechoIndexado(
            id=f"learn:p{i}#s/1", id_pagina=f"learn:p{i}", url="u", titulo_pagina="T",
            ancora="s", caminho="S", texto=t, texto_indexado=t,
        )
        for i, t in enumerate(textos)
    ]
    rng = np.random.default_rng(7)
    vetores = rng.normal(size=(len(trechos), 3)).astype(np.float32)
    vetores /= np.linalg.norm(vetores, axis=1, keepdims=True)
    pasta = tmp_path / "i"
    pasta.mkdir()
    (pasta / "trechos.jsonl").write_text("".join(t.model_dump_json() + "\n" for t in trechos), encoding="utf-8")
    configuracao = Configuracao(chunking="secao", cabecalho=False, busca=busca, corpus="completo")
    (pasta / "config.json").write_text(configuracao.model_dump_json(), encoding="utf-8")
    colecao = modulo_indice._cliente(tmp_path / "c").create_collection(modulo_indice.COLECAO)
    colecao.add(ids=[t.id for t in trechos], embeddings=vetores.tolist(), documents=textos)
    return trechos, vetores


@pytest.mark.parametrize("busca", ["densa", "bm25", "hibrida"])
def test_carregar_buscador_reproduz_a_busca_em_memoria(tmp_path, busca):
    trechos, vetores = _indice_sintetico(tmp_path, busca)
    embedder = EmbedderFixo()
    do_indice = carregar_buscador(embedder, pasta_indice=tmp_path / "i", pasta_chroma=tmp_path / "c")
    em_memoria = criar_buscador(
        busca, trechos, vetores=vetores, embedder=embedder,
        indice_bm25=IndiceBm25([t.texto_indexado for t in trechos]),
    )
    for consulta in ("auto date", "star schema", "divide"):
        assert do_indice(consulta, 3) == em_memoria(consulta, 3), (busca, consulta)
