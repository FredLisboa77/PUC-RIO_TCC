"""Métricas da rubrica: taxas, recortes, utilizável, descarte e humano × automático."""

import pytest

from avaliacao_geracao.metricas import medir, taxa
from avaliacao_geracao.planilha import LinhaRubrica
from avaliacao_geracao.rodada import ItemDaRodada, id_do_achado, impressao
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.rules.base import RegraMeta
from core.rules.registry import Registro
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto


def _registro() -> Registro:
    registro = Registro()
    for id_regra, categoria in [("MOD-001", "modelagem"), ("DAX-001", "dax")]:
        registro.registrar(RegraMeta(id=id_regra, titulo=id_regra, categoria=categoria, severidade="alta",
                                     url_canonica="https://learn.microsoft.com/x", termos_consulta=("t",),
                                     recomendacao_padrao=RECOMENDACAO_PADRAO), lambda m: [])
    return registro


def _gerado(id_regra, objeto, cita_ancora=True, divergencias=()) -> AchadoEnriquecido:
    return AchadoEnriquecido(
        achado=achado(id_regra, objeto=objeto), contexto=contexto(2),
        geracao=Geracao(explicacao=f"e {objeto}", recomendacao="r", citacoes=[1]),
        situacao="gerado", cita_ancora=cita_ancora, fidelidade=Fidelidade(divergencias=list(divergencias)), modelo="m",
    )


def _cenario():
    itens = [
        _gerado("MOD-001", "A", cita_ancora=True),
        _gerado("MOD-001", "B", cita_ancora=False, divergencias=["42"]),
        _gerado("DAX-001", "C", cita_ancora=True),
        AchadoEnriquecido(achado=achado("MOD-001", objeto="D"), contexto=contexto(1), situacao="sem_fundamentacao",
                          motivo_descarte="json_invalido", modelo="m"),
    ]
    rodada = {id_do_achado("P1", i): ItemDaRodada("P1", i) for i in itens}
    vereditos = {"A": ("sim", "sim", "sim"), "B": ("não", "não", "sim"), "C": ("sim", "sim", "indeterminado")}
    linhas = [
        LinhaRubrica(id=id_do_achado("P1", i), impressao=impressao(i), pertinente=v[0], fiel=v[1],
                     recomendacao_correta=v[2], justificativa="j" if "não" in v else None)
        for i in itens[:3] for v in [vereditos[i.achado.evidencia.objeto]]
    ]
    return linhas, rodada


def test_taxa_principal_piso_teto_wilson():
    t = taxa(sim=2, nao=1, ind=1)
    assert (t["principal"], t["piso"], t["teto"]) == pytest.approx((2 / 3, 2 / 4, 3 / 4))
    assert t["n"] == {"sim": 2, "nao": 1, "indeterminado": 1}
    assert t["wilson"][0] < 2 / 3 < t["wilson"][1]


def test_recorte_so_de_indeterminados_nao_divide_por_zero():
    """Review Focus 4."""
    t = taxa(sim=0, nao=0, ind=3)
    assert (t["principal"], t["wilson"]) == (None, None)
    assert (t["piso"], t["teto"]) == (0.0, 1.0)


def test_medir_itens_recortes_utilizavel():
    linhas, rodada = _cenario()
    r = medir(linhas, rodada, registro=_registro(), commit="abc1234")
    assert r["ambiente"]["commit"] == "abc1234" and r["ambiente"]["linhas"] == 3
    assert r["itens"]["pertinente"]["total"]["n"] == {"sim": 2, "nao": 1, "indeterminado": 0}
    assert r["itens"]["pertinente"]["por_regra"]["MOD-001"]["principal"] == 0.5
    assert r["itens"]["recomendacao_correta"]["por_categoria"]["dax"]["n"]["indeterminado"] == 1
    # A: utilizável; B: não; C: indeterminado
    assert r["utilizavel"]["total"]["n"] == {"sim": 1, "nao": 1, "indeterminado": 1}


def test_descarte_e_automatico():
    linhas, rodada = _cenario()
    d = medir(linhas, rodada, registro=_registro())["descarte"]
    assert (d["achados"], d["sem_fundamentacao"], d["por_motivo"]) == (4, 1, {"json_invalido": 1})


def test_concordancia_humano_automatico():
    linhas, rodada = _cenario()
    c = medir(linhas, rodada, registro=_registro())["concordancia"]
    # pertinente: A auto sim/humano sim; B auto não/humano não; C auto sim/humano sim
    assert c["pertinente"]["tabela"] == {"a": 2, "b": 0, "c": 0, "d": 1}
    assert c["pertinente"]["concordancia"] == 1.0 and c["pertinente"]["kappa"] == pytest.approx(1.0)
    # fiel: automático "sem divergência"; B tem divergência e humano disse não
    assert c["fiel"]["tabela"] == {"a": 2, "b": 0, "c": 0, "d": 1}
