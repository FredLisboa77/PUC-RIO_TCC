"""Enriquecimento de um achado (ADR-003): o LLM explica e cita; se a resposta não
passa na validação, o achado sai com a recomendação padrão da regra."""

import logging

from core.analise.base import AchadoEnriquecido
from core.analise.contexto import montar_contexto
from core.analise.fidelidade import verificar_fidelidade
from core.analise.llm import ErroDeLLM, LLMClient
from core.analise.prompt import ESQUEMA, montar_mensagens
from core.analise.validacao import validar
from core.rules.base import Achado, RegraMeta
from rag.avaliacao import Gabarito
from rag.indice import BaseRag

logger = logging.getLogger(__name__)


def enriquecer(
    achado: Achado, meta: RegraMeta, *, base: BaseRag, gabarito: Gabarito, llm: LLMClient
) -> AchadoEnriquecido:
    contexto = montar_contexto(meta, achado, base, gabarito)
    comum = dict(achado=achado, contexto=contexto, modelo=llm.nome)
    try:
        resposta = llm.gerar(montar_mensagens(meta, achado, contexto), ESQUEMA)
    except ErroDeLLM as erro:
        logger.warning("LLM falhou no achado %s/%s: %s", achado.id_regra, achado.evidencia.objeto, erro)
        return AchadoEnriquecido(**comum, situacao="sem_fundamentacao", motivo_descarte="erro_llm")

    geracao, motivo = validar(resposta.texto, len(contexto))
    if geracao is None:
        return AchadoEnriquecido(
            **comum, situacao="sem_fundamentacao", motivo_descarte=motivo, segundos=resposta.segundos
        )
    return AchadoEnriquecido(
        **comum,
        geracao=geracao,
        situacao="gerado",
        cita_ancora=1 in geracao.citacoes,
        fidelidade=verificar_fidelidade(geracao, achado, contexto),
        segundos=resposta.segundos,
    )
