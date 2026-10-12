"""Prompt da geração (ADR-003): a regra já decidiu, o LLM só explica e cita.

Os trechos ficam em inglês, como o corpus (ADR-002, C-6); a resposta é pedida em
português. A citação é pelo número do trecho: o código traduz para página e
seção, e um 7B não precisa copiar URLs.
"""

import json

from core.analise.base import TrechoDeContexto
from core.rules.base import Achado, RegraMeta
from rag.chunking import cabecalho_de

LIMITE_TRECHO_CODIGO = 1500

ESQUEMA = {
    "type": "object",
    "properties": {
        "explicacao": {"type": "string"},
        "recomendacao": {"type": "string"},
        "citacoes": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 3},
    },
    "required": ["explicacao", "recomendacao", "citacoes"],
}

SISTEMA = """Você é um auditor de modelos semânticos do Power BI.
Uma regra determinística JÁ detectou o problema descrito pelo usuário. Você NÃO decide se o problema existe: sua tarefa é explicá-lo e recomendar a correção.
Use somente as informações do achado e dos trechos de documentação numerados. Não invente números, nomes de objetos nem fatos.
Responda em português do Brasil, em JSON, com:
- "explicacao": por que isso é um problema neste modelo;
- "recomendacao": o que fazer, de forma acionável;
- "citacoes": de 1 a 3 números dos trechos que sustentam a explicação.
Explicação e recomendação juntas devem ter no máximo 120 palavras."""


def _cortar(codigo: str) -> str:
    if len(codigo) <= LIMITE_TRECHO_CODIGO:
        return codigo
    return codigo[:LIMITE_TRECHO_CODIGO] + " […]"


def _usuario(meta: RegraMeta, achado: Achado, contexto: list[TrechoDeContexto]) -> str:
    evidencia = achado.evidencia
    partes = [
        f"REGRA: {meta.id} — {meta.titulo} (categoria {meta.categoria})",
        f"OBJETO: {evidencia.tipo_objeto} {evidencia.objeto}",
        f"ACHADO: {achado.mensagem}",
    ]
    if evidencia.trecho:
        partes.append(f"TRECHO DO MODELO:\n{_cortar(evidencia.trecho)}")
    if evidencia.detalhe:
        detalhe = json.dumps(evidencia.detalhe, ensure_ascii=False, default=str, sort_keys=True)
        partes.append(f"DETALHE: {detalhe}")
    trechos = "\n\n".join(
        f"[{t.numero}] {cabecalho_de(t.titulo, t.caminho)}\n{t.texto}" for t in contexto
    )
    partes.append(f"TRECHOS DE DOCUMENTAÇÃO\n{trechos}")
    return "\n\n".join(partes)


def montar_mensagens(meta: RegraMeta, achado: Achado, contexto: list[TrechoDeContexto]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": _usuario(meta, achado, contexto)},
    ]
