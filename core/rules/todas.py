"""Carrega todas as regras, populando o registro global.

Importar este módulo é o que faz as regras existirem para o `runner`. Sem ele o
`REGISTRO` fica vazio — e isso é deliberado, para que os testes do motor usem
registros isolados sem depender da ordem de importação.
"""

from core.rules import modelagem, performance  # noqa: F401 — o import registra
from core.rules.registry import REGISTRO

__all__ = ["REGISTRO"]
