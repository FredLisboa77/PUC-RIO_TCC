"""Intervalo de Wilson (Wilson, 1927), kappa de Cohen (Cohen, 1960) e teste exato
de McNemar (McNemar, 1947).

Wilson e não o intervalo normal: com n pequeno e taxas perto de 1 — o caso das
regras por projeto — o intervalo normal sai de [0, 1] e fica estreito demais.
"""

from math import comb, sqrt


def wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = sucessos / total
    denominador = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / denominador
    margem = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominador
    return max(0.0, centro - margem), min(1.0, centro + margem)


def kappa(a: int, b: int, c: int, d: int) -> float | None:
    """Automático (linhas) × humano (colunas): `a` ambos sim, `b` automático sim e
    humano não, `c` automático não e humano sim, `d` ambos não. `None` quando não
    há linhas ou quando o acaso explica tudo (`pe == 1`)."""
    n = a + b + c + d
    if n == 0:
        return None
    observada = (a + d) / n
    acaso = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    if acaso == 1:
        return None
    return (observada - acaso) / (1 - acaso)


def mcnemar_exato(b: int, c: int) -> float:
    """p bilateral do teste exato de McNemar sobre os pares discordantes `b` e `c`.

    Sob a hipótese nula, cada par discordante cai de um lado ou do outro com
    probabilidade 1/2: binomial(b + c, 1/2), dobrando a cauda menor.
    """
    n = b + c
    if n == 0:
        return 1.0
    cauda = sum(comb(n, k) for k in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * cauda)
