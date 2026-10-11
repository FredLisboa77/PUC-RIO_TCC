"""Normalização usada para casar a frase-marca com o texto do Learn."""

from rag.texto import normalizar


def test_aspas_tipograficas_viram_retas():
    assert normalizar("Don’t use “DIVIDE” ‘here’") == "don't use \"divide\" 'here'"


def test_espaco_nao_separavel_e_espacos_repetidos():
    assert normalizar("Auto date/time   option\n\tnow") == "auto date/time option now"


def test_maiusculas_viram_minusculas():
    assert normalizar("Mark Your Date Table") == "mark your date table"
