"""Validação da resposta do LLM (ADR-003): sem citação válida, não há geração.

Não confia no esquema imposto pelo Ollama: os limites de itens do JSON Schema
podem não ser respeitados pela decodificação restrita, então tudo é conferido
de novo aqui.
"""

import json

from core.analise.base import Geracao, MotivoDescarte

MAX_CITACOES = 3


def validar(texto: str, tamanho_contexto: int) -> tuple[Geracao | None, MotivoDescarte | None]:
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError:
        return None, "json_invalido"
    if not isinstance(bruto, dict):
        return None, "json_invalido"
    explicacao = bruto.get("explicacao")
    recomendacao = bruto.get("recomendacao")
    citacoes = bruto.get("citacoes")
    # `type(c) is int`, não `isinstance`: `True` é `int` em Python.
    if (
        not isinstance(explicacao, str)
        or not isinstance(recomendacao, str)
        or not isinstance(citacoes, list)
        or not all(type(c) is int for c in citacoes)
    ):
        return None, "json_invalido"
    if not explicacao.strip() or not recomendacao.strip():
        return None, "campo_vazio"
    if not 1 <= len(citacoes) <= MAX_CITACOES or len(set(citacoes)) != len(citacoes):
        return None, "citacoes_fora_do_limite"
    if any(not 1 <= c <= tamanho_contexto for c in citacoes):
        return None, "citacao_inexistente"
    return Geracao(explicacao=explicacao.strip(), recomendacao=recomendacao.strip(), citacoes=citacoes), None
