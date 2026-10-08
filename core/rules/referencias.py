"""Onde cada coluna do modelo é usada.

Este módulo nasceu para sustentar a PERF-005, que afirmaria por **ausência**:
"esta coluna não é referenciada em lugar nenhum". A medição que ele produziu
foi o que **rejeitou** essa regra, não o que a confirmou. Dos 36 pares
(tabela, coluna) sem uso em nenhum dos oito sítios abaixo, medidos no P8, só
uma fração pequena é defensável como coluna sem uso (chaves surrogate
órfãs); o resto são atributos comuns de relatório — `StoreName`, `Education`,
`Occupation`… — quase certamente usados numa visual do Power BI, e colunas de
calendário que a própria documentação recomenda manter. O critério de
detectabilidade exige varrer **todos** os lugares onde o sinal poderia estar
— seu terceiro teste, cláusula (c) —, e a camada de relatório, onde um
atributo comum justifica sua existência, é F19: fora do que esta auditoria
lê. Uma regra que afirmasse "sem uso" só a partir deste módulo estaria
afirmando sobre um domínio que não observa — e é exatamente por isso que a
precisão não pode ser estabelecida: dos 33 que a regra reportaria (36 menos 3
geradas por agrupamento/análise), 5 são verdadeiro positivo defensável, 3 são
falso positivo confirmado (documentação recomenda mantê-las), e os outros 25
dependem da camada de relatório que este módulo não lê. A precisão, portanto,
varia entre ~15% (5/33, se as 25 estiverem em uso — o cenário provável) e
~91% (30/33, se nenhuma estiver) contra um limiar de projeto de 0,7: uma
faixa larga o bastante para não sustentar nenhum número único. **Nenhuma
regra deve tratar um conjunto vazio aqui como "coluna sem uso"**; é, no
máximo, "sem uso estrutural ou em DAX conhecido pela ferramenta".

O módulo continua existindo porque é a evidência reprodutível desse
resultado — apagá-lo reduziria a medição a anedota — e porque serve a uma
regra futura cuja afirmação não dependa da camada de relatório.

São oito sítios, e no P8 existem 10 `sortByColumn` e 16 níveis de
hierarquia — esquecer um deles distorceria a contagem na mesma direção do
erro que já rejeitou a PERF-005: colunas que parecem sem uso sem sê-lo.

Dois riscos de sósia, resolvidos por construção:

- **nome dentro de comentário ou string não é referência** — o lexer
  (`core/dax.py`) já separa esses tokens de `REFERENCIA`, então um nome de
  coluna mencionado em `// comentário` ou em `"string"` nunca chega a este
  módulo como uso.
- **coluna homônima em outra tabela** — `[Coluna]` sem qualificador resolve
  na tabela dona da expressão (`ref.tabela or e.tabela`), nunca na tabela de
  uma referência qualificada que use o mesmo nome de coluna. O P8 tem três
  colunas `GeographyKey`, em tabelas diferentes; marcar a tabela errada
  trocaria o resultado de duas colunas ao mesmo tempo — a usada pareceria sem
  uso, e a sem uso pareceria usada.

Um limite conhecido e **não corrigido**: `ref.tabela or e.tabela` resolve
toda referência não qualificada pela tabela dona da expressão, nunca pela
tabela de um iterador. Numa medida como `SUMX(Outra, [Coluna])` ou
`FILTER(Outra, [Coluna] = …)`, o DAX resolve `[Coluna]` pelo contexto de
linha de `Outra`, não pela tabela da medida — e este módulo não modela
contexto de linha, de modo que uma coluna referenciada só desse jeito não
seria marcada. Corrigir isso exige um parser sintático de DAX (F18, Trabalhos
Futuros, fora desta fase). É aceitável agora porque nenhuma regra afirma
ausência a partir deste módulo (ver acima); seria inaceitável se alguma
viesse a afirmar, e quem construir essa regra precisa resolver este ponto
antes. No PBIP real, toda chamada de `SUMX`, `RANKX` e `MINX` qualifica o
argumento de coluna, então a medição de 36 não é distorcida por este
limite — mas isso é um fato deste corpus, não uma garantia do método.

Este módulo é a única casa dessa resolução. Nenhuma regra a reimplementa.
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
    conjunto vazio é o sinal medido — ver o docstring do módulo sobre por que
    ele não basta para afirmar "sem uso" — e uma chave ausente seria
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
            marcar(ref.tabela or e.tabela, ref.coluna, sitio)

    return usos
