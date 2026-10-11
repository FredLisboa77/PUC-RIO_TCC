"""A consulta de recuperação de um achado (Fase 3).

É a função que o pipeline real chama, e também a que gera as consultas do
conjunto de avaliação: o conjunto mede a consulta que será usada. Os termos
são os da regra, em inglês, porque o `bge-small-en-v1.5` é monolíngue (ADR-002,
revisão C-6). A `mensagem` do achado, em português, e o trecho de DAX ou M
ficam de fora.
"""

from core.rules.base import Achado, RegraMeta

TIPOS_EM_INGLES = {
    "tabela": "table",
    "coluna": "column",
    "medida": "measure",
    "relacionamento": "relationship",
    "particao": "partition",
    "modelo": "model",
}


def montar_consulta(meta: RegraMeta, achado: Achado | None = None) -> str:
    texto = "; ".join(meta.termos_consulta)
    if achado is None:
        return texto
    tipo = TIPOS_EM_INGLES[achado.evidencia.tipo_objeto]
    return f"{texto} | {tipo} {achado.evidencia.objeto}"
