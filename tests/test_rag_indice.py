"""Índice do vencedor: arquivos e falhas, sem modelo nem base real."""

import pytest

from rag.indice import ErroDeIndice, carregar_buscador, configuracao_do_indice, construir, resultado_mais_recente


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
    monkeypatch.setattr(modulo_indice, "construir", lambda busca=None: _decisao("completo").vencedora)
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


from rag.indice import BaseRag


def _t(id_pagina, texto, *, parte=1, ancora="s"):
    return TrechoIndexado(
        id=f"{id_pagina}#{ancora}/{parte}", id_pagina=id_pagina, url="u", titulo_pagina="T",
        ancora=ancora, caminho="S", texto=texto, texto_indexado=texto,
    )


def _config(busca):
    return Configuracao(chunking="secao", cabecalho=False, busca=busca, corpus="completo")


def test_base_bm25_nao_carrega_embedder_nem_chroma(tmp_path, monkeypatch):
    pasta = tmp_path / "i"
    pasta.mkdir()
    trechos = [_t("learn:p", "auto date time"), _t("learn:q", "divide by zero"), _t("learn:r", "star schema")]
    (pasta / "trechos.jsonl").write_text("".join(t.model_dump_json() + "\n" for t in trechos), encoding="utf-8")
    (pasta / "config.json").write_text(_config("bm25").model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(modulo_indice, "EmbedderBge", lambda: pytest.fail("BM25 não usa embedder"))
    monkeypatch.setattr(modulo_indice, "_cliente", lambda pasta: pytest.fail("BM25 não usa o Chroma"))

    base = BaseRag.carregar(pasta_indice=pasta, pasta_chroma=tmp_path / "c")

    achados = base.buscar("divide", 1)
    assert [t.id for t in achados] == ["learn:q#s/1"]
    assert (achados[0].url, achados[0].titulo_pagina) == ("u", "T")


def test_trecho_ancora_pega_a_parte_da_secao_com_a_frase_marca():
    base = BaseRag(_config("bm25"), [
        _t("learn:p", "intro text"),
        _t("learn:p", "You should disable the Auto  date/time option.", parte=2),
        _t("learn:q", "disable the auto date/time option"),
    ])
    assert base.trecho_ancora("learn:p", "s", "disable the auto date/time option").id == "learn:p#s/2"


def test_trecho_ancora_de_secao_ausente_falha():
    base = BaseRag(_config("bm25"), [_t("learn:p", "texto")])
    with pytest.raises(ErroDeIndice, match="ausente"):
        base.trecho_ancora("learn:sumiu", "s", "texto")


def test_trecho_ancora_sem_a_frase_marca_falha():
    base = BaseRag(_config("bm25"), [_t("learn:p", "outro texto")])
    with pytest.raises(ErroDeIndice, match="frase-marca"):
        base.trecho_ancora("learn:p", "s", "disable the option")


import json as _json



def _complementares(pasta, vencedora, data="2026-10-13"):
    (pasta / f"complementares-{data}.json").write_text(
        _json.dumps({"decisao": {"vencedora": vencedora, "justificativa": "x"}}), encoding="utf-8"
    )


def test_sem_busca_a_configuracao_e_a_vencedora_de_11_10(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    configuracao, origem = configuracao_do_indice(tmp_path, None)
    assert configuracao.busca == "bm25" and origem is None


def test_busca_que_casa_com_a_decisao_troca_so_a_busca(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    _complementares(tmp_path, "hibrida")
    configuracao, origem = configuracao_do_indice(tmp_path, "hibrida")
    assert (configuracao.busca, configuracao.chunking, configuracao.cabecalho, configuracao.corpus) == (
        "hibrida", "secao", False, "completo",
    )
    assert origem == "complementares-2026-10-13.json"


def test_busca_que_nao_casa_com_a_decisao_e_recusada(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    _complementares(tmp_path, "bm25")
    with pytest.raises(ErroDeIndice, match="decisão mais recente"):
        configuracao_do_indice(tmp_path, "densa")


def test_busca_sem_resultado_de_complementares_e_recusada(tmp_path):
    gravar_resultado(tmp_path / "recuperacao-2026-10-11.json", [], _decisao("completo"), {})
    with pytest.raises(ErroDeIndice, match="rag.complementares medir"):
        configuracao_do_indice(tmp_path, "hibrida")


def test_colecao_usa_cosseno_e_busca_hnsw_ampla(tmp_path):
    """Depois de trocar para densa ou combinada, o Chroma precisa reproduzir a busca medida
    (produto escalar exato sobre vetores normalizados): espaço cosseno e ef alto."""
    colecao = modulo_indice.criar_colecao(modulo_indice._cliente(tmp_path / "c"))
    hnsw = colecao.configuration.get("hnsw")
    assert hnsw["space"] == "cosine"
    assert hnsw["ef_search"] >= 200 and hnsw["ef_construction"] >= 200
