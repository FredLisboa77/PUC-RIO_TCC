# Varredura textual de DAX e o grupo 2 de regras — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar ao projeto a capacidade de ler o texto das expressões DAX com exatidão, e sobre ela entregar as primeiras regras do grupo 2 — sem nunca afirmar algo sobre um trecho que não foi analisado.

**Architecture:** Três componentes com assuntos separados. `core/dax.py` é um lexer: texto entra, tokens tipados saem, e nunca levanta exceção. `core/rules/expressoes.py` enumera onde o DAX mora no modelo, respeitando as exclusões de escopo e filtrando por linguagem, e devolve as expressões tokenizadas **junto** com as lacunas — expressão que não tokenizou por completo não chega às regras. `core/rules/dax.py` e a PERF-005 em `performance.py` consomem os dois.

**Tech Stack:** Python 3.11.9 · Pydantic 2.13.5 · pytest 9.1.1. **Sem novas dependências.**

**Spec:** [`docs/superpowers/specs/2026-10-08-regras-de-dax-e-varredura-textual-design.md`](../specs/2026-10-08-regras-de-dax-e-varredura-textual-design.md)

## Global Constraints

- **Sem novas dependências.** `requirements.txt` fica em `pydantic==2.13.5` e `pytest==9.1.1`.
- **Os 15 achados atuais do P8 não podem mudar**, e os 101 testes atuais continuam passando. Nenhuma tarefa tem direito de alterar contagem de MOD-\* ou PERF-001/003.
- **Vocabulário em português** em nome de módulo, classe, função, variável, teste e mensagem de commit — convenção do projeto inteiro.
- **Nenhuma regra entra sem âncora citável do Microsoft Learn**, lida e transcrita **antes** do código (`backlog.md`, 06/10). `RegraMeta` valida na importação: `url_canonica` precisa começar com `https://`, `termos_consulta` não pode ser vazio, `recomendacao_padrao` precisa de 40 caracteres de texto útil.
- **Nenhuma exclusão por nome de objeto.** Toda exclusão é predicado explícito em TMSL (`escopo.py`). Exceção já existente e única: a identificação de tabela automática de data usa annotation, não nome.
- **Um achado por ocorrência**, nunca agregado (D-4 da spec anterior).
- **O lexer nunca levanta exceção** (D-4). Caractere não reconhecido vira token `DESCONHECIDO`.
- **Expressão com token `DESCONHECIDO` não chega a nenhuma regra** (D-5), e aparece em `lacunas` com sítio, objeto, posição e trecho.
- **Nenhuma afirmação de precisão** entra na monografia ou no `status.md` antes do procedimento de verificação da seção 6 da spec (Tarefa 9).
- Rodar testes com `./.venv/Scripts/python.exe -m pytest` (Windows, venv na raiz).

## Review Focus

Cinco classes de entrada que a spec implica e que nenhuma tarefa exercitaria sem isto. Cada linha tem o teste correspondente embutido na tarefa dona do código.

1. **Expressão DAX vazia ou só comentário.** `Medida.expressao` tem default `""`, e uma medida pode ser só um comentário. O lexer deve devolver lista vazia ou só `COMENTARIO` sem estourar índice. → Tarefa 1, Passo 13.
2. **Comentário ou string não terminados.** `/* sem fechar` e `"sem fechar` no fim da expressão. O lexer não pode entrar em laço infinito nem ler além do fim. → Tarefa 1, Passo 15.
3. **Colchete não fechado.** `Tabela[Coluna` é DAX inválido que pode estar num arquivo salvo com erro. Deve virar `DESCONHECIDO`, e portanto lacuna, não referência silenciosamente truncada. → Tarefa 1, Passo 17.
4. **Coluna homônima em duas tabelas.** `[CustomerKey]` não qualificado existindo em três tabelas — o P8 tem três `GeographyKey`. Resolver para a tabela errada faria a PERF-005 julgar a coluna errada. → Tarefa 6, Passo 7.
5. **`annotations: null` e `source: null`.** Já derrubaram as oito regras de uma vez em 06/10. Os módulos novos leem `variations`, `hierarchies`, `sortByColumn` e `roles`, e qualquer um pode vir `null`. → Tarefa 5, Passo 9.

---

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `core/dax.py` | **novo.** Lexer. Conhece sintaxe de DAX, não conhece modelo |
| `core/rules/expressoes.py` | **novo.** Enumera onde o DAX mora no modelo; devolve expressões tokenizadas e lacunas. Conhece modelo, não conhece sintaxe |
| `core/rules/dax.py` | **novo.** DAX-001 e, se a âncora verificar, DAX-002 |
| `core/rules/performance.py` | **sem mudança** — a PERF-005 foi rejeitada (Tarefa 7) |
| `core/rules/referencias.py` | **novo.** Resolve onde cada coluna é usada, nos oito sítios. Só a PERF-005 usa, mas é o pedaço mais delicado e merece arquivo e teste próprios |
| `core/model.py` | `Hierarquia`, `Nivel`, `Role`, `PermissaoDeTabela`; `Coluna.ordenar_por`; `Tabela.hierarquias`; `ModeloSemantico.roles` |
| `core/parser_bim.py` | Lê hierarquias, `sortByColumn` e roles |
| `core/rules/runner.py` | `lacunas_de_expressao` e `cobertura_de_expressoes` |
| `core/rules/todas.py` | Importa `dax` |
| `tests/conftest.py` | Construtores: `hierarquia`, `nivel`, `role`, e `roles=` em `modelo_tmsl`/`ler` |

**Ordem das tarefas:** 1 (lexer) → 2 (helpers do lexer) → 3 (modelo e parser) → 4 (varredura e lacunas) → 5 (canal de aviso no runner) → 6 (referências) → 7 (**rejeição da PERF-005**) → 8 (DAX-001) → 9 (verificação do rendimento) → 10 (documentos).

**Mudança de escopo em 08/10/2026:** a Tarefa 7 implementava a PERF-005. A medição da Tarefa 6 a rejeitou pela cláusula (c) do terceiro teste — a regra afirma ausência de uso sem poder ler a camada de relatório, onde ~25 das 33 colunas que ela apontaria estão provavelmente em uso. A tarefa passa a registrar a rejeição. **A etapa entrega uma regra nova, a DAX-001**, não duas.

**Bloqueio:** o ramo de RLS da Tarefa 3 e da Tarefa 6 depende da verificação empírica das roles (seção 10 da spec). Enquanto ela não vier, implementar tudo e **deixar a PERF-005 abster-se por completo em modelo com ao menos uma role**, declarando a lacuna. A Tarefa 7 Passo 11 cobre isso.

---

### Task 1: O lexer de DAX

**Files:**
- Create: `core/dax.py`
- Test: `tests/test_dax_lexer.py`

**Interfaces:**
- Consumes: nada. É a base.
- Produces:
  - `class TipoToken(StrEnum)` com os membros `COMENTARIO`, `STRING`, `NUMERO`, `REFERENCIA`, `IDENTIFICADOR`, `OPERADOR`, `PARENTESE_ABRE`, `PARENTESE_FECHA`, `VIRGULA`, `DESCONHECIDO`
  - `class Token(BaseModel)` com `tipo: TipoToken`, `texto: str`, `posicao: int`, `tabela: str | None = None`, `coluna: str | None = None`
  - `def tokenizar(expressao: str | None) -> list[Token]`
  - `def tem_desconhecido(tokens: list[Token]) -> bool`

O `Token.tabela` e `Token.coluna` só são preenchidos em `REFERENCIA`: `Vendas[Total]` dá `tabela="Vendas"`, `coluna="Total"`; `[Total]` dá `tabela=None`, `coluna="Total"`. É assim que medida se distingue de coluna sem consultar o modelo.

- [ ] **Step 1: Write the failing test — operador de divisão**

```python
"""Testes do lexer de DAX.

O lexer existe por medição: 92 das 128 expressões de medida e coluna do P8 têm
comentário `//`. Regex sobre texto bruto casaria o comentário como divisão.
"""

from core.dax import TipoToken, tokenizar


def _tipos(expressao: str) -> list[TipoToken]:
    return [t.tipo for t in tokenizar(expressao)]


def _de(expressao: str, tipo: TipoToken) -> list[str]:
    return [t.texto for t in tokenizar(expressao) if t.tipo == tipo]


def test_divisao_e_operador():
    assert _de("[a] / [b]", TipoToken.OPERADOR) == ["/"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py::test_divisao_e_operador -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.dax'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Lexer de DAX.

Texto entra, tokens saem. Não conhece modelo, tabela nem regra.

**Nunca levanta exceção.** Caractere que não reconhece vira `DESCONHECIDO`, e é
a varredura (`core/rules/expressoes.py`) que decide o que fazer com isso. Essa
escolha é o terceiro teste do critério de detectabilidade em tempo de execução:
uma regra que afirma por ausência não pode alegar varredura exaustiva sobre uma
expressão que não foi tokenizada por completo.

Não constrói AST, não conhece precedência e não valida. Parser sintático é F18,
Trabalhos Futuros — e é o que mantém o grupo 3 de regras fora do MVP.
"""

from enum import StrEnum

from pydantic import BaseModel


class TipoToken(StrEnum):
    COMENTARIO = "comentario"
    STRING = "string"
    NUMERO = "numero"
    REFERENCIA = "referencia"
    IDENTIFICADOR = "identificador"
    OPERADOR = "operador"
    PARENTESE_ABRE = "parentese_abre"
    PARENTESE_FECHA = "parentese_fecha"
    VIRGULA = "virgula"
    DESCONHECIDO = "desconhecido"


class Token(BaseModel):
    tipo: TipoToken
    texto: str
    posicao: int
    tabela: str | None = None
    """Só em `REFERENCIA`, e `None` quando a referência é uma medida."""
    coluna: str | None = None
    """Só em `REFERENCIA`: o nome dentro dos colchetes."""


OPERADORES = ("<>", "<=", ">=", "||", "&&", "+", "-", "*", "/", "^", "&", "=", "<", ">")
"""Os de dois caracteres vêm primeiro: a busca é por prefixo, e `<=` precisa
ganhar de `<`."""


def tokenizar(expressao: str | None) -> list[Token]:
    """Quebra uma expressão DAX em tokens. Nunca levanta exceção."""
    texto = expressao or ""
    tokens: list[Token] = []
    i = 0

    while i < len(texto):
        c = texto[i]

        if c in " \t\r\n":
            i += 1
            continue

        if c == "/" and texto.startswith("//", i):
            fim = texto.find("\n", i)
            fim = len(texto) if fim == -1 else fim
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue

        for simbolo in OPERADORES:
            if texto.startswith(simbolo, i):
                tokens.append(Token(tipo=TipoToken.OPERADOR, texto=simbolo, posicao=i))
                i += len(simbolo)
                break
        else:
            tokens.append(Token(tipo=TipoToken.DESCONHECIDO, texto=c, posicao=i))
            i += 1

    return tokens
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py::test_divisao_e_operador -v`
Expected: PASS

- [ ] **Step 5: Write the failing test — as três formas de comentário**

```python
def test_comentario_de_duas_barras_nao_e_divisao():
    """O sósia medido: 92 das 128 expressões do P8 têm `//`."""
    assert _de("[a] // isto / aquilo", TipoToken.OPERADOR) == []
    assert _de("[a] // isto / aquilo", TipoToken.COMENTARIO) == ["// isto / aquilo"]


def test_comentario_de_dois_tracos():
    assert _de("[a] -- nota", TipoToken.COMENTARIO) == ["-- nota"]
    assert _de("[a] -- nota", TipoToken.OPERADOR) == []


def test_comentario_em_bloco():
    assert _de("[a] /* nota / com barra */ + [b]", TipoToken.COMENTARIO) == [
        "/* nota / com barra */"
    ]
    assert _de("[a] /* nota */ + [b]", TipoToken.OPERADOR) == ["+"]


