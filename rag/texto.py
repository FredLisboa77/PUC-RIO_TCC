"""Normalização de texto para comparar trechos do Learn com frases transcritas.

O Learn usa aspas tipográficas (`’`) e espaço não separável; as specs de regras
transcrevem com aspas retas. Sem normalizar, a frase-marca não casaria.
"""

_TROCAS = {
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
    " ": " ",
}


def normalizar(texto: str) -> str:
    for de, para in _TROCAS.items():
        texto = texto.replace(de, para)
    return " ".join(texto.lower().split())
