"""Execução das regras.

A auditoria é sequencial e sem estado (ADR-003). Este módulo é o passo "regras"
do fluxo: recebe o modelo normalizado e devolve os achados, em ordem estável.
"""

import logging

from pydantic import BaseModel, Field

from core.model import ModeloSemantico
from core.rules.base import ORDEM_SEVERIDADE, Achado
from core.rules.registry import REGISTRO, Registro

logger = logging.getLogger(__name__)


class FalhaDeRegra(BaseModel):
    id_regra: str
    erro: str


class ResultadoRegras(BaseModel):
    """O que a etapa de regras entrega.

    Não é uma lista nua de propósito: a interface precisa poder dizer "7 de 8
    regras executadas" em vez de entregar menos achados em silêncio.
    """

    achados: list[Achado] = Field(default_factory=list)
    regras_com_falha: list[FalhaDeRegra] = Field(default_factory=list)
    regras_executadas: int = 0

    @property
    def total_de_regras(self) -> int:
        return self.regras_executadas + len(self.regras_com_falha)


def avaliar(
    modelo: ModeloSemantico, registro: Registro | None = None
) -> ResultadoRegras:
    """Executa as regras do registro sobre o modelo.

    A ordem da saída é severidade (alta → baixa), ID da regra e nome do objeto.
    Determinismo não é estética: a avaliação da Fase 5 compara listas, e uma
    ordem instável viraria diferença falsa entre execuções.

    Uma regra que levanta exceção é isolada e registrada. O usuário final não
    perde a auditoria inteira por causa de uma propriedade inesperada do TMSL.
    """
    reg = REGISTRO if registro is None else registro
    achados: list[Achado] = []
    falhas: list[FalhaDeRegra] = []
    executadas = 0

    for id_regra in reg.ids():
        try:
            # Materializa antes de acumular. Uma regra geradora pode levantar
            # exceção depois de já ter produzido achados, e `list.extend`
            # acrescenta item a item: sem a lista local, metade da saída de uma
            # regra que quebrou entraria no resultado. Saída parcial de regra
            # com defeito é pior que saída nenhuma — ela falsearia as contagens
            # da Fase 5 sem que nada aparecesse.
            da_regra = list(reg.avaliador(id_regra)(modelo))
        except Exception as erro:  # noqa: BLE001 — isolar é o objetivo
            logger.exception("a regra %s falhou", id_regra)
            falhas.append(
                FalhaDeRegra(id_regra=id_regra, erro=f"{type(erro).__name__}: {erro}")
            )
        else:
            achados.extend(da_regra)
            executadas += 1

    achados.sort(
        key=lambda a: (
            ORDEM_SEVERIDADE[reg.meta(a.id_regra).severidade],
            a.id_regra,
            a.evidencia.objeto,
        )
    )
    return ResultadoRegras(
        achados=achados, regras_com_falha=falhas, regras_executadas=executadas
    )