def test_comentario_de_linha_termina_na_quebra():
    """A divisão da linha seguinte precisa sobreviver ao comentário da primeira."""
    assert _de("// nota\n[a] / [b]", TipoToken.OPERADOR) == ["/"]
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v -k comentario`
Expected: FAIL — `--` vira dois `OPERADOR` e `/*` vira `OPERADOR` de `/`

- [ ] **Step 7: Implement the three comment forms**

Em `tokenizar`, **antes** do laço de operadores, acrescentar `--` e `/* */`. O trecho de `//` já existe; o de `--` segue a mesma forma:

```python
        if texto.startswith("--", i):
            fim = texto.find("\n", i)
            fim = len(texto) if fim == -1 else fim
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue

        if texto.startswith("/*", i):
            fechamento = texto.find("*/", i + 2)
            # Bloco sem fechar: consome até o fim. É DAX inválido, mas o lexer
            # não valida — e não pode ler além do fim nem repetir a posição.
            fim = len(texto) if fechamento == -1 else fechamento + 2
            tokens.append(Token(tipo=TipoToken.COMENTARIO, texto=texto[i:fim], posicao=i))
            i = fim
            continue
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: PASS, 5 testes

- [ ] **Step 9: Commit**

```bash
git add core/dax.py tests/test_dax_lexer.py
git commit -m "feat(dax): lexer com operadores e as tres formas de comentario"
```

- [ ] **Step 10: Write the failing test — string, número, parêntese, vírgula, identificador**

```python
def test_string_com_aspas_literais():
    """`""` dentro de string é uma aspa, não o fim dela."""
    assert _de('"a""b"', TipoToken.STRING) == ['"a""b"']


def test_barra_dentro_de_string_nao_e_divisao():
    assert _de('"km/h"', TipoToken.OPERADOR) == []
    assert _de('"km/h"', TipoToken.STRING) == ['"km/h"']


def test_numero_inteiro_e_decimal():
    assert _de("1 + 2.5", TipoToken.NUMERO) == ["1", "2.5"]


def test_chamada_de_funcao():
    assert _tipos("SUM([a])") == [
        TipoToken.IDENTIFICADOR,
        TipoToken.PARENTESE_ABRE,
        TipoToken.REFERENCIA,
        TipoToken.PARENTESE_FECHA,
    ]


def test_virgula_separa_argumentos():
    assert _de("DIVIDE([a], [b])", TipoToken.VIRGULA) == [","]
```

- [ ] **Step 11: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: FAIL — aspas, dígitos, letras e parênteses viram `DESCONHECIDO`

- [ ] **Step 12: Implement string, number, parenthesis, comma, identifier and reference**

Acrescentar antes do laço de operadores, nesta ordem:

```python
        if c == '"':
            j = i + 1
            while j < len(texto):
                if texto[j] == '"':
                    if texto.startswith('""', j):   # aspa literal
                        j += 2
                        continue
                    j += 1
                    break
                j += 1
            else:
                # String sem fechar: consome até o fim, sem estourar o índice.
                j = len(texto)
            tokens.append(Token(tipo=TipoToken.STRING, texto=texto[i:j], posicao=i))
            i = j
            continue

        if c.isdigit():
            j = i
            while j < len(texto) and (texto[j].isdigit() or texto[j] == "."):
                j += 1
            tokens.append(Token(tipo=TipoToken.NUMERO, texto=texto[i:j], posicao=i))
            i = j
            continue

        if c == "(":
            tokens.append(Token(tipo=TipoToken.PARENTESE_ABRE, texto=c, posicao=i))
            i += 1
            continue

        if c == ")":
            tokens.append(Token(tipo=TipoToken.PARENTESE_FECHA, texto=c, posicao=i))
            i += 1
            continue

        if c == ",":
            tokens.append(Token(tipo=TipoToken.VIRGULA, texto=c, posicao=i))
            i += 1
            continue

        if c == "[" or c == "'" or c.isalpha() or c == "_":
            token, i = _referencia_ou_identificador(texto, i)
            tokens.append(token)
            continue
```

E a função de referência, que é o coração do lexer:

```python
def _nome_entre(texto: str, i: int, abre: str, fecha: str) -> tuple[str | None, int]:
    """Lê `[nome]` ou `'nome'`, tratando o fechamento duplicado como literal.

    Devolve `(None, i)` quando o delimitador não fecha — o chamador transforma
    isso em `DESCONHECIDO`, e portanto em lacuna declarada. Nome truncado em
    silêncio seria pior: a PERF-005 concluiria ausência de referência a partir
    de um nome que ela própria cortou.
    """
    j = i + 1
    partes: list[str] = []
    while j < len(texto):
        if texto[j] == fecha:
            if texto.startswith(fecha * 2, j):
                partes.append(fecha)
                j += 2
                continue
            return "".join(partes), j + 1
        partes.append(texto[j])
        j += 1
    return None, i


def _referencia_ou_identificador(texto: str, i: int) -> tuple[Token, int]:
    """`[Medida]`, `Tabela[Coluna]`, `'Com espaço'[Coluna]` ou nome de função."""
    inicio = i

    if texto[i] == "[":
        coluna, fim = _nome_entre(texto, i, "[", "]")
        if coluna is None:
            return Token(tipo=TipoToken.DESCONHECIDO, texto=texto[i], posicao=i), i + 1
        return (
            Token(
                tipo=TipoToken.REFERENCIA,
                texto=texto[inicio:fim],
                posicao=inicio,
                tabela=None,
                coluna=coluna,
            ),
            fim,
        )

    if texto[i] == "'":
        tabela, fim = _nome_entre(texto, i, "'", "'")
        if tabela is None:
            return Token(tipo=TipoToken.DESCONHECIDO, texto=texto[i], posicao=i), i + 1
    else:
        fim = i
        while fim < len(texto) and (texto[fim].isalnum() or texto[fim] == "_"):
            fim += 1
        tabela = texto[i:fim]

    if fim < len(texto) and texto[fim] == "[":
        coluna, depois = _nome_entre(texto, fim, "[", "]")
        if coluna is None:
            return Token(tipo=TipoToken.DESCONHECIDO, texto=texto[fim], posicao=fim), fim + 1
        return (
            Token(
                tipo=TipoToken.REFERENCIA,
                texto=texto[inicio:depois],
                posicao=inicio,
                tabela=tabela,
                coluna=coluna,
            ),
            depois,
        )

    # Nome nu: função (`SUM`) ou tabela como argumento (`FILTER(Vendas, …)`).
    return (
        Token(tipo=TipoToken.IDENTIFICADOR, texto=texto[inicio:fim], posicao=inicio),
        fim,
    )
```

E a função de conveniência:

```python
def tem_desconhecido(tokens: list[Token]) -> bool:
    """A expressão não foi tokenizada por completo."""
    return any(t.tipo is TipoToken.DESCONHECIDO for t in tokens)
```

- [ ] **Step 13: Run tests, and add the Review Focus test for empty expression**

```python
def test_expressao_vazia_ou_so_comentario():
    """`Medida.expressao` tem default "" e uma medida pode ser só um comentário."""
    assert tokenizar("") == []
    assert tokenizar(None) == []
    assert tokenizar("   \n  ") == []
    assert _tipos("// só um comentário") == [TipoToken.COMENTARIO]
```

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: PASS

- [ ] **Step 14: Write the failing test — referência**

```python
def test_referencia_de_coluna_qualificada():
    t = tokenizar("Vendas[Total]")[0]
    assert (t.tipo, t.tabela, t.coluna) == (TipoToken.REFERENCIA, "Vendas", "Total")


def test_referencia_de_medida_nao_tem_tabela():
    """É assim que medida se distingue de coluna sem consultar o modelo."""
    t = tokenizar("[Receita Total]")[0]
    assert (t.tipo, t.tabela, t.coluna) == (TipoToken.REFERENCIA, None, "Receita Total")


def test_tabela_com_espaco_entre_apostrofos():
    t = tokenizar("'Tabela de Regressão Linear'[Previsao]")[0]
    assert (t.tabela, t.coluna) == ("Tabela de Regressão Linear", "Previsao")


def test_apostrofo_literal_no_nome_da_tabela():
    t = tokenizar("'O''Brien'[Coluna]")[0]
    assert t.tabela == "O'Brien"


def test_barra_dentro_de_colchete_nao_e_divisao():
    """`[Receita/Custo]` é um nome, não uma divisão."""
    assert _de("[Receita/Custo]", TipoToken.OPERADOR) == []
    assert tokenizar("[Receita/Custo]")[0].coluna == "Receita/Custo"
```

- [ ] **Step 15: Run tests, and add the Review Focus test for unterminated comment and string**

```python
def test_comentario_em_bloco_sem_fechar_nao_entra_em_laco():
    """DAX inválido num arquivo salvo com erro. O lexer consome até o fim."""
    tokens = tokenizar("[a] + /* sem fechar")
    assert tokens[-1].tipo is TipoToken.COMENTARIO
    assert tokens[-1].texto == "/* sem fechar"


def test_string_sem_fechar_nao_estoura_indice():
    tokens = tokenizar('[a] + "sem fechar')
    assert tokens[-1].tipo is TipoToken.STRING
    assert tokens[-1].texto == '"sem fechar'
```

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: PASS

- [ ] **Step 16: Commit**

```bash
git add core/dax.py tests/test_dax_lexer.py
git commit -m "feat(dax): string, numero, referencia e identificador"
```

- [ ] **Step 17: Write the failing test — Review Focus: colchete não fechado**

```python
def test_colchete_sem_fechar_vira_desconhecido():
    """Nome truncado em silêncio seria pior que lacuna declarada.

    A PERF-005 afirma por ausência: se o lexer cortasse `Tabela[Coluna` em
    `Coluna`, ela concluiria ausência de referência a partir de um nome que ela
    própria mutilou. `DESCONHECIDO` faz a expressão virar lacuna, e a regra se
    cala sobre ela.
    """
    from core.dax import tem_desconhecido

    assert tem_desconhecido(tokenizar("Vendas[Total")) is True
    assert tem_desconhecido(tokenizar("[Total")) is True
    assert tem_desconhecido(tokenizar("'Tabela[Coluna]")) is True
    assert tem_desconhecido(tokenizar("Vendas[Total]")) is False


def test_caractere_estranho_vira_desconhecido():
    from core.dax import tem_desconhecido

    assert tem_desconhecido(tokenizar("[a] § [b]")) is True
```

- [ ] **Step 18: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: PASS. Se falhar, `_nome_entre` está devolvendo nome truncado em vez de `None`.

- [ ] **Step 19: Write the coverage test against the real corpus**

Em `tests/test_pbip_real.py`, junto dos que já existem:

```python
def test_o_lexer_tokeniza_todo_o_dax_do_p8(modelo):
    """Critério de aceite 1: zero token DESCONHECIDO nas expressões do P8.

    Mede a cobertura do lexer contra um corpus real em vez de contra a
    imaginação de quem o escreveu. É o número que a monografia cita no lugar de
    "usamos expressões regulares".
    """
    from core.dax import tem_desconhecido, tokenizar

    textos = []
    for t in modelo.tabelas:
        textos += [m.expressao for m in t.medidas]
        textos += [c.expressao for c in t.colunas if c.expressao]
        textos += [
            p.origem for p in t.particoes if p.tipo_origem == "calculated" and p.origem
        ]

    assert len(textos) == 137
    falhas = [x for x in textos if tem_desconhecido(tokenizar(x))]
    assert falhas == []
```

- [ ] **Step 20: Run the test**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pbip_real.py -v -k lexer`
Expected: PASS. **Se falhar**, não corrigir o teste: cada expressão em `falhas` é um caractere de DAX que o lexer não cobre. Acrescentar o tratamento e um teste unitário para ele, e só então rodar de novo. O número 137 e a lista vazia são o critério de aceite 1.

- [ ] **Step 21: Commit**

