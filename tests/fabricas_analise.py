"""Fábricas dos testes da geração (`core/analise`, `core/auditoria`).

Ficam fora do `conftest.py` porque não são fixtures: são construtores que cada
teste chama com os parâmetros que quer variar.
"""

import json

from core.analise.base import TrechoDeContexto
from core.analise.llm import ErroDeLLM, RespostaLLM
from core.rules.base import Achado, Evidencia, RegraMeta
from rag.avaliacao import Gabarito
from rag.chunking import TrechoIndexado
from rag.indice import BaseRag
from rag.medicao import Configuracao

RECOMENDACAO_PADRAO = (
    "Desative a opção global de data/hora automática e use uma tabela de datas própria."
)


def meta(id_regra: str = "MOD-001", termos: tuple[str, ...] = ("auto date time",)) -> RegraMeta:
    return RegraMeta(
        id=id_regra,
        titulo="Tabela de data automática",
        categoria="modelagem",
        severidade="media",
        url_canonica="https://learn.microsoft.com/x",
        termos_consulta=termos,
        recomendacao_padrao=RECOMENDACAO_PADRAO,
    )


def achado(
    id_regra: str = "MOD-001",
    *,
    objeto: str = "LocalDateTable_1",
    mensagem: str = "O modelo tem 4 tabelas de data automáticas.",
    trecho: str | None = None,
    detalhe: dict | None = None,
    tipo_objeto: str = "tabela",
) -> Achado:
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(
            tipo_objeto=tipo_objeto, objeto=objeto, tabela=objeto, trecho=trecho, detalhe=detalhe or {}
        ),
        mensagem=mensagem,
    )


def trecho_de_contexto(
    numero: int, texto: str = "Disable the auto date/time option.", origem: str | None = None
) -> TrechoDeContexto:
    return TrechoDeContexto(
        numero=numero,
        id_pagina=f"learn:p{numero}",
        url=f"https://learn.microsoft.com/p{numero}",
        titulo=f"Página {numero}",
        ancora="s",
        caminho="Seção",
        texto=texto,
        origem=origem or ("ancora" if numero == 1 else "busca"),
    )


def contexto(n: int = 3) -> list[TrechoDeContexto]:
    return [trecho_de_contexto(i) for i in range(1, n + 1)]


def trecho_indexado(id_pagina: str, texto: str, *, ancora: str = "s", parte: int = 1) -> TrechoIndexado:
    return TrechoIndexado(
        id=f"{id_pagina}#{ancora}/{parte}",
        id_pagina=id_pagina,
        url=f"https://learn.microsoft.com/{id_pagina.split(':', 1)[1]}",
        titulo_pagina="T",
        ancora=ancora,
        caminho="Seção",
        texto=texto,
        texto_indexado=texto,
    )


def base_bm25(trechos: list[TrechoIndexado]) -> BaseRag:
    return BaseRag(Configuracao(chunking="secao", cabecalho=False, busca="bm25", corpus="completo"), trechos)


def gabarito(
    id_regra: str = "MOD-001",
    *,
    id_pagina: str = "learn:auto",
    ancora: str = "s",
    frase_marca: str = "disable the auto date time option",
) -> Gabarito:
    return Gabarito(id_regra=id_regra, frase_marca=frase_marca, id_pagina=id_pagina, ancora=ancora)


TRECHO_ANCORA = trecho_indexado("learn:auto", "You should disable the auto date time option in every model.")


def base_padrao() -> BaseRag:
    return base_bm25([TRECHO_ANCORA, trecho_indexado("learn:outra", "auto date time tables are hidden")])


def resposta(
    explicacao: str = "As tabelas automáticas aumentam o tamanho do modelo sem necessidade.",
    recomendacao: str = "Desative a opção global de data/hora automática.",
    citacoes: tuple[int, ...] = (1,),
) -> str:
    return json.dumps(
        {"explicacao": explicacao, "recomendacao": recomendacao, "citacoes": list(citacoes)}, ensure_ascii=False
    )


RESPOSTA_BOA = resposta()


class LLMFalso:
    """Devolve as respostas roteirizadas, em ordem; depois delas, `RESPOSTA_BOA`.
    Uma exceção na lista é levantada no lugar da resposta."""

    nome = "llm-falso"

    def __init__(self, *respostas, falha_no_aquecimento: bool = False) -> None:
        self.respostas = list(respostas)
        self.falha_no_aquecimento = falha_no_aquecimento
        self.chamadas: list[list[dict[str, str]]] = []
        self.aquecimentos = 0

    def aquecer(self) -> None:
        self.aquecimentos += 1
        if self.falha_no_aquecimento:
            raise ErroDeLLM("o Ollama não respondeu em http://127.0.0.1:11434")

    def gerar(self, mensagens, esquema) -> RespostaLLM:
        self.chamadas.append(mensagens)
        proxima = self.respostas.pop(0) if self.respostas else RESPOSTA_BOA
        if isinstance(proxima, Exception):
            raise proxima
        return RespostaLLM(texto=proxima, segundos=0.5)
