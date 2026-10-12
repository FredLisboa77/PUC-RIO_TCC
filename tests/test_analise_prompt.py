"""Prompt da geração: o LLM explica um achado já decidido e cita pelo número."""

from pathlib import Path

from core.analise.prompt import ESQUEMA, LIMITE_TRECHO_CODIGO, montar_mensagens
from fabricas_analise import achado, contexto, meta


def test_duas_mensagens_sistema_e_usuario():
    assert [m["role"] for m in montar_mensagens(meta(), achado(), contexto(1))] == ["system", "user"]


def test_sistema_fixa_o_papel_do_llm():
    sistema = montar_mensagens(meta(), achado(), contexto(1))[0]["content"]
    assert "NÃO decide" in sistema
    assert "1 a 3" in sistema
    assert "português do Brasil" in sistema


def test_usuario_traz_o_achado_e_os_trechos_numerados():
    usuario = montar_mensagens(meta(), achado(), contexto(2))[1]["content"]
    assert "MOD-001" in usuario
    assert "O modelo tem 4 tabelas de data automáticas." in usuario
    assert "[1] Página 1 › Seção" in usuario
    assert "[2] Página 2 › Seção" in usuario


def test_trecho_de_codigo_longo_e_cortado():
    usuario = montar_mensagens(meta(), achado(trecho="X" * 3000), contexto(1))[1]["content"]
    assert "X" * LIMITE_TRECHO_CODIGO + " […]" in usuario
    assert "X" * (LIMITE_TRECHO_CODIGO + 1) not in usuario


def test_achado_sem_trecho_nem_detalhe_omite_as_secoes():
    usuario = montar_mensagens(meta(), achado(), contexto(1))[1]["content"]
    assert "TRECHO DO MODELO" not in usuario
    assert "DETALHE" not in usuario


def test_detalhe_nao_serializavel_nao_quebra():
    usuario = montar_mensagens(meta(), achado(detalhe={"p": Path("a/b"), "s": {1}}), contexto(1))[1]["content"]
    assert "DETALHE" in usuario


def test_esquema_exige_os_tres_campos_e_limita_citacoes():
    assert set(ESQUEMA["required"]) == {"explicacao", "recomendacao", "citacoes"}
    citacoes = ESQUEMA["properties"]["citacoes"]
    assert (citacoes["minItems"], citacoes["maxItems"], citacoes["items"]["type"]) == (1, 3, "integer")