```bash
git add core/dax.py tests/test_dax_lexer.py tests/test_pbip_real.py
git commit -m "test(dax): o lexer cobre as 137 expressoes do P8 sem token desconhecido"
```

---

### Task 2: Helpers do lexer para as regras

**Files:**
- Modify: `core/dax.py`
- Test: `tests/test_dax_lexer.py`

**Interfaces:**
- Consumes: `Token`, `TipoToken`, `tokenizar` da Tarefa 1.
- Produces:
  - `def referencias(tokens: list[Token]) -> list[Token]`
  - `def operadores(tokens: list[Token], simbolo: str) -> list[Token]`
  - `def chamadas(tokens: list[Token], nome: str) -> list[list[list[Token]]]` — para cada chamada da função, a lista dos seus argumentos; cada argumento é uma lista de tokens

`chamadas` existe para a DAX-002, que precisa de **fronteira de argumento**: `FILTER(Vendas, …)` só é achado se o primeiro argumento for uma tabela nua, e isso exige saber onde o argumento começa e termina. A profundidade de parêntese é o que o lexer entrega e a regex não entregaria.

- [ ] **Step 1: Write the failing test**

```python
def test_referencias_ignora_comentario_e_string():
    from core.dax import referencias

    tokens = tokenizar('Vendas[Total] // Vendas[Oculto]\n+ "Vendas[Falso]"')
    assert [(t.tabela, t.coluna) for t in referencias(tokens)] == [("Vendas", "Total")]


def test_operadores_conta_so_o_simbolo_pedido():
    from core.dax import operadores

    tokens = tokenizar("[a] / [b] + [c] / [d]")
    assert len(operadores(tokens, "/")) == 2
    assert len(operadores(tokens, "+")) == 1


def test_chamadas_separa_os_argumentos():
    from core.dax import chamadas

    args = chamadas(tokenizar("DIVIDE([a], [b])"), "DIVIDE")
    assert len(args) == 1
    assert [len(a) for a in args[0]] == [1, 1]


def test_chamadas_respeita_parenteses_aninhados():
    """A vírgula de dentro pertence ao argumento, não à chamada de fora."""
    from core.dax import chamadas

    args = chamadas(tokenizar("SUMX(Vendas, DIVIDE([a], [b]))"), "SUMX")
    assert len(args[0]) == 2
    assert args[0][0][0].texto == "Vendas"


def test_chamadas_e_insensivel_a_caixa():
    from core.dax import chamadas

    assert len(chamadas(tokenizar("divide([a],[b])"), "DIVIDE")) == 1


def test_chamadas_sem_a_funcao_devolve_vazio():
    from core.dax import chamadas

    assert chamadas(tokenizar("SUM([a])"), "FILTER") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v -k "referencias or operadores or chamadas"`
Expected: FAIL com `ImportError: cannot import name 'referencias'`

- [ ] **Step 3: Write the implementation**

```python
def referencias(tokens: list[Token]) -> list[Token]:
    """Só as referências. Comentário e string já são outros tipos de token."""
    return [t for t in tokens if t.tipo is TipoToken.REFERENCIA]


def operadores(tokens: list[Token], simbolo: str) -> list[Token]:
    return [t for t in tokens if t.tipo is TipoToken.OPERADOR and t.texto == simbolo]


def chamadas(tokens: list[Token], nome: str) -> list[list[list[Token]]]:
    """Para cada chamada de `nome`, a lista dos seus argumentos.

    A fronteira de argumento sai da profundidade de parêntese: uma vírgula só
    separa argumentos desta chamada quando a profundidade é 1. É o que uma
    expressão regular não consegue fazer, e o motivo de a DAX-002 depender do
    lexer.
    """
    alvo = nome.upper()
    resultado: list[list[list[Token]]] = []

    for i, t in enumerate(tokens):
        if t.tipo is not TipoToken.IDENTIFICADOR or t.texto.upper() != alvo:
            continue
        if i + 1 >= len(tokens) or tokens[i + 1].tipo is not TipoToken.PARENTESE_ABRE:
            continue

        argumentos: list[list[Token]] = []
        atual: list[Token] = []
        profundidade = 0

        for u in tokens[i + 1 :]:
            if u.tipo is TipoToken.PARENTESE_ABRE:
                profundidade += 1
                if profundidade == 1:
                    continue
            elif u.tipo is TipoToken.PARENTESE_FECHA:
                profundidade -= 1
                if profundidade == 0:
                    argumentos.append(atual)
                    break
            elif u.tipo is TipoToken.VIRGULA and profundidade == 1:
                argumentos.append(atual)
                atual = []
                continue
            atual.append(u)
        else:
            # Parêntese sem fechar. Não inventa argumento: a expressão terá
            # token DESCONHECIDO ou virará lacuna por outro caminho.
            continue

        resultado.append(argumentos)

    return resultado
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_dax_lexer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/dax.py tests/test_dax_lexer.py
git commit -m "feat(dax): helpers de referencia, operador e fronteira de argumento"
```

---

### Task 3: Modelo e parser — hierarquias, sortByColumn e roles

**Files:**
- Modify: `core/model.py`, `core/parser_bim.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_parser_bim.py`

**Interfaces:**
- Consumes: as classes existentes de `core/model.py`.
- Produces:
  - `class Nivel(BaseModel)`: `nome: str`, `tabela: str`, `coluna: str`, `ordem: int | None`
  - `class Hierarquia(BaseModel)`: `nome: str`, `tabela: str`, `niveis: list[Nivel]`
  - `class PermissaoDeTabela(BaseModel)`: `tabela: str`, `expressao_filtro: str | None`
  - `class Role(BaseModel)`: `nome: str`, `permissoes: list[PermissaoDeTabela]`
  - `Coluna.ordenar_por: str | None` (o `sortByColumn`)
  - `Tabela.hierarquias: list[Hierarquia]`
  - `ModeloSemantico.roles: list[Role]`
  - Construtores de teste `hierarquia(...)`, `nivel(...)`, `role(...)`, e `roles=` em `modelo_tmsl` e na fixture `ler`

Esses são os sítios que o terceiro teste obriga a ler. Sítio não lido é prova de ausência que não existe.

- [ ] **Step 1: Write the failing test**

```python
def test_le_sort_by_column():
    """10 colunas do P8 ordenam por outra coluna. Esquecer isso faria a
    PERF-005 recomendar apagar a coluna de ordenação."""
    modelo = ler(
        tabelas=[
            tabela(
                "DimDate",
                colunas=[
                    coluna("MesNome", ordenar_por="MesNumero"),
                    coluna("MesNumero", tipo_dado="int64"),
                ],
            )
        ]
    )

    assert modelo.tabelas[0].colunas[0].ordenar_por == "MesNumero"
    assert modelo.tabelas[0].colunas[1].ordenar_por is None


def test_le_hierarquias_e_seus_niveis():
    modelo = ler(
        tabelas=[
            tabela(
                "DimProduct",
                colunas=[coluna("Categoria"), coluna("Produto")],
                hierarquias=[
                    hierarquia(
                        "Produtos",
                        niveis=[nivel("Categoria", "Categoria"), nivel("Produto", "Produto")],
                    )
                ],
            )
        ]
    )

    h = modelo.tabelas[0].hierarquias[0]
    assert h.nome == "Produtos"
    assert [n.coluna for n in h.niveis] == ["Categoria", "Produto"]
    assert h.niveis[0].tabela == "DimProduct"


def test_le_roles_com_expressao_de_filtro():
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro="[Regiao] = \"Sul\"")],
    )

    assert modelo.roles[0].nome == "Vendedor"
    assert modelo.roles[0].permissoes[0].tabela == "Vendas"
    assert modelo.roles[0].permissoes[0].expressao_filtro == '[Regiao] = "Sul"'


def test_modelo_sem_roles_tem_lista_vazia():
    """O P8 não tem a chave `roles`. Ausência não pode virar None."""
    modelo = ler(tabelas=[tabela("Vendas")])
    assert modelo.roles == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_parser_bim.py -v -k "sort or hierarqu or role"`
Expected: FAIL com `TypeError: coluna() got an unexpected keyword argument 'ordenar_por'`

- [ ] **Step 3: Extend the test builders in `tests/conftest.py`**

Em `coluna(...)`, acrescentar o parâmetro e o campo:

```python
def coluna(
    nome: str,
    *,
    tipo_dado: str = "string",
    tipo: str | None = None,
    expressao: str | None = None,
    resumir_por: str = "none",
    oculta: bool = False,
    annotations: dict[str, str] | None = None,
    variacao_para: str | None = None,
    ordenar_por: str | None = None,
) -> dict:
```

e, junto dos outros opcionais:

```python
    if ordenar_por is not None:
        bruto["sortByColumn"] = ordenar_por
```

Construtores novos:

```python
def nivel(nome: str, coluna_de: str, *, ordem: int | None = None) -> dict:
    """Um nível de hierarquia. `coluna_de` é o nome da coluna que ele usa."""
    bruto: dict = {"name": nome, "column": coluna_de}
    if ordem is not None:
        bruto["ordinal"] = ordem
    return bruto


def hierarquia(nome: str, *, niveis: list[dict] | tuple = ()) -> dict:
    return {"name": nome, "levels": list(niveis)}


def role(nome: str, *, tabela: str, filtro: str) -> dict:
    """Uma role de RLS com uma permissão de tabela e sua expressão de filtro."""
    return {
        "name": nome,
        "modelPermission": "read",
        "tablePermissions": [{"name": tabela, "filterExpression": filtro}],
    }
```

Em `tabela(...)`, acrescentar `hierarquias`:

```python
def tabela(
    nome: str,
    *,
    colunas: list[dict] | tuple = (),
    medidas: list[dict] | tuple = (),
    particoes: list[dict] | tuple = (),
    hierarquias: list[dict] | tuple = (),
    data_category: str | None = None,
    annotations: dict[str, str] | None = None,
) -> dict:
```

e, dentro do dicionário:

```python
    if hierarquias:
        bruto["hierarchies"] = list(hierarquias)
```

Em `modelo_tmsl` e na fixture `ler`, acrescentar `roles`:

```python
def modelo_tmsl(tabelas=(), relacionamentos=(), roles=()) -> dict:
    model: dict = {
        "culture": "pt-BR",
        "tables": list(tabelas),
        "relationships": list(relacionamentos),
    }
    if roles:
        model["roles"] = list(roles)
    return {"name": "SemanticModel", "compatibilityLevel": 1600, "model": model}
```

```python
    def _ler(tabelas=(), relacionamentos=(), roles=()) -> ModeloSemantico:
        caminho = tmp_path / "model.bim"
        caminho.write_text(
            json.dumps(
                modelo_tmsl(tabelas, relacionamentos, roles), ensure_ascii=False
            ),
            encoding="utf-8",
        )
        return ler_modelo(caminho)
```

- [ ] **Step 4: Extend `core/model.py`**

```python
class Nivel(BaseModel):
    """Um nível de hierarquia. Referencia uma coluna da própria tabela."""

    nome: str
    tabela: str
    coluna: str
    ordem: int | None = None


class Hierarquia(BaseModel):
    nome: str
    tabela: str
    niveis: list[Nivel] = Field(default_factory=list)


class PermissaoDeTabela(BaseModel):
    tabela: str
    expressao_filtro: str | None = None
    """DAX da RLS. Referencia colunas, e por isso conta como uso de coluna."""


class Role(BaseModel):
    """Role de segurança em nível de linha."""

    nome: str
    permissoes: list[PermissaoDeTabela] = Field(default_factory=list)
```

Em `Coluna`, acrescentar:

```python
    ordenar_por: str | None = None
    """`sortByColumn`: a coluna que define a ordem desta. Conta como uso da
    coluna apontada — esquecer isso faria a PERF-005 recomendar apagar a coluna
    de ordenação, quebrando a ordem no relatório."""
```

Em `Tabela`, acrescentar `hierarquias: list[Hierarquia] = Field(default_factory=list)`.
Em `ModeloSemantico`, acrescentar `roles: list[Role] = Field(default_factory=list)`.

