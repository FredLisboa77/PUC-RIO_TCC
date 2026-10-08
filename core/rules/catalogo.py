"""O catálogo de regras, em Markdown.

`python -m core.rules.catalogo` imprime a tabela que vai ao capítulo de
metodologia. Gerar em vez de manter à mão elimina a divergência entre o que o
código faz e o que a monografia diz que ele faz.

As URLs canónicas daqui são também as páginas que a base RAG precisa conter
(G-8, semana 5): o catálogo de regras alimenta o catálogo de fontes.
"""

from core.rules.todas import REGISTRO

IDS_ESPERADOS = [
    "DAX-001",
    "MOD-001",
    "MOD-002",
    "MOD-003",
    "MOD-005",
    "MOD-006",
    "MOD-007",
    "PERF-001",
    "PERF-003",
]
"""As regras desta etapa. Um teste compara com o registro: regra acrescentada
sem atualizar esta lista falha a suíte, de propósito."""

CABECALHO = (
    "| ID | Regra | Categoria | Severidade | Fonte |\n"
    "|---|---|---|---|---|"
)


def como_markdown() -> str:
    """O catálogo como tabela Markdown, uma linha por regra."""
    linhas = [CABECALHO]
    for meta in REGISTRO.metas():
        nota = " (nota)" if meta.nota_de_verificacao else ""
        linhas.append(
            f"| {meta.id} | {meta.titulo}{nota} | {meta.categoria} | "
            f"{meta.severidade} | <{meta.url_canonica}> |"
        )
    linhas.append("")
    linhas.append(f"{len(REGISTRO)} regras. (nota) = tem nota de verificação.")
    return "\n".join(linhas)


def main() -> None:
    print(como_markdown())
    for meta in REGISTRO.metas():
        if meta.nota_de_verificacao:
            print(f"\n**{meta.id} — nota de verificação:** {meta.nota_de_verificacao}")


if __name__ == "__main__":
    main()
