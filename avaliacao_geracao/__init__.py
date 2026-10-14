"""Avaliação da geração com rubrica humana e consolidação dos resultados (Fase 5).

Desenho: `docs/superpowers/specs/2026-10-13-avaliacao-da-geracao-design.md`.
"""


class ErroDeAvaliacao(Exception):
    """A avaliação não pode seguir sem produzir um número enganoso."""