Corrigir também a docstring de `Particao.origem`, hoje enganosa:

```python
    origem: str | None = None
    """Expressão da partição: M quando `tipo_origem == "m"`, DAX quando
    `tipo_origem == "calculated"`. O campo carrega as duas, e quem lê precisa
    olhar `tipo_origem` antes — uma regra de DAX que varresse toda partição
    leria as 10 expressões M do P8."""
```

- [ ] **Step 5: Extend `core/parser_bim.py`**

```python
def _nivel(bruto: dict, tabela: str) -> Nivel:
    return Nivel(
        nome=bruto.get("name", ""),
        tabela=tabela,
        coluna=bruto.get("column", ""),
        ordem=bruto.get("ordinal"),
    )


def _hierarquia(bruto: dict, tabela: str) -> Hierarquia:
    return Hierarquia(
        nome=bruto.get("name", ""),
        tabela=tabela,
        niveis=[_nivel(n, tabela) for n in bruto.get("levels") or []],
    )


def _role(bruto: dict) -> Role:
    return Role(
        nome=bruto.get("name", ""),
        permissoes=[
            PermissaoDeTabela(
                tabela=p.get("name", ""),
                expressao_filtro=_texto(p.get("filterExpression")),
            )
            for p in bruto.get("tablePermissions") or []
        ],
    )
```

Em `_coluna`, acrescentar `ordenar_por=bruto.get("sortByColumn")`.
Em `_tabela`, acrescentar `hierarquias=[_hierarquia(h, nome) for h in bruto.get("hierarchies") or []]`.
Em `ler_modelo`, acrescentar `roles=[_role(r) for r in model.get("roles") or []]`.

O `or []` em cada um não é adorno: `"annotations": null` derrubou as oito regras de uma vez em 06/10, e `hierarchies`, `levels`, `tablePermissions` e `roles` podem vir `null` do mesmo jeito.

- [ ] **Step 6: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_parser_bim.py -v`
Expected: PASS

- [ ] **Step 7: Run the whole suite — nothing may regress**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: 101 testes anteriores + os novos, todos passando. Em particular `test_as_contagens_por_regra_no_p8` continua em 15 achados.

- [ ] **Step 8: Add the P8 inventory test for the new sites**

Em `tests/test_pbip_real.py`:

```python
def test_inventario_dos_sitios_estruturais(modelo):
    """Os sítios que a PERF-005 precisa varrer, medidos no P8 em 08/10/2026."""
    niveis = [n for t in modelo.tabelas for h in t.hierarquias for n in h.niveis]
    ordenacoes = [c for t in modelo.tabelas for c in t.colunas if c.ordenar_por]

    assert len(modelo.relacionamentos) == 11
    assert sum(len(t.hierarquias) for t in modelo.tabelas) == 4
    assert len(niveis) == 16
    assert len(ordenacoes) == 10
    assert modelo.roles == []
```

- [ ] **Step 9: Run it and commit**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pbip_real.py -v -k sitios`
Expected: PASS

```bash
git add core/model.py core/parser_bim.py tests/conftest.py tests/test_parser_bim.py tests/test_pbip_real.py
git commit -m "feat(model): hierarquias, sortByColumn e roles de RLS"
```

---

### Task 4: A varredura e as lacunas

**Files:**
- Modify: `core/rules/escopo.py` — a distincao que falta (Passos 0a a 0c)
- Create: `core/rules/expressoes.py`
- Test: `tests/test_rules_escopo.py`, `tests/test_rules_expressoes.py`

**Interfaces:**
- Consumes: `tokenizar`, `tem_desconhecido`, `Token` (Tarefa 1); `Role` de `core/model.py` (Tarefa 3); os predicados de `core/rules/escopo.py`.
- Produces:
  - `def dax_escrito_pela_ferramenta(t: Tabela) -> bool` (em `escopo.py`)
  - `def tabelas_com_dax_do_autor(modelo: ModeloSemantico) -> list[Tabela]` (em `escopo.py`)
  - `class ExpressaoDax(BaseModel)`: `sitio: str`, `objeto: str`, `tabela: str | None`, `texto: str`, `tokens: list[Token]`
  - `class LacunaDax(BaseModel)`: `sitio: str`, `objeto: str`, `tabela: str | None`, `posicao: int`, `trecho: str`, `motivo: str`
  - `class VarreduraDax(BaseModel)`: `expressoes: list[ExpressaoDax]`, `lacunas: list[LacunaDax]`
  - `def varrer_dax(modelo: ModeloSemantico) -> VarreduraDax`

Os valores de `sitio`: `"medida"`, `"coluna calculada"`, `"particao calculada"`, `"role"`.

#### Correcao de 08/10/2026: a varredura nao pode usar `tabelas_em_escopo`

A primeira versao desta tarefa filtrava as expressoes por `tabelas_em_escopo`, e isso estava **errado**. Medido contra o PBIP real: a varredura veria **12** expressoes em vez de **105** — cegueira para 89% do DAX que o autor escreveu.

A causa e que `fora_de_escopo` junta num mesmo `or` quatro predicados de **duas naturezas diferentes**, e ate agora isso nao importava porque toda regra era de nivel de tabela:

| Natureza | Predicado | A varredura de DAX deve excluir? |
|---|---|---|
| O **DAX e escrito pela ferramenta** | `tabela_automatica_de_data` | **Sim** |
| | `tabela_gerada_por_analise` (cluster, agrupamento) | **Sim** |
| | `tabela_de_parametro_hipotetico` | **Sim** — o Desktop escreve a medida (`% Previsao = SELECTEDVALUE(...)`), nao o autor |
| **Padrao legitimo do autor**, sem relacionamento por natureza | `tabela_apenas_de_medidas` | **Nao** — o autor escreveu as 92 medidas que estao la |

No P8 a tabela `_Medidas` carrega **93 das 105 expressoes**. Exclui-la da auditoria de DAX seria deixar de ler quase todo o DAX do modelo.

`fora_de_escopo` e `tabelas_em_escopo` **nao mudam**: as 8 regras existentes as usam e as 15 ocorrencias do P8 estao travadas em teste. A distincao entra como funcao nova.

**Isso tambem resolve, sem tocar em predicado nenhum,** o segundo defeito encontrado: `tabela_apenas_de_medidas` devolve `True` para tabela com zero colunas e uma medida (`all()` sobre lista vazia e `True`), o que fazia a fixture `tabela("Vendas", medidas=[...])` sair de escopo. Com `dax_escrito_pela_ferramenta` ela entra, porque nao e nenhuma das tres.

- [ ] **Step 0a: Write the failing test for the scope split**

Em `tests/test_rules_escopo.py`:

```python
def test_dax_do_autor_inclui_a_tabela_so_de_medidas(ler):
    """A tabela de medidas sai das regras de nivel de tabela, nao da auditoria de DAX.

    Ela nao tem relacionamento por natureza, e e por isso que `fora_de_escopo` a
    exclui — nao porque seu DAX seja de outra pessoa. No PBIP real ela carrega
    93 das 105 expressoes do modelo.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
            )
        ]
    )
    t = modelo.tabelas[0]

    assert tabela_apenas_de_medidas(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is False
    assert [x.nome for x in tabelas_com_dax_do_autor(modelo)] == ["_Medidas"]


def test_dax_do_autor_exclui_tabela_de_data_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "LocalDateTable_x",
                colunas=[coluna("Trim", tipo="calculated", expressao="INT([Mes]/3)")],
                annotations={"__PBI_LocalDateTable": "true"},
            )
        ]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []


def test_dax_do_autor_exclui_tabela_de_cluster(ler):
    modelo = ler(
        tabelas=[tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "x"})]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []


def test_dax_do_autor_exclui_parametro_hipotetico(ler):
    """O Desktop escreve a medida do parametro hipotetico, nao o autor.

    No P8: `% Previsao = SELECTEDVALUE('Parametro'[Parametro])`, gerada pelo
    recurso de parametro hipotetico junto com a tabela.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Parametro",
                colunas=[coluna("Parametro", tipo="calculatedTableColumn")],
                medidas=[medida("Valor", "SELECTEDVALUE(Parametro[Parametro])")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.1)")],
            )
        ]
    )

    assert dax_escrito_pela_ferramenta(modelo.tabelas[0]) is True
    assert tabelas_com_dax_do_autor(modelo) == []
```

Acrescentar `dax_escrito_pela_ferramenta` e `tabelas_com_dax_do_autor` ao import de `escopo` no topo do arquivo de teste.

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_escopo.py -v -k dax_do_autor`
Expected: FAIL com `ImportError: cannot import name 'dax_escrito_pela_ferramenta'`

- [ ] **Step 0b: Implement the scope split in `core/rules/escopo.py`**

Acrescentar depois de `tabelas_em_escopo`, **sem tocar** em `fora_de_escopo` nem em `tabelas_em_escopo`:

```python
def dax_escrito_pela_ferramenta(t: Tabela) -> bool:
    """O DAX desta tabela foi escrito pelo Power BI, nao pelo autor.

    Distincao que `fora_de_escopo` nao faz, porque ate aqui toda regra era de
    nivel de tabela. Aquele predicado junta duas naturezas de exclusao:

    - **o DAX e da ferramenta** — tabela de data automatica, tabela de cluster, e
      a tabela de parametro hipotetico, cuja medida o Desktop escreve junto com
      a tabela (`% Previsao = SELECTEDVALUE(...)`);
    - **padrao legitimo do autor** — a tabela que so carrega medidas, excluida
      apenas por nao ter relacionamento por natureza.

    So a primeira natureza vale para uma regra que le texto DAX. No PBIP real a
    tabela de medidas carrega 93 das 105 expressoes do modelo: trata-la como
    fora de escopo deixaria a auditoria de DAX cega para quase tudo.
    """
    return (
        tabela_automatica_de_data(t)
        or tabela_gerada_por_analise(t)
        or tabela_de_parametro_hipotetico(t)
    )


def tabelas_com_dax_do_autor(modelo: ModeloSemantico) -> list[Tabela]:
    """Tabelas cujo DAX o autor escreveu. E o escopo das regras de texto.

    Difere de `tabelas_em_escopo` apenas pela tabela que so carrega medidas, que
    aqui **entra**.
    """
    return [t for t in modelo.tabelas if not dax_escrito_pela_ferramenta(t)]
```

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_escopo.py -v`
Expected: PASS, e os testes de escopo que ja existiam continuam passando — `fora_de_escopo` nao foi tocado.

- [ ] **Step 0c: Commit the scope split**

```bash
git add core/rules/escopo.py tests/test_rules_escopo.py
git commit -m "feat(rules): separa o DAX da ferramenta do DAX do autor"
```

- [ ] **Step 1: Write the failing test**

```python
"""Testes da varredura de expressões DAX."""

from tests.conftest import coluna, medida, particao, role, tabela


def test_varre_medida_coluna_calculada_e_particao_calculada(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Margem", tipo="calculated", expressao="[a] - [b]")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(1,2)")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert {e.sitio for e in v.expressoes} == {
        "medida",
        "coluna calculada",
        "particao calculada",
    }
    assert v.lacunas == []


def test_nao_varre_particao_m(ler):
    """10 das 19 partições do P8 são M. `/` em caminho de arquivo não é divisão."""
    modelo = ler(
        tabelas=[
            tabela("Vendas", particoes=[particao(tipo="m", expressao='Csv.Document("c:/x")')])
        ]
    )

    assert varrer_dax(modelo).expressoes == []


def test_respeita_as_exclusoes_de_escopo(ler):
    """Tabela de data automática não entra: auditar o que o autor escreveu."""
    modelo = ler(
        tabelas=[
            tabela(
                "LocalDateTable_x",
                colunas=[coluna("Trim", tipo="calculated", expressao="INT([Mes]/3)")],
                annotations={"__PBI_LocalDateTable": "true"},
            )
        ]
    )

    assert varrer_dax(modelo).expressoes == []


def test_objeto_vem_qualificado(ler):
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Total", "1")])])

    assert varrer_dax(modelo).expressoes[0].objeto == "Vendas[Total]"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_expressoes.py -v`
