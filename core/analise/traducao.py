"""Tradução sob demanda de um trecho citado (spec de 13/10/2026, seção 2.5).

Só de exibição: a validação da citação já foi feita sobre o original, e nada
traduzido é gravado no resultado. A interface mostra a tradução ao lado do
original, com o rótulo de tradução automática.
"""

import json

from core.analise.llm import LLMClient

ESQUEMA_TRADUCAO = {
    "type": "object",
    "properties": {"traducao": {"type": "string"}},
    "required": ["traducao"],
}

SISTEMA_TRADUCAO = """Você traduz trechos da documentação oficial do Power BI do inglês para o português do Brasil.
Traduza fielmente, sem resumir, sem explicar e sem acrescentar nada.
Mantenha em inglês os nomes de funções DAX e M, de propriedades e de opções do Power BI, e todo trecho de código.
Responda em JSON com o campo "traducao"."""


class ErroDeTraducao(Exception):
    """O LLM respondeu, mas não com uma tradução utilizável."""


def traduzir_trecho(texto: str, llm: LLMClient) -> str:
    """Erros do próprio LLM (`ErroDeLLM`, inclusive `ContextoExcedido`) passam
    adiante: quem chama decide a mensagem."""
    mensagens = [{"role": "system", "content": SISTEMA_TRADUCAO}, {"role": "user", "content": texto}]
    resposta = llm.gerar(mensagens, ESQUEMA_TRADUCAO)
    try:
        bruto = json.loads(resposta.texto)
    except json.JSONDecodeError as erro:
        raise ErroDeTraducao("o LLM não devolveu JSON válido") from erro
    traducao = bruto.get("traducao") if isinstance(bruto, dict) else None
    if not isinstance(traducao, str) or not traducao.strip():
        raise ErroDeTraducao("o LLM devolveu uma tradução vazia")
    return traducao.strip()
