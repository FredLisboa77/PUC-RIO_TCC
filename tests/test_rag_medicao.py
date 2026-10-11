"""Grade, oráculo, medição e regra de decisão, sobre dados sintéticos."""

import numpy as np
import pytest

from rag.avaliacao import ConjuntoAvaliacao, Consulta, Gabarito, Metricas
from rag.chunking import TrechoIndexado
from rag.medicao import (
    GRADE,
    MARGEM,
    Configuracao,
    ResultadoConfiguracao,
    decidir,
    formatar_tabela,
    medir,
    verificar_oraculo,
)


def test_grade_tem_24_combinacoes_distintas():
    assert len(GRADE) == 24
    assert len({c.nome for c in GRADE}) == 24
    assert {c.variante for c in GRADE} == {"secao-sem", "secao-com", "janela-sem", "janela-com"}


def test_complexidade():
    assert Configuracao(chunking="secao", cabecalho=False, busca="densa", corpus="completo").complexidade == 0
    assert Configuracao(chunking="secao", cabecalho=False, busca="bm25", corpus="completo").complexidade == 0
    assert Configuracao(chunking="janela", cabecalho=True, busca="hibrida", corpus="completo").complexidade == 3


def _metricas(acerto5, mrr=0.5):
    return Metricas(
        consultas=9,
        acerto={1: acerto5 / 2, 3: acerto5, 5: acerto5, 10: acerto5},
        precisao={1: 0.1, 3: 0.1, 5: 0.1, 10: 0.1},
        mrr=mrr,
    )


def _resultado(chunking="secao", cabecalho=False, busca="densa", corpus="completo", acerto5=0.5, mrr=0.5):
    m = _metricas(acerto5, mrr)
    return ResultadoConfiguracao(
        configuracao=Configuracao(chunking=chunking, cabecalho=cabecalho, busca=busca, corpus=corpus),
        macro=m,
        micro=m,
        por_tipo={"regra": m},
        por_regra={"R1": m},
        erros=[],
    )


def test_vence_a_maior_macro_acerto5_quando_a_diferenca_e_grande():
    decisao = decidir([_resultado(acerto5=4 / 9), _resultado(busca="hibrida", acerto5=6 / 9)])
    assert decisao.vencedora.busca == "hibrida"


def test_dentro_da_margem_vence_a_mais_simples():
    decisao = decidir([_resultado(acerto5=5 / 9), _resultado(busca="hibrida", cabecalho=True, acerto5=5.9 / 9)])
    assert decisao.vencedora.busca == "densa"
    assert len(decisao.empatadas) == 2


def test_diferenca_de_exatamente_uma_regra_nao_e_empate():
    melhor = sum([1.0] * 6 + [0.0] * 3) / 9
    outra = sum([1.0] * 5 + [0.0] * 4) / 9
    assert melhor - outra == pytest.approx(MARGEM)
    decisao = decidir([_resultado(acerto5=outra), _resultado(busca="hibrida", acerto5=melhor)])
    assert decisao.vencedora.busca == "hibrida"


def test_desempate_por_mrr_e_depois_pela_ordem_fixa():
    por_mrr = decidir([_resultado(busca="densa", acerto5=0.5, mrr=0.4), _resultado(busca="bm25", acerto5=0.5, mrr=0.6)])
    assert por_mrr.vencedora.busca == "bm25"
    por_ordem = decidir([_resultado(busca="bm25", acerto5=0.5), _resultado(busca="densa", acerto5=0.5)])
    assert por_ordem.vencedora.busca == "densa"


def test_corpus_guidance_nunca_vence_sozinho_mas_avisa():
    decisao = decidir([_resultado(acerto5=3 / 9), _resultado(corpus="guidance", acerto5=7 / 9)])
    assert decisao.vencedora.corpus == "completo"
    assert decisao.aviso_corpus is not None and "guidance" in decisao.aviso_corpus


def test_sem_aviso_quando_guidance_nao_supera_pela_margem():
    assert decidir([_resultado(acerto5=5 / 9), _resultado(corpus="guidance", acerto5=5.5 / 9)]).aviso_corpus is None


def _trecho(texto, pagina="learn:p", ancora="s", n=1):
    return TrechoIndexado(
        id=f"{pagina}#{ancora}/{n}", id_pagina=pagina, url="u", titulo_pagina="T",
        ancora=ancora, caminho="S", texto=texto, texto_indexado=texto,
    )


CONJUNTO = ConjuntoAvaliacao(
    gabaritos=[Gabarito(id_regra="R1", frase_marca="alpha beta", id_pagina="learn:p", ancora="s")],
    consultas=[Consulta(id="REGRA/R1", tipo="regra", id_regra="R1", texto="q")],
)


def test_oraculo_passa_quando_a_frase_esta_inteira_num_trecho_da_pagina():
    assert verificar_oraculo([_trecho("x Alpha  beta y", ancora="outra")], CONJUNTO) == []


def test_oraculo_acusa_frase_partida_ou_em_outra_pagina():
    partida = [_trecho("x alpha", n=1), _trecho("beta y", n=2)]
    assert verificar_oraculo(partida, CONJUNTO) == ["R1"]
    assert verificar_oraculo([_trecho("alpha beta", pagina="learn:outra")], CONJUNTO) == ["R1"]


class EmbedderFixo:
    nome = "fixo"

    def vetores(self, textos):
        raise AssertionError

    def vetor_consulta(self, texto):
        return np.array([1.0, 0.0], dtype=np.float32)


def test_medir_roda_cada_configuracao_da_grade_pedida():
    trechos = [_trecho("alpha beta"), _trecho("other", pagina="learn:q", n=2)]
    vetores = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    variantes = {"secao-sem": trechos}
    grade = [
        Configuracao(chunking="secao", cabecalho=False, busca=b, corpus=c)
        for b in ("densa", "bm25", "hibrida")
        for c in ("completo", "guidance")
    ]
    resultados = medir(
        CONJUNTO,
        trechos=variantes,
        vetores={"secao-sem": vetores},
        embedder=EmbedderFixo(),
        paginas_guidance=frozenset({"learn:q"}),
        grade=grade,
    )
    por_nome = {r.configuracao.nome: r for r in resultados}
    assert len(resultados) == 6
    assert por_nome["secao-sem-densa-completo"].macro.acerto[1] == 1.0
    assert por_nome["secao-sem-densa-guidance"].macro.acerto[10] == 0.0
    assert por_nome["secao-sem-densa-guidance"].erros[0].id == "REGRA/R1"


def test_tabela_marca_a_vencedora():
    resultados = [_resultado(acerto5=5 / 9), _resultado(busca="bm25", acerto5=2 / 9)]
    texto = formatar_tabela(resultados, decidir(resultados))
    assert "secao-sem-densa-completo" in texto and "*" in texto
    assert "0.556" in texto