Expected: FAIL com `NameError: name 'varrer_dax' is not defined`

- [ ] **Step 3: Write the implementation**

```python
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

from core.dax import Token, tem_desconhecido, tokenizar
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
            primeiro = next(t for t in tokens if tem_desconhecido([t]))
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
```

Acrescentar o import no topo do arquivo de teste:

```python
from core.rules.expressoes import varrer_dax
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_expressoes.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test — a lacuna e a conta que fecha**

```python
def test_expressao_com_caractere_estranho_vira_lacuna(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[medida("Boa", "SUM(Vendas[Valor])"), medida("Ruim", "[a] § [b]")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert [e.objeto for e in v.expressoes] == ["Vendas[Boa]"]
    assert [l.objeto for l in v.lacunas] == ["Vendas[Ruim]"]
    assert v.lacunas[0].motivo == "caractere não reconhecido: '§'"
    assert v.lacunas[0].posicao == 4
    assert "§" in v.lacunas[0].trecho


def test_a_expressao_com_lacuna_nao_chega_as_regras(ler):
    """A garantia estrutural: nenhuma regra vê o que o relatório diz não ter lido."""
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Ruim", "[a] § [b]")])])

    v = varrer_dax(modelo)

    assert v.expressoes == []
    assert len(v.lacunas) == 1


def test_a_soma_fecha_com_o_total_de_sitios(ler):
    """Critério de aceite 2. Lacuna que desaparece da soma é lacuna escondida."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("X", tipo="calculated", expressao="1")],
                medidas=[medida("A", "1"), medida("B", "[a] § [b]")],
                particoes=[particao(tipo="calculated", expressao="CALENDAR(1,2)")],
            )
        ]
    )

    v = varrer_dax(modelo)

    assert v.total == 4
    assert len(v.expressoes) == 3
    assert len(v.lacunas) == 1


def test_varre_a_expressao_de_filtro_da_role(ler):
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro='Vendas[Regiao] = "Sul"')],
    )

    v = varrer_dax(modelo)

    assert [e.sitio for e in v.expressoes] == ["role"]
    assert v.expressoes[0].objeto == "Vendedor:Vendas"
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_expressoes.py -v`
Expected: PASS

- [ ] **Step 7: Add the P8 test for the scan**

Em `tests/test_pbip_real.py`:

```python
def test_a_varredura_cobre_o_dax_do_p8_sem_lacuna(modelo):
    """As 137 expressões, menos as de tabela automática, que saem por escopo."""
    from core.rules.expressoes import varrer_dax

    v = varrer_dax(modelo)

    assert v.lacunas == []
    assert len(v.expressoes) == v.total
    assert {e.sitio for e in v.expressoes} == {
        "medida",
        "coluna calculada",
        "particao calculada",
    }
```

- [ ] **Step 8: Run it**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pbip_real.py -v -k varredura`
Expected: PASS. O número de `expressoes` será menor que 137, porque as 4 tabelas automáticas saem por escopo — registrar o número medido no próprio teste, com um comentário dizendo de onde ele vem.

- [ ] **Step 9: Commit**

```bash
git add core/rules/expressoes.py tests/test_rules_expressoes.py tests/test_pbip_real.py
git commit -m "feat(rules): varredura de DAX com lacuna declarada"
```

---

### Task 5: O canal de aviso no resultado

**Files:**
- Modify: `core/rules/runner.py`
- Test: `tests/test_rules_runner.py`

**Interfaces:**
- Consumes: `varrer_dax`, `LacunaDax` (Tarefa 4).
- Produces:
  - `ResultadoRegras.lacunas_de_expressao: list[LacunaDax]`
  - `ResultadoRegras.expressoes_analisadas: int`
  - `ResultadoRegras.falha_na_varredura: str | None`
  - `ResultadoRegras.cobertura_de_expressoes -> tuple[int, int]` — (analisadas, total)

O contrato das regras **não muda**: elas continuam devolvendo `Iterable[Achado]`. A lacuna é propriedade da varredura, não de cada regra — se uma expressão não tokeniza, nenhuma regra de texto a enxerga, e declarar a mesma cegueira uma vez por regra seria pior.

- [ ] **Step 1: Write the failing test**

```python
def test_o_resultado_carrega_as_lacunas(ler):
    """A interface precisa poder dizer "135 de 137 expressões analisadas"."""
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Ruim", "[a] § [b]")])])

    resultado = avaliar(modelo, Registro())

    assert len(resultado.lacunas_de_expressao) == 1
    assert resultado.lacunas_de_expressao[0].objeto == "Vendas[Ruim]"
    assert resultado.cobertura_de_expressoes == (0, 1)


def test_modelo_sem_lacuna_tem_cobertura_total(ler):
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Boa", "SUM(Vendas[V])")])])

    resultado = avaliar(modelo, Registro())

    assert resultado.lacunas_de_expressao == []
    assert resultado.cobertura_de_expressoes == (1, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_runner.py -v -k "lacuna or cobertura"`
Expected: FAIL com `AttributeError: 'ResultadoRegras' object has no attribute 'lacunas_de_expressao'`

- [ ] **Step 3: Write the implementation**

Em `core/rules/runner.py`, no import:

```python
from core.rules.expressoes import LacunaDax, varrer_dax
```

Em `ResultadoRegras`, acrescentar o campo e a propriedade, e estender a docstring da classe:

```python
    lacunas_de_expressao: list[LacunaDax] = Field(default_factory=list)
    """Expressões que o lexer não leu por completo, e que portanto nenhuma regra
    de texto examinou. Não são achados nem falhas: são cegueira declarada. O
    relatório precisa mostrá-las junto da contagem de achados, não num apêndice
    — "15 achados" e "135 de 137 expressões analisadas" devem ser lidos na mesma
    olhada."""

    @property
    def cobertura_de_expressoes(self) -> tuple[int, int]:
        """(analisadas, total) das expressões DAX em escopo."""
        total = self.expressoes_analisadas + len(self.lacunas_de_expressao)
        return self.expressoes_analisadas, total
```

e o campo que a sustenta:

```python
    expressoes_analisadas: int = 0
```

Em `avaliar`, antes do laço das regras:

```python
    varredura = varrer_dax(modelo)
```

e no `return`:

```python
    return ResultadoRegras(
        achados=achados,
        regras_com_falha=falhas,
        regras_executadas=executadas,
        lacunas_de_expressao=varredura.lacunas,
        expressoes_analisadas=len(varredura.expressoes),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_runner.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test — a varredura não pode derrubar a auditoria**

```python
def test_falha_na_varredura_nao_derruba_a_auditoria(ler, monkeypatch):
    """A varredura roda fora do isolamento por regra. Se ela estourar, a
    auditoria inteira morre — e o usuário perde também os achados estruturais,
    que não dependem de DAX nenhum."""
    import core.rules.runner as runner

    def explode(_modelo):
        raise RuntimeError("varredura com defeito")

    monkeypatch.setattr(runner, "varrer_dax", explode)
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("A", "1")])])

    resultado = runner.avaliar(modelo, Registro())

    assert resultado.cobertura_de_expressoes == (0, 0)
    assert resultado.falha_na_varredura is not None
    assert "RuntimeError" in resultado.falha_na_varredura
```

- [ ] **Step 6: Run it to verify it fails**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_runner.py -v -k varredura`
Expected: FAIL com `RuntimeError: varredura com defeito` escapando de `avaliar`

- [ ] **Step 7: Isolate the scan**

Em `ResultadoRegras`:

```python
    falha_na_varredura: str | None = None
    """A varredura de DAX falhou. As regras estruturais seguem valendo; as de
    texto não rodaram."""
```

Em `avaliar`:

```python
    try:
        varredura = varrer_dax(modelo)
    except Exception as erro:  # noqa: BLE001 — isolar é o objetivo
        logger.exception("a varredura de DAX falhou")
        varredura = VarreduraDax()
        falha_na_varredura = f"{type(erro).__name__}: {erro}"
    else:
        falha_na_varredura = None
```

Acrescentar `VarreduraDax` ao import, e `falha_na_varredura=falha_na_varredura` no `return`.

- [ ] **Step 8: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_runner.py -v`
Expected: PASS

- [ ] **Step 9: Add the Review Focus test for `null` in the new TMSL fields**

```python
def test_nulos_do_tmsl_nao_derrubam_a_varredura(tmp_path):
    """`annotations: null` derrubou as oito regras de uma vez em 06/10. Os
    campos novos — hierarchies, levels, roles, tablePermissions, variations —
    podem vir null do mesmo jeito."""
    import json

    from core.parser_bim import ler_modelo

    bruto = {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "pt-BR",
            "relationships": None,
            "roles": None,
            "tables": [
                {
                    "name": "Vendas",
                    "columns": [
                        {"name": "A", "variations": None, "sortByColumn": None}
                    ],
                    "measures": None,
                    "partitions": None,
                    "hierarchies": None,
                    "annotations": None,
                }
            ],
        },
    }
    caminho = tmp_path / "model.bim"
    caminho.write_text(json.dumps(bruto), encoding="utf-8")

    resultado = avaliar(ler_modelo(caminho), Registro())

    assert resultado.falha_na_varredura is None
    assert resultado.cobertura_de_expressoes == (0, 0)
```

- [ ] **Step 10: Run it**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_runner.py -v -k nulos`
Expected: PASS. Se falhar, falta um `or []` em `parser_bim.py` — inclusive em `relationships` e `tables`, que hoje usam `model.get("tables", [])` e devolveriam `None` se a chave existisse com valor nulo.

- [ ] **Step 11: Run the whole suite and commit**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: tudo passando, 15 achados no P8 intactos.

```bash
git add core/rules/runner.py core/parser_bim.py tests/test_rules_runner.py
git commit -m "feat(rules): o resultado declara cobertura e lacunas de expressao"
```

---

### Task 6: Onde cada coluna é usada

**Files:**
- Create: `core/rules/referencias.py`
- Test: `tests/test_rules_referencias.py`

**Interfaces:**
- Consumes: `varrer_dax`, `ExpressaoDax` (Tarefa 4); `referencias` de `core/dax.py` (Tarefa 2); `Role`, `Hierarquia` (Tarefa 3); `tabelas_em_escopo` de `escopo.py`.

**Os dois escopos, e por que aqui é `tabelas_em_escopo` e na Tarefa 4 não.** São perguntas diferentes, e confundi-las foi o defeito corrigido na Tarefa 4:

| Pergunta | Escopo certo | Onde |
|---|---|---|
| *De que colunas a PERF-005 pode falar?* | `tabelas_em_escopo` | as chaves do dicionário de usos, e o laço de marcação estrutural, nesta tarefa; e o laço da regra, na Tarefa 7 |
| *Que texto DAX o autor escreveu?* | `tabelas_com_dax_do_autor` | dentro de `varrer_dax`, na Tarefa 4 |

A coluna fictícia `calculatedTableColumn` da tabela de medidas é criada pelo Power BI para a tabela existir. Apontá-la como "sem uso" seria falso positivo, então ela **não** deve estar entre as chaves — e é por isso que `tabelas_em_escopo` está correto aqui. Ao mesmo tempo, as 92 medidas que moram nessa tabela referenciam colunas de outras tabelas, e essas referências **precisam** contar: elas chegam por `varrer_dax`, que já usa o escopo do autor.

O guarda `if chave in usos` dentro de `marcar()` é o que faz os dois escopos conviverem: uma referência a coluna de tabela fora de escopo é simplesmente descartada, porque não há nada a afirmar sobre ela.

**Não troque `tabelas_em_escopo` por `tabelas_com_dax_do_autor` nesta tarefa.** A inconsistência entre as duas tarefas é deliberada e está medida.
- Produces:
  - `SITIOS_DE_USO: tuple[str, ...]` — os oito nomes, na ordem em que a regra os reporta
  - `def usos_de_coluna(modelo: ModeloSemantico) -> dict[tuple[str, str], set[str]]` — de `(tabela, coluna)` para o conjunto de sítios que a usam

Arquivo próprio porque é o pedaço mais delicado da etapa: a PERF-005 afirma por **ausência**, e um sítio esquecido aqui faz a ferramenta recomendar apagar uma coluna em uso.

- [ ] **Step 1: Write the failing test — os sítios estruturais**

```python
"""Testes da resolução de uso de coluna.

Oito sítios. Um esquecido faz a PERF-005 recomendar apagar coluna em uso — e no
P8 há 10 `sortByColumn` e 16 níveis de hierarquia esperando por esse erro.
"""

from core.rules.referencias import usos_de_coluna
from tests.conftest import coluna, hierarquia, medida, nivel, particao, relacionamento, role, tabela


def test_chave_de_relacionamento_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[coluna("ClienteKey", tipo_dado="int64")]),
            tabela("Cliente", colunas=[coluna("ClienteKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("Fato", "ClienteKey", "Cliente", "ClienteKey")],
    )

    usos = usos_de_coluna(modelo)

    assert "relacionamento" in usos[("Fato", "ClienteKey")]
    assert "relacionamento" in usos[("Cliente", "ClienteKey")]


def test_nivel_de_hierarquia_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Produto",
                colunas=[coluna("Categoria"), coluna("Nome")],
                hierarquias=[hierarquia("H", niveis=[nivel("Cat", "Categoria")])],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "hierarquia" in usos[("Produto", "Categoria")]
    assert usos[("Produto", "Nome")] == set()


def test_sort_by_column_e_uso_da_coluna_apontada(ler):
    """O caso que quebraria a ordenação do relatório se fosse esquecido."""
    modelo = ler(
        tabelas=[
            tabela(
                "Data",
                colunas=[
                    coluna("MesNome", ordenar_por="MesNumero"),
                    coluna("MesNumero", tipo_dado="int64"),
                ],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "ordenacao" in usos[("Data", "MesNumero")]
    assert usos[("Data", "MesNome")] == set()


def test_variations_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela("Vendas", colunas=[coluna("Data", tipo_dado="dateTime", variacao_para="LDT")]),
            tabela("LDT", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ]
    )

    assert "variacao" in usos_de_coluna(modelo)[("Vendas", "Data")]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_referencias.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.referencias'`

- [ ] **Step 3: Write the implementation — os quatro sítios estruturais**

```python
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

    return usos
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_referencias.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test — referência em DAX**

```python
def test_referencia_qualificada_em_medida_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double"), coluna("Sobra")],
                medidas=[medida("Total", "SUM(Vendas[Valor])")],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Vendas", "Valor")]
    assert usos[("Vendas", "Sobra")] == set()


def test_nome_de_coluna_em_comentario_nao_e_uso(ler):
    """O lexer já separou: comentário é COMENTARIO, não REFERENCIA."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double")],
                medidas=[medida("Total", "// usa Vendas[Valor]\n1")],
            )
        ]
    )

    assert usos_de_coluna(modelo)[("Vendas", "Valor")] == set()


