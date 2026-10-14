"""Rodada avaliada: id estável, impressão digital, auditoria e leitura."""

import pytest

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.rodada import (
    auditar, carregar_rodada, id_do_achado, impressao, projetos_da_avaliacao,
)
from conftest import escrever_pbip, modelo_tmsl, tabela
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.analise.cache import ClienteComCache
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, contexto, gabarito, meta, trecho_de_contexto


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    return registro


def _gerado(explicacao="e", recomendacao="Use uma tabela de datas própria.") -> AchadoEnriquecido:
    return AchadoEnriquecido(
        achado=achado(objeto="T"), contexto=contexto(2),
        geracao=Geracao(explicacao=explicacao, recomendacao=recomendacao, citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m",
    )


def test_id_e_impressao():
    item = _gerado()
    assert id_do_achado("P1_X", item) == "P1_X|MOD-001|T"
    assert impressao(item) == impressao(_gerado()) and len(impressao(item)) == 64
    assert impressao(item) != impressao(_gerado(explicacao="outra"))
    assert impressao(AchadoEnriquecido.so_regras(achado())) is None


def test_projetos_da_avaliacao_so_p1_a_p7(tmp_path):
    for nome in ["P1_A", "P7_B", "P8_contoso", "P9_x", "outra"]:
        (tmp_path / nome).mkdir()
    (tmp_path / "P2_arquivo.txt").write_text("x", encoding="utf-8")
    assert [p.name for p in projetos_da_avaliacao(tmp_path)] == ["P1_A", "P7_B"]


def test_auditar_grava_um_json_por_projeto_e_conta_o_cache(tmp_path):
    tabelas_por_projeto = {"P1_A": ["T1", "T2"], "P2_B": ["U1", "U2"]}
    pastas = [escrever_pbip(tmp_path / n, nome=n, model_bim=modelo_tmsl([tabela(t) for t in ts]))
              for n, ts in tabelas_por_projeto.items()]
    comum = dict(base=base_padrao(), registro=_registro(), gabaritos={"MOD-001": gabarito()})
    llm = ClienteComCache(LLMFalso(), tmp_path / "cache")
    primeiro = auditar(pastas, tmp_path / "rodada", llm=llm, **comum)
    assert (primeiro.projetos, primeiro.achados, primeiro.gerados, primeiro.fora_do_cache) == (2, 4, 4, 4)
    segundo = auditar(pastas, tmp_path / "rodada", llm=ClienteComCache(LLMFalso(), tmp_path / "cache"), **comum)
    assert segundo.fora_do_cache == 0
    rodada = carregar_rodada(tmp_path / "rodada")
    assert sorted(rodada) == ["P1_A|MOD-001|T1", "P1_A|MOD-001|T2", "P2_B|MOD-001|U1", "P2_B|MOD-001|U2"]
    assert rodada["P2_B|MOD-001|U1"].projeto == "P2_B"


def test_carregar_rodada_ausente_ou_ilegivel(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="nenhuma auditoria"):
        carregar_rodada(tmp_path / "nao-existe")
    (tmp_path / "P1_A.json").write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ErroDeAvaliacao, match="P1_A.json"):
        carregar_rodada(tmp_path)


def test_impressao_cobre_citacoes_e_trechos_citados():
    base = _gerado()
    outra_citacao = base.model_copy(update={"geracao": base.geracao.model_copy(update={"citacoes": [2]})})
    assert impressao(outra_citacao) != impressao(base)
    ctx = contexto(2)
    ctx[0] = trecho_de_contexto(1, texto="Outro texto do trecho citado.", origem="ancora")
    outro_trecho = base.model_copy(update={"contexto": ctx})
    assert impressao(outro_trecho) != impressao(base)
    outro_url = contexto(2)
    outro_url[0] = outro_url[0].model_copy(update={"ancora": "outra"})
    assert impressao(base.model_copy(update={"contexto": outro_url})) != impressao(base)
