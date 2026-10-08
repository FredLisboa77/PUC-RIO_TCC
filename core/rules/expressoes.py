"""Onde o DAX mora no modelo.

Modelo entra, varredura sai. **Não conhece sintaxe de DAX** — isso é de
`core/dax.py` — e não conhece regra. Filtra por linguagem (partição só entra se
`source.type == "calculated"`) e pelo escopo de `tabelas_com_dax_do_autor`, que
é o de quem escreveu o DAX — **não** `tabelas_em_escopo`, que exclui também a
tabela de medidas e deixaria a varredura cega para 93 das 105 expressões do
PBIP real.

As duas listas vêm juntas, de uma função só, e por construção: as regras iteram
apenas `expressoes`, de modo que uma expressão que não tokenizou por completo
não chega a nenhuma regra. É estruturalmente impossível a ferramenta afirmar
algo sobre um trecho que o relatório declara não ter analisado.

O grupo 4 — regras de Power Query M — reusa este módulo trocando o filtro.
"""

from pydantic import BaseModel, Field

from core.dax import TipoToken, Token, tem_desconhecido, tokenizar
from core.model import ModeloSemantico
from core.rules.escopo import tabelas_com_dax_do_autor

VIZINHANCA = 40
"""Caracteres de contexto em volta da posição da lacuna, para o usuário
localizar o trecho no Power BI Desktop."""


class ExpressaoDax(BaseModel):
    sitio: str
    objeto: str
    tabela: str | None = None
    texto: str
    tokens: list[Token] = Field(default_factory=list)


class LacunaDax(BaseModel):
    """Expressão que o lexer não conseguiu ler por completo.

    Não é achado — nada se afirma sobre o modelo — nem falha de regra. É uma
    declaração de cegueira: estas linhas do arquivo não foram analisadas.
    """

    sitio: str
    objeto: str
    tabela: str | None = None
    posicao: int
    trecho: str
    motivo: str


class VarreduraDax(BaseModel):
    expressoes: list[ExpressaoDax] = Field(default_factory=list)
    lacunas: list[LacunaDax] = Field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.expressoes) + len(self.lacunas)


def _sitios(modelo: ModeloSemantico):
    """Todo lugar em escopo onde há DAX, como (sitio, objeto, tabela, texto)."""
    for t in tabelas_com_dax_do_autor(modelo):
        for m in t.medidas:
            if m.expressao:
                yield "medida", f"{t.nome}[{m.nome}]", t.nome, m.expressao
        for c in t.colunas:
            if c.expressao:
                yield "coluna calculada", f"{t.nome}[{c.nome}]", t.nome, c.expressao
        for p in t.particoes:
            if p.tipo_origem == "calculated" and p.origem:
                yield "particao calculada", f"{t.nome}:{p.nome}", t.nome, p.origem

    for r in modelo.roles:
        for perm in r.permissoes:
            if perm.expressao_filtro:
                yield (
                    "role",
                    f"{r.nome}:{perm.tabela}",
                    perm.tabela,
                    perm.expressao_filtro,
                )


def varrer_dax(modelo: ModeloSemantico) -> VarreduraDax:
    """Tokeniza todo o DAX em escopo, separando o que não deu."""
    expressoes: list[ExpressaoDax] = []
    lacunas: list[LacunaDax] = []

    for sitio, objeto, tabela, texto in _sitios(modelo):
        tokens = tokenizar(texto)

        if tem_desconhecido(tokens):
            primeiro = next(t for t in tokens if t.tipo is TipoToken.DESCONHECIDO)
            inicio = max(0, primeiro.posicao - VIZINHANCA)
            lacunas.append(
                LacunaDax(
                    sitio=sitio,
                    objeto=objeto,
                    tabela=tabela,
                    posicao=primeiro.posicao,
                    trecho=texto[inicio : primeiro.posicao + VIZINHANCA],
                    motivo=f"caractere não reconhecido: {primeiro.texto!r}",
                )
            )
            continue

        expressoes.append(
            ExpressaoDax(
                sitio=sitio, objeto=objeto, tabela=tabela, texto=texto, tokens=tokens
            )
        )

    return VarreduraDax(expressoes=expressoes, lacunas=lacunas)
