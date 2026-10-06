"""Registro das regras.

O registro guarda metadados e função lado a lado, indexados pelo ID. É o que
permite ao achado carregar só o `id_regra` e ao catálogo ser gerado a partir do
código, em vez de mantido à mão.
"""

from collections.abc import Callable, Iterable

from core.model import ModeloSemantico
from core.rules.base import Achado, RegraMeta

Avaliador = Callable[[ModeloSemantico], Iterable[Achado]]


class RegraDuplicada(ValueError):
    """Duas regras com o mesmo ID. Erro de programação, não de dado."""


class Registro:
    """Coleção de regras. Instanciável, para que os testes usem o seu próprio."""

    def __init__(self) -> None:
        self._metas: dict[str, RegraMeta] = {}
        self._avaliadores: dict[str, Avaliador] = {}

    def registrar(self, meta: RegraMeta, avaliador: Avaliador) -> None:
        if meta.id in self._metas:
            raise RegraDuplicada(f"a regra {meta.id} já está registrada")
        self._metas[meta.id] = meta
        self._avaliadores[meta.id] = avaliador

    def ids(self) -> list[str]:
        """IDs em ordem alfabética — a ordem de execução do runner."""
        return sorted(self._metas)

    def meta(self, id_regra: str) -> RegraMeta:
        return self._metas[id_regra]

    def metas(self) -> list[RegraMeta]:
        return [self._metas[i] for i in self.ids()]

    def avaliador(self, id_regra: str) -> Avaliador:
        return self._avaliadores[id_regra]

    def __len__(self) -> int:
        return len(self._metas)


REGISTRO = Registro()
"""Registro global. Só fica populado depois de importar `core.rules.todas`."""


def regra(
    *, registro: Registro | None = None, **campos
) -> Callable[[Avaliador], Avaliador]:
    """Registra a função decorada como regra.

    Os `campos` são os de `RegraMeta`, e é ele quem os valida — uma regra sem
    âncora falha aqui, na importação do módulo.
    """

    def decorador(funcao: Avaliador) -> Avaliador:
        destino = REGISTRO if registro is None else registro
        destino.registrar(RegraMeta(**campos), funcao)
        return funcao

    return decorador
