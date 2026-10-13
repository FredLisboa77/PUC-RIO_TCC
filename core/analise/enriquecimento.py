"""Enriquecimento de um achado (ADR-003): o LLM explica e cita; se a resposta não
passa na validação, o achado sai com a recomendação padrão da regra."""

import logging

from core.analise.base import AchadoEnriquecido
from core.analise.contexto import montar_contexto
from core.analise.fidelidade import verificar_fidelidade
from core.analise.llm import ContextoExcedido, ErroDeLLM, LLMClient
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
    reducoes = 0
    while True:
        comum = dict(achado=achado, contexto=contexto, modelo=llm.nome, reducoes_de_contexto=reducoes)
        try:
            resposta = llm.gerar(montar_mensagens(meta, achado, contexto), ESQUEMA)
            break
        except ContextoExcedido as erro:
            # O orçamento de contexto é em palavras, e código chega a ~3,4 tokens por
            # palavra: tira o último complementar e tenta de novo. A âncora nunca sai.
            if len(contexto) == 1:
                logger.warning("nem a âncora coube no achado %s/%s: %s", achado.id_regra, achado.evidencia.objeto, erro)
                return AchadoEnriquecido(**comum, situacao="sem_fundamentacao", motivo_descarte="contexto_excedido")
            contexto = contexto[:-1]
            reducoes += 1
        except ErroDeLLM as erro:
            logger.warning("LLM falhou no achado %s/%s: %s", achado.id_regra, achado.evidencia.objeto, erro)
            return AchadoEnriquecido(**comum, situacao="sem_fundamentacao", motivo_descarte="erro_llm")

    comum.update(segundos=resposta.segundos, tokens_prompt=resposta.tokens_prompt, do_cache=resposta.do_cache)
    geracao, motivo = validar(resposta.texto, len(contexto))
    if geracao is None:
        return AchadoEnriquecido(**comum, situacao="sem_fundamentacao", motivo_descarte=motivo)
    return AchadoEnriquecido(
        **comum,
        geracao=geracao,
        situacao="gerado",
        cita_ancora=1 in geracao.citacoes,
        fidelidade=verificar_fidelidade(geracao, achado, contexto),
    )