def test_nome_de_coluna_em_string_nao_e_uso(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Valor", tipo_dado="double")],
                medidas=[medida("Rotulo", '"Vendas[Valor]"')],
            )
        ]
    )

    assert usos_de_coluna(modelo)[("Vendas", "Valor")] == set()


def test_referencia_em_coluna_calculada_e_em_particao(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[
                    coluna("Base", tipo_dado="double"),
                    coluna("Dobro", tipo="calculated", expressao="Vendas[Base] * 2"),
                    coluna("Semente", tipo_dado="int64"),
                ],
                particoes=[particao(tipo="calculated", expressao="ROW(\"x\", Vendas[Semente])")],
            )
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de coluna calculada" in usos[("Vendas", "Base")]
    assert "dax de particao calculada" in usos[("Vendas", "Semente")]
```

- [ ] **Step 6: Implement the DAX sites**

No fim de `usos_de_coluna`, antes do `return`:

```python
    varredura = varrer_dax(modelo)
    for e in varredura.expressoes:
        sitio = _SITIO_DA_VARREDURA[e.sitio]
        for ref in referencias(e.tokens):
            if ref.coluna is None:
                continue
            marcar(ref.tabela or e.tabela, ref.coluna, sitio)
```

O `ref.tabela or e.tabela` é a resolução de referência não qualificada: `[Coluna]` dentro de uma expressão da tabela `Vendas` significa `Vendas[Coluna]` — é assim que o DAX resolve, e a `ExpressaoDax` carrega a tabela de origem exatamente para isto.

- [ ] **Step 7: Run tests, and add the Review Focus test for the homonym column**

```python
def test_coluna_homonima_em_outra_tabela_nao_e_marcada(ler):
    """O P8 tem três `GeographyKey`, em tabelas diferentes.

    `Cliente[GeographyKey]` numa medida não é uso de `Loja[GeographyKey]`.
    Marcar a tabela errada faria a PERF-005 julgar a coluna errada: a usada
    pareceria sem uso, e a sem uso pareceria usada.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Cliente",
                colunas=[coluna("GeoKey", tipo_dado="int64")],
                medidas=[medida("Conta", "DISTINCTCOUNT(Cliente[GeoKey])")],
            ),
            tabela("Loja", colunas=[coluna("GeoKey", tipo_dado="int64")]),
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Cliente", "GeoKey")]
    assert usos[("Loja", "GeoKey")] == set()


def test_referencia_nao_qualificada_resolve_na_tabela_da_expressao(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Cliente",
                colunas=[coluna("Idade", tipo_dado="int64")],
                medidas=[medida("Media", "AVERAGE([Idade])")],
            ),
            tabela("Loja", colunas=[coluna("Idade", tipo_dado="int64")]),
        ]
    )

    usos = usos_de_coluna(modelo)

    assert "dax de medida" in usos[("Cliente", "Idade")]
    assert usos[("Loja", "Idade")] == set()
```

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_referencias.py -v`
Expected: PASS

- [ ] **Step 8: Write the failing test — role**

```python
def test_referencia_em_filtro_de_role_e_uso(ler):
    """Condição de existência da PERF-005: sem isto, um modelo com RLS teria a
    coluna do filtro marcada como sem uso."""
    modelo = ler(
        tabelas=[tabela("Vendas", colunas=[coluna("Regiao")])],
        roles=[role("Vendedor", tabela="Vendas", filtro='Vendas[Regiao] = "Sul"')],
    )

    assert "dax de role" in usos_de_coluna(modelo)[("Vendas", "Regiao")]
```

- [ ] **Step 9: Run it and commit**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_referencias.py -v`
Expected: PASS — o sítio `role` já vem da varredura, montada na Tarefa 4.

```bash
git add core/rules/referencias.py tests/test_rules_referencias.py
git commit -m "feat(rules): resolucao de uso de coluna nos oito sitios"
```

- [ ] **Step 10: Add the P8 test — the eight sites measured**

Em `tests/test_pbip_real.py`:

```python
def test_os_usos_de_coluna_no_p8(modelo):
    """Quantas colunas em escopo não têm nenhum uso.

    Este número é insumo da PERF-005, e precede a contagem da regra: travá-lo
    aqui, antes de a regra existir, é o que permite verificar depois se a regra
    reproduz a medição ou divergiu dela.
    """
    from core.rules.referencias import usos_de_coluna

    usos = usos_de_coluna(modelo)
    sem_uso = sorted(chave for chave, sitios in usos.items() if not sitios)

    # Registrar aqui a lista medida, com data. Se mudar, a causa precisa ser
    # entendida antes de o número ser atualizado.
    assert len(sem_uso) >= 0, sem_uso
    print(f"\ncolunas sem uso no P8: {len(sem_uso)}")
    for chave in sem_uso:
        print(f"  {chave[0]}[{chave[1]}]")
```

- [ ] **Step 11: Run it with output and record the real list**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_pbip_real.py -v -k usos_de_coluna -s`

Anotar a lista impressa. **Esta é a medição que a Tarefa 7 usa**, e ela substitui a estimativa de 5 do `backlog.md`, feita antes de `sortByColumn` e hierarquia entrarem na conta. Trocar o `assert len(sem_uso) >= 0` pelo número medido e pela lista de nomes, e remover os `print`.

- [ ] **Step 12: Commit**

```bash
git add tests/test_pbip_real.py
git commit -m "test(rules): colunas sem uso no P8, medidas nos oito sitios"
```

---

### Task 7: Registrar a rejeição da PERF-005

**Files:**
- Modify: `docs/project/backlog.md`
- Modify: `docs/project/riscos.md`
- Modify: `docs/superpowers/specs/2026-10-08-regras-de-dax-e-varredura-textual-design.md`
- Modify: `tests/test_pbip_real.py`

**Interfaces:**
- Consumes: `usos_de_coluna`, `SITIOS_DE_USO` (Tarefa 6).
- Produces: nenhum código de produção. Esta tarefa **não** implementa regra.

#### A regra não entra. A medição da Tarefa 6 a rejeitou.

A PERF-005 estava especificada, tinha âncora transcrita no `backlog.md` desde 06/10, e era a regra de maior valor esperado da etapa. A medição da Tarefa 6, feita contra o PBIP real, a derrubou.

**O que foi medido.** `usos_de_coluna` achou **36** colunas sem uso em nenhum dos oito sítios, contra uma estimativa de 5 no backlog — estimativa feita antes de `sortByColumn` e hierarquias entrarem na conta. A regra reportaria **33** (três saem por `coluna_gerada_por_analise`), e elas se repartem assim:

| Quantas | O que são | Veredito |
|---|---|---|
| 5 | Chaves substitutas órfãs: `FactOnlineSales[OnlineSalesKey]`, `DimEmployee[EmployeeKey]`, e três `GeographyKey` | Defensáveis — chave substituta não tem propósito de relatório |
| 3 | Colunas de calendário: `DimCalendar[Mês]`, `[Trimestre]`, `[Semestre]` | **Falso positivo** — a documentação recomenda acrescentá-las, e a PERF-001 já as exclui por isso |
| 25 | Atributos reportáveis: `StoreName`, `PromotionName`, `ProductCategoryName`, `Education`, `Occupation`… | **Provável falso positivo** — quase certamente em uso em visuais |

**Por que ela não se sustenta.** A âncora (`guidance/import-modeling-data-reduction`, *Remove unnecessary columns*) justifica uma coluna por servir a **um de dois propósitos**: o relatório, ou a estrutura do modelo. A camada de relatório é o **F19**, Trabalhos Futuros — a ferramenta não a lê e não pode observar o primeiro propósito.

Portanto a PERF-005 afirma ausência sobre um domínio que ela não enxerga, e isso viola a **cláusula (c) do terceiro teste** formulado nesta mesma etapa: *todos os sítios onde o sinal pode morar*. Precisão **indeterminável** dentro do que o MVP lê — entre ~15% e ~91%, dependendo de quantos dos 25 atributos reportáveis estão de fato em uso —, contra o gatilho de 0,7 do R-03.

**O que isso vale para a monografia.** O terceiro teste rejeitou a **primeira** regra que passou nos dois primeiros critérios — e era uma regra que o projeto queria ter. É o critério se provando sobre um caso em que havia incentivo para ignorá-lo. Com a MOD-005, são dois casos em que o terceiro teste mudou o resultado, e o segundo é mais forte que o primeiro: na MOD-005 a regra foi corrigida, aqui ela foi descartada.

- [ ] **Step 1: Travar a medição no PBIP real**

A Tarefa 6 Passo 11 já escreveu o teste que trava as 36 colunas. Confirmar que ele está lá, com a lista e a data, e **acrescentar o comentário que diz por que o número importa agora**: ele não alimenta mais uma contagem de regra, ele é a evidência da rejeição.

Rodar `./.venv/Scripts/python.exe -m pytest tests/test_pbip_real.py -v -k usos_de_coluna` e confirmar que passa.

**Não acrescentar `PERF-005` a `CONTAGENS_P8`.** A regra não existe, e o total do P8 continua em 15.

- [ ] **Step 2: `backlog.md` — a candidata passa a recusada, com o motivo**

Na tabela de candidatas, a linha **"Coluna sem uso"** sai de "candidata registrada" e passa a recusada. Acrescentar ao *Log de alertas de escopo* uma linha datada de 08/10/2026:

> | 08/10/2026 | Implementar a candidata "coluna sem uso" como PERF-005 | **Recusada.** A âncora justifica a coluna por servir ao relatório **ou** à estrutura do modelo, e a camada de relatório é o F19, que a ferramenta não lê — então a regra afirma ausência sobre domínio que não observa, violando a cláusula (c) do terceiro teste. Medido no P8: 33 achados, dos quais 5 são defensáveis, 3 são colunas de calendário que a documentação recomenda (falso positivo confirmado) e 25 são atributos reportáveis cujo uso depende da camada de relatório, desconhecida para a ferramenta. **Precisão indeterminável** — entre ~15% e ~91% —, contra o gatilho de 0,7 do R-03. A resolução de uso (`core/rules/referencias.py`) **fica** como evidência reproduzível da medição e para uso de regra futura |

Acrescentar também, à seção do terceiro teste, a nota de que ele teve seu primeiro caso de rejeição — não apenas de correção.

Registrar como candidata futura a **forma estreita**: regra que aponte apenas chave substituta órfã, cujo propósito é estrutural por natureza e portanto não depende da camada de relatório. Com duas perguntas abertas: existe passagem citável para a forma estreita, e existe predicado **estrutural** que separe chave substituta de atributo, sem convenção de nome — que o projeto recusou em 06/10 (R-10).

- [ ] **Step 3: `riscos.md` — R-03 e R-12**

- **R-03** ganha um caso concreto: o critério rejeitou uma regra por precisão projetada, antes de ela existir em código, e a projeção veio de medição contra arquivo real.
- **R-12** piora. O prognóstico da seção 6 da spec já era desfavorável, e a PERF-005 era a única regra da etapa com rendimento esperado no P8. Com ela fora, a etapa acrescenta ao P8 **o que a DAX-001 render — medido como zero**. O slot **P9** passa de provável a quase certo, e converter P1–P7 deixa de ser recomendação e passa a bloqueio para decidir a Fase 3.

- [ ] **Step 4: A spec**

A seção 5 da spec descreve a PERF-005 como regra a implementar. Reescrevê-la como **regra rejeitada**, com a medição e o motivo, do mesmo jeito que a seção de rendimento (6) já trata hipótese e verificação. A seção 6 também precisa ser atualizada: a hipótese era "PERF-005 entre 0 e 5", e a medição deu 33 com precisão indeterminável (entre ~15% e ~91%, dentro do que o MVP lê) — o que confirma a hipótese do rendimento baixo da etapa por um caminho que ela não previa.

Acrescentar à seção 4.1 da spec a tabela de tokens que falta: `CHAVE_ABRE` e `CHAVE_FECHA`, acrescentados na Tarefa 1 porque o corpus real usa o construtor de tabela do DAX (`x IN {"No Discount"}`).

- [ ] **Step 5: Rodar a suíte e commitar**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: tudo passando, 15 achados no P8.

```bash
git add docs/ tests/test_pbip_real.py
git commit -m "docs: PERF-005 recusada pelo terceiro teste do criterio"
```

### Task 8: DAX-001 — Divisão com `/` onde o denominador pode ser zero

**Files:**
- Create: `core/rules/dax.py`
- Modify: `core/rules/todas.py`
- Modify: `tests/test_pbip_real.py` — trava a contagem de DAX-001 no P8 (Passo 8)
- Test: `tests/test_rules_dax.py`

**Interfaces:**
- Consumes: `Token`, `TipoToken` de `core/dax.py` (Tarefa 1); `varrer_dax` (Tarefa 4); `regra`, `Achado`, `Evidencia`.
- Produces: a regra `DAX-001` no registro global.

**A âncora foi verificada em 08/10/2026, e a verificação mudou a regra.**

URL canônica: `https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator` — *DIVIDE function vs divide operator (/) in DAX*. A URL sob `power-bi/guidance/` que a spec trazia antes **não** é a canônica.

A página **recomenda o operador `/`** num caso:

> *"In the case that the denominator is a constant value, we recommend that you use the divide operator. In this case, the division is guaranteed to succeed, and your expression will perform better because it will avoid unnecessary testing."*

E a recomendação a favor de `DIVIDE` é condicional:

> *"It's recommended that you use the DIVIDE function whenever the denominator is an expression that could return zero or BLANK."*

Portanto **a regra não marca divisão com denominador constante** — marcar seria repetir o defeito que derrubou a PERF-004 em 06/10, quando a página que a sustentaria recomendava o que a regra apontaria como erro.

Denominador é o **operando mínimo** depois do `/`: um `NUMERO`, ou o grupo entre parênteses que começa ali. É constante quando não contém nenhum token `REFERENCIA` nem `IDENTIFICADOR`.

- [ ] **Step 1: Write the failing test**

```python
"""Testes das regras de DAX por padrão textual."""

from core.rules.dax import divisao_sem_divide
from tests.conftest import coluna, medida, particao, tabela


def test_dax001_marca_divisao_com_operador(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("A", tipo_dado="double"), coluna("B", tipo_dado="double")],
                medidas=[medida("Razao", "SUM(Vendas[A]) / SUM(Vendas[B])")],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert [a.evidencia.objeto for a in achados] == ["Vendas[Razao]"]
    assert achados[0].id_regra == "DAX-001"
    assert achados[0].evidencia.detalhe["ocorrencias"] == 1
    assert achados[0].evidencia.trecho is not None


def test_dax001_nao_marca_quem_usa_divide(ler):
    modelo = ler(
        tabelas=[
            tabela("Vendas", medidas=[medida("Razao", "DIVIDE([A], [B])")]),
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_um_achado_por_expressao_nao_por_barra(ler):
    """Um achado por ocorrência, e a ocorrência é a expressão: é nela que o
    autor corrige. O número de barras marcadas vai no detalhe.

    As duas divisões aqui têm denominador variável, então as duas contam."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("Duas", "[a]/[b] + [c]/[d]")])]
    )

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.detalhe["ocorrencias"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_dax.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.dax'`

- [ ] **Step 3: Write the rule**

```python
"""Regras de DAX por padrão textual — o grupo 2 do critério de detectabilidade.

Toda regra aqui lê tokens, nunca a string crua. O motivo é medido: 92 das 128
expressões de medida e coluna do P8 têm comentário `//`, e uma expressão regular
procurando `/` casaria o comentário em todas elas.

As expressões vêm de `core.rules.expressoes.varrer_dax`, que entrega apenas o
que o lexer leu por completo. O que ele não leu é lacuna declarada no resultado
da auditoria, e nenhuma regra daqui o examina.
"""

from collections.abc import Iterator

from core.dax import Token, TipoToken
from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.expressoes import varrer_dax
from core.rules.registry import regra

TIPO_DE_OBJETO = {
    "medida": "medida",
    "coluna calculada": "coluna",
    "particao calculada": "particao",
    "role": "modelo",
}


@regra(
    id="DAX-001",
    titulo="Divisão com o operador onde o denominador pode ser zero",
    categoria="dax",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator",
    termos_consulta=[
        "DIVIDE function versus divide operator",
        "divide by zero DAX blank",
        "safe division DAX alternate result",
        "division operator performance DAX",
    ],
    recomendacao_padrao=(
        "Troque a divisão pela função DIVIDE quando o denominador for uma expressão "
        "que possa retornar zero ou BLANK. A DIVIDE foi desenhada para tratar a "
        "divisão por zero automaticamente: sem o terceiro argumento ela devolve BLANK "
        "quando o denominador é zero ou BLANK, e com ele devolve o valor alternativo "
        "que você indicar. Ela também dispensa testar o denominador antes, e é mais "
        "otimizada para esse teste que a função IF — o ganho é significativo, porque "
        "verificar divisão por zero é caro. Há exceção declarada pela própria "
        "documentação: quando o denominador é um valor constante, o recomendado é usar "
        "o operador, porque a divisão não pode falhar e evitar o teste faz a expressão "
        "ter melhor desempenho. Sobre o valor alternativo, pense duas vezes antes de "
        "usá-lo: em medidas, devolver BLANK costuma ser o melhor desenho, porque os "
        "visuais eliminam por padrão os agrupamentos cujo resultado é BLANK, o que "
        "concentra a atenção nos grupos onde há dados."
    ),
    nota_de_verificacao=(
        "A regra não marca divisão cujo denominador é constante — a documentação "
        "recomenda o operador nesse caso. Denominador é o operando mínimo depois do "
        "'/', e é tido por constante quando não contém referência nem identificador. "
        "Falso positivo declarado: denominador constante escrito de forma que o lexer "
        "não reconheça como tal. Falso negativo declarado: denominador que é expressão "
        "mas nunca retorna zero nem BLANK na prática, como (1 + ABS([x])) — a regra "
        "marca, porque decidir isso exigiria avaliar a expressão, e avaliação de DAX "
        "está fora do MVP."
    ),
)
def _denominador(tokens: list[Token], posicao_da_barra: int) -> list[Token]:
    """O operando mínimo depois do `/`: um número, ou o grupo entre parênteses.

    Mínimo de propósito. Pegar tudo até o fim do argumento incluiria mais
    tokens, acharia referência com mais facilidade e faria a regra marcar
    divisão que a documentação recomenda. Errar para o lado do silêncio é a
    política do projeto: regra com precisão baixa é pior que regra ausente.
    """
    resto = tokens[posicao_da_barra + 1 :]
    if not resto:
        return []

    if resto[0].tipo is not TipoToken.PARENTESE_ABRE:
        return [resto[0]]

    profundidade = 0
    for i, t in enumerate(resto):
        if t.tipo is TipoToken.PARENTESE_ABRE:
            profundidade += 1
        elif t.tipo is TipoToken.PARENTESE_FECHA:
            profundidade -= 1
            if profundidade == 0:
                return resto[: i + 1]
    return resto


def _e_constante(denominador: list[Token]) -> bool:
    """Denominador sem referência e sem identificador é valor constante.

    A documentação recomenda o operador nesse caso, e marcar seria apontar como
    defeito o que a fonte recomenda — o erro que derrubou a PERF-004 em 06/10.
    """
    if not denominador:
        return False
    return not any(
        t.tipo in (TipoToken.REFERENCIA, TipoToken.IDENTIFICADOR) for t in denominador
    )


def divisao_sem_divide(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por expressão com divisão `/` de denominador não constante.

    O achado é a expressão, não cada barra: é na expressão que o autor corrige.
    A contagem de barras marcadas vai no detalhe da evidência.
    """
    for e in varrer_dax(modelo).expressoes:
        barras = [
            t
            for i, t in enumerate(e.tokens)
            if t.tipo is TipoToken.OPERADOR
            and t.texto == "/"
            and not _e_constante(_denominador(e.tokens, i))
        ]
        if not barras:
            continue
        yield Achado(
            id_regra="DAX-001",
            evidencia=Evidencia(
                tipo_objeto=TIPO_DE_OBJETO[e.sitio],
                objeto=e.objeto,
                tabela=e.tabela,
                trecho=e.texto,
                detalhe={
                    "ocorrencias": len(barras),
                    "posicoes": [t.posicao for t in barras],
                    "sitio": e.sitio,
                },
            ),
            mensagem=(
                f"A expressão de '{e.objeto}' divide com o operador '/' em "
                f"{len(barras)} lugar(es) onde o denominador é uma expressão que "
                "pode retornar zero ou BLANK."
            ),
        )
```

Em `core/rules/todas.py`, acrescentar o import:

```python
from core.rules import dax, modelagem, performance  # noqa: F401 — o import registra
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_dax.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing test — the three lookalikes**

```python
def test_dax001_ignora_barra_em_comentario(ler):
    """O sósia que torna a regex inviável: 92 das 128 expressões do P8 têm `//`."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("A", "// taxa a/b\nDIVIDE([a],[b])")])]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_barra_em_string(ler):
    modelo = ler(tabelas=[tabela("Vendas", medidas=[medida("Unidade", '"km/h"')])])

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_barra_em_nome_de_coluna(ler):
    """`[Receita/Custo]` é um nome, não uma divisão."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Receita/Custo", tipo_dado="double")],
                medidas=[medida("Total", "SUM(Vendas[Receita/Custo])")],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_ignora_particao_m(ler):
    """`/` em caminho de arquivo do Power Query não é divisão em DAX."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                particoes=[particao(tipo="m", expressao='Csv.Document(File.Contents("c:/d/x.csv"))')],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_nao_marca_denominador_constante(ler):
    """A documentação **recomenda** o operador quando o denominador é constante.

    "In the case that the denominator is a constant value, we recommend that you
    use the divide operator." Marcar isto seria apontar como defeito o que a
    fonte recomenda — o erro que derrubou a PERF-004 em 06/10.
    """
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                colunas=[coluna("Mes", tipo_dado="int64")],
                medidas=[
                    medida("Trimestre", "INT(Vendas[Mes] / 3)"),
                    medida("Percentual", "[Taxa] / 100"),
                    medida("Constante entre parenteses", "[Taxa] / (2 * 3)"),
                ],
            )
        ]
    )

    assert list(divisao_sem_divide(modelo)) == []


