"""Onde cada coluna do modelo é usada.

A PERF-005 afirma por **ausência**: "esta coluna não é referenciada em lugar
nenhum". Sob o terceiro teste do critério de detectabilidade, afirmação por
ausência exige varrer **todos** os lugares onde o sinal poderia aparecer. São
oito, e no P8 existem 10 `sortByColumn` e 16 níveis de hierarquia — esquecer um
desses sítios faz a ferramenta recomendar apagar uma coluna em uso, quebrando a
ordenação ou a hierarquia do relatório.

Este módulo é a única casa dessa resolução. A regra não a reimplementa.
"""

from core.dax import referencias
from core.model import ModeloSemantico
from core.rules.escopo import tabelas_em_escopo
from core.rules.expressoes import varrer_dax

SITIOS_DE_USO = (
    "relacionamento",
    "hierarquia",
    "ordenacao",
    "variacao",
    "dax de medida",
    "dax de coluna calculada",
    "dax de particao calculada",
    "dax de role",
)

_SITIO_DA_VARREDURA = {
    "medida": "dax de medida",
    "coluna calculada": "dax de coluna calculada",
    "particao calculada": "dax de particao calculada",
    "role": "dax de role",
}


def usos_de_coluna(modelo: ModeloSemantico) -> dict[tuple[str, str], set[str]]:
    """De `(tabela, coluna)` para os sítios que a usam.

    Toda coluna de tabela em escopo aparece na saída, mesmo com conjunto vazio:
    conjunto vazio é o que a PERF-005 procura, e uma chave ausente seria
    indistinguível de uma coluna que não existe.
    """
    usos: dict[tuple[str, str], set[str]] = {
        (t.nome, c.nome): set() for t in tabelas_em_escopo(modelo) for c in t.colunas
    }

    def marcar(tabela: str | None, coluna: str, sitio: str) -> None:
        if tabela is None:
            return
        chave = (tabela, coluna)
        if chave in usos:
            usos[chave].add(sitio)

    for r in modelo.relacionamentos:
        marcar(r.tabela_origem, r.coluna_origem, "relacionamento")
        marcar(r.tabela_destino, r.coluna_destino, "relacionamento")

    for t in tabelas_em_escopo(modelo):
        for h in t.hierarquias:
            for n in h.niveis:
                marcar(n.tabela, n.coluna, "hierarquia")
        for c in t.colunas:
            if c.ordenar_por:
                marcar(t.nome, c.ordenar_por, "ordenacao")
            if c.bruto.get("variations"):
                marcar(t.nome, c.nome, "variacao")

    varredura = varrer_dax(modelo)
    for e in varredura.expressoes:
        sitio = _SITIO_DA_VARREDURA[e.sitio]
        for ref in referencias(e.tokens):
            if ref.coluna is None:
                continue
            marcar(ref.tabela or e.tabela, ref.coluna, sitio)

    return usos
