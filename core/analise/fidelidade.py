"""Fidelidade à evidência: números e nomes da resposta precisam aparecer no
achado ou nos trechos do contexto.

Critério nascido no spike de 29/09 (ADR-002): o 3B escreveu "duas tabelas"
quando a evidência dizia quatro, e passou nos critérios de tempo e de citação.
É uma heurística de superfície — não pega erro de sentido com números certos e
pode acusar um número derivado corretamente (8 − 4 = 4) —, por isso registra e
não descarta.
"""

import json
import re

from core.analise.base import Fidelidade, Geracao, TrechoDeContexto
from core.rules.base import Achado
from rag.texto import normalizar

_NUMERO = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?!\w)")
_PALAVRA = re.compile(r"[a-zà-ü]+")
EXTENSO_PT = {
    "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}
"""De dois a dez. `um`/`uma` ficam de fora: são artigos na maior parte das vezes."""
EXTENSO_EN = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
"""Só do lado da fonte: os trechos são em inglês, a resposta é em português."""
_NOMES = (
    re.compile(r"(?:'[^'\n]+'|[\w.-]+)?\[[^\]\n]+\]"),  # Tabela[Coluna], 'Tabela X'[Coluna], [Medida]
    re.compile(r"'([^'\n]{2,80})'"),
    re.compile(r'"([^"\n]{2,80})"'),
    re.compile(r"`([^`\n]{2,80})`"),
)
_ASPAS_RETAS = {"’": "'", "‘": "'", "“": '"', "”": '"'}


def _retas(texto: str) -> str:
    for de, para in _ASPAS_RETAS.items():
        texto = texto.replace(de, para)
    return texto


def _numeros(texto: str, extenso: dict[str, int]) -> list[float]:
    valores = [float(n.replace(",", ".")) for n in _NUMERO.findall(texto)]
    valores += [float(extenso[p]) for p in _PALAVRA.findall(normalizar(texto)) if p in extenso]
    return valores


def _nomes(texto: str) -> list[str]:
    nomes: list[str] = []
    for padrao in _NOMES:
        for casado in padrao.finditer(texto):
            nomes.append(casado.group(1) if padrao.groups else casado.group(0))
    return nomes


def _comparavel(texto: str) -> str:
    """Sem maiúsculas e sem aspas simples: `'Dim Data'[Data]` e `Dim Data[Data]`
    são o mesmo objeto."""
    return normalizar(texto).replace("'", "")


def _fonte(achado: Achado, contexto: list[TrechoDeContexto]) -> str:
    evidencia = achado.evidencia
    partes = [
        achado.mensagem,
        evidencia.objeto,
        evidencia.tabela or "",
        evidencia.trecho or "",
        json.dumps(evidencia.detalhe, ensure_ascii=False, default=str),
        *(t.texto for t in contexto),
    ]
    return _retas("\n".join(partes))


def verificar_fidelidade(geracao: Geracao, achado: Achado, contexto: list[TrechoDeContexto]) -> Fidelidade:
    resposta = _retas(f"{geracao.explicacao}\n{geracao.recomendacao}")
    fonte = _fonte(achado, contexto)
    numeros_da_fonte = set(_numeros(fonte, {**EXTENSO_EN, **EXTENSO_PT}))
    fonte_comparavel = _comparavel(fonte)

    divergencias: list[str] = []
    for valor in _numeros(resposta, EXTENSO_PT):
        if valor not in numeros_da_fonte:
            divergencias.append(f"número {valor:g} ausente do achado e dos trechos")
    for nome in _nomes(resposta):
        if _comparavel(nome) not in fonte_comparavel:
            divergencias.append(f"nome {nome} ausente do achado e dos trechos")
    return Fidelidade(divergencias=list(dict.fromkeys(divergencias)))