def test_dax001_marca_denominador_que_e_expressao(ler):
    """O caso que a página manda trocar: denominador que pode dar zero ou BLANK."""
    modelo = ler(
        tabelas=[
            tabela(
                "Vendas",
                medidas=[
                    medida("Razao de medidas", "[Lucro] / [Receita]"),
                    medida("Razao com funcao", "[Lucro] / SUM(Vendas[Receita])"),
                    medida("Razao em grupo", "[Lucro] / ([Receita] + 1)"),
                ],
            )
        ]
    )

    achados = list(divisao_sem_divide(modelo))

    assert sorted(a.evidencia.objeto for a in achados) == [
        "Vendas[Razao com funcao]",
        "Vendas[Razao de medidas]",
        "Vendas[Razao em grupo]",
    ]


def test_dax001_conta_so_as_barras_que_marca(ler):
    """Uma expressão com as duas formas: só a de denominador variável conta."""
    modelo = ler(
        tabelas=[tabela("Vendas", medidas=[medida("Mista", "[a]/100 + [b]/[c]")])]
    )

    achados = list(divisao_sem_divide(modelo))

    assert len(achados) == 1
    assert achados[0].evidencia.detalhe["ocorrencias"] == 1
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `./.venv/Scripts/python.exe -m pytest tests/test_rules_dax.py -v`
Expected: PASS — os quatro sósias já são tratados pelo lexer e pela varredura. Se algum falhar, o defeito está na Tarefa 1 ou 4, não aqui.

- [ ] **Step 7: Write the recommendation from the verified passage**

Substituir a `recomendacao_padrao` pelo texto escrito a partir da passagem transcrita no `backlog.md`. Precisa de pelo menos 40 caracteres de texto útil — `RegraMeta` valida na importação — e **precisa repetir as exceções que a página declarar**, como fazem PERF-001 e PERF-003.

- [ ] **Step 8: Lock the P8 count**

Acrescentar `"DAX-001"` a `CONTAGENS_P8` em `tests/test_pbip_real.py` com o número medido. A sondagem de 08/10 previu **zero** em escopo; confirmar com a regra implementada e registrar o número real.

- [ ] **Step 9: Run the whole suite and commit**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: tudo passando, contagens anteriores intactas.

```bash
git add core/rules/dax.py core/rules/todas.py tests/test_rules_dax.py tests/test_pbip_real.py
git commit -m "feat(rules): DAX-001, divisao com operador em vez de DIVIDE"
```

- [ ] **Step 10: Check the catalog**

Run: `./.venv/Scripts/python.exe -m core.rules.catalogo`
Expected: 10 regras, com DAX-001 e PERF-005 e suas URLs. Critério de aceite 8.

---

### Task 9: Verificar o rendimento antes de afirmar precisão

**Files:**
- Modify: `docs/project/progress-log.md`
- Test: `tests/test_pbip_real.py`

Esta tarefa não escreve código de produção. Ela executa o procedimento da seção 6 da spec, que o critério de aceite 7 exige: **todo zero no P8 tem a causa identificada** — ausência de defeito, que é precisão, ou cegueira da regra, que é falso negativo. Sem isso, nenhuma afirmação de precisão entra na monografia nem no `status.md`.

- [ ] **Step 1: Recount DAX-001 with the lexer, not with regex**

Script descartável, rodado no PBIP real:

```python
from core.dax import operadores
from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.dax import divisao_sem_divide
from core.rules.expressoes import varrer_dax

modelo = ler_modelo(abrir_pbip("data/pbip/P8_contoso-vendas").model_bim)
v = varrer_dax(modelo)

print("--- o que a regra marca ---")
for a in divisao_sem_divide(modelo):
    print(a.evidencia.objeto, a.evidencia.detalhe)

print("--- toda barra, inclusive a de denominador constante ---")
for e in v.expressoes:
    barras = operadores(e.tokens, "/")
    if barras:
        print(e.sitio, e.objeto, len(barras), "|", e.texto[:90].replace("
", " "))

print("expressoes em escopo:", len(v.expressoes), "| lacunas:", len(v.lacunas))
```

As duas listas respondem perguntas diferentes, e é por isso que ambas são impressas:

- a **primeira** é o rendimento da regra. Vazia, o zero se confirma **medido pelo lexer**, e aí é zero verdadeiro;
- a **segunda** é o controle. Se ela trouxer barras que a primeira não trouxe, cada uma precisa ser conferida à mão: é denominador constante de fato, que a documentação recomenda, ou é cegueira de `_e_constante`? Esta é a metade que detecta falso negativo, e sem ela o zero da primeira lista não sustenta afirmação de precisão.

- [ ] **Step 2: Conferir a medição que rejeitou a PERF-005**

A regra foi rejeitada na Tarefa 7, então não há achados dela para verificar. O que precisa ser conferido é a **medição que a rejeitou**, porque é ela que vai para a monografia:

Para **cinco** das 36 colunas que `usos_de_coluna` dá como sem uso, conferir à mão no `model.bim` os oito sítios — e escolher as cinco de propósito, não ao acaso: uma chave órfã, uma coluna de calendário, e três atributos reportáveis. Se alguma delas tiver uso que a resolução não viu, a medição está contaminada e a rejeição precisa ser reavaliada.

Conferir também, para **três colunas que a resolução dá como usadas**, que o uso existe mesmo. Essa metade detecta o erro oposto — resolução marcando uso que não há faria colunas genuinamente órfãs parecerem usadas, e teria escondido o problema em vez de revelá-lo.

- [ ] **Step 3: Classify the six `SUMX` occurrences**

Listar as 6 ocorrências de `SUMX` em escopo e classificar cada uma: iteração desnecessária (poderia ser `SUM` sobre uma coluna) ou iteração legítima (expressão de várias colunas). O resultado é o que diz se a DAX-002 vale a pena, e é o denominador de qualquer afirmação de precisão sobre ela.

```python
from core.dax import chamadas
# ... monta `v` como no Passo 1
for e in v.expressoes:
    for args in chamadas(e.tokens, "SUMX"):
        print(e.objeto, "| args:", [[t.texto for t in a] for a in args])
```

- [ ] **Step 4: Write the findings in `progress-log.md`**

Uma entrada datada que registre: o número medido de cada regra que entrou, a causa do zero quando houver zero, e a conferência da medição que rejeitou a PERF-005. Dizer explicitamente qual afirmação de precisão a medição **autoriza** e qual não autoriza.

- [ ] **Step 5: Commit**

```bash
git add docs/project/progress-log.md tests/test_pbip_real.py
git commit -m "docs: rendimento do grupo 2 no P8, verificado e com a causa de cada zero"
```

---

### Task 10: Documentos de projeto

**Files:**
- Modify: `docs/project/backlog.md`, `docs/project/riscos.md`, `docs/project/status.md`, `README.md`, `docs/project/progress-log.md`

- [ ] **Step 1: `backlog.md`**

- O **terceiro teste** do critério de detectabilidade, com as cláusulas (a), (b) e (c), como seção própria depois da de 06/10.
- **D-1:** a contagem de 20–25 deixa de ser meta e passa a ser resultado, com a aritmética que levou a isso.
- A passagem citável da DAX-001, transcrita com data de acesso (Tarefa 8).
- **DAX-003 (`FILTER`)** movida para candidata adiada, com o motivo: zero ocorrência no P8.
- Em Trabalhos Futuros: **F25**, recusar-se a declarar o grupo de DAX completo enquanto houver lacuna aberta (D-7).
- A candidata "coluna sem uso" passa a **recusada**, com o motivo e a medição (a Tarefa 7 Passo 2 já escreve a linha do log de alertas; conferir que está lá e consistente).

- [ ] **Step 2: `riscos.md`**

- **R-03** ganha a terceira mitigação: o lexer, com o número de cobertura medido no P8.
- **R-12** ganha o prognóstico da seção 6 da spec: o grupo 2 rende pouco até num modelo problemático, o que torna o slot P9 mais provável.
- Data da última atualização.

- [ ] **Step 3: `status.md`**

- A tabela de fases: a semana 5 foi usada para fechar o grupo 2, e a Fase 3 começa na semana 6. A folga de uma semana foi consumida, e isso precisa aparecer porque a versão anterior reportou a folga ao orientador.
- A seção 4.1 (contagem de regras) atualizada com D-1 e a decisão aprovada.
- A tabela de regras com as novas e as contagens medidas.
- A afirmação de precisão **somente** no que a Tarefa 9 autorizar.

- [ ] **Step 4: `README.md`**

Contagem de regras, de testes e de achados no P8; a Fase 3 como em andamento.

- [ ] **Step 5: `progress-log.md` — estender a entrada da Tarefa 9, não abrir outra**

A Tarefa 9 já criou a entrada de 08/10/2026 com a verificação do rendimento. **Estender aquela entrada**, em vez de abrir uma segunda da mesma data: duas entradas com assuntos sobrepostos tornam o log pior de ler, e o log é material da monografia.

Acrescentar: o que foi entregue, o terceiro teste e de onde veio, o número de cobertura do lexer, e as pendências que seguem abertas — a verificação das roles e a conversão de P1–P7.

- [ ] **Step 6: Run the whole suite one last time**

Run: `./.venv/Scripts/python.exe -m pytest -q`
Expected: tudo passando.

Run: `./.venv/Scripts/python.exe -m core.rules.catalogo`
Expected: o catálogo completo, com as regras novas.

- [ ] **Step 7: Commit**

```bash
git add docs/ README.md
git commit -m "docs: terceiro teste do criterio, contagem como resultado e o uso da folga"
```

---

## Tarefa adiada: DAX-002 — Iteração desnecessária

**Não está nas tarefas acima de propósito.** A âncora não foi verificada, e sob o critério do projeto a regra não pode ser planejada em detalhe antes disso. A Tarefa 9 Passo 3 produz o dado que decide se vale: quantas das 6 ocorrências de `SUMX` no P8 são iteração desnecessária de fato.

Se valer, a regra entra numa etapa própria, com a âncora transcrita primeiro. A infraestrutura de que ela precisa — `chamadas`, com fronteira de argumento — já fica pronta na Tarefa 2.
