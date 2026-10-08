# Varredura textual de DAX e o grupo 2 de regras

- **Data:** 08/10/2026
- **Fase:** 2 (continuação) — executada na **semana 5**, que o roadmap reservou à Fase 3
- **Status:** Aprovado para implementação
- **Funcionalidades:** F04 (regras DAX), parte de F07 (performance estática) e F15

## 1. Objetivo e contexto

A Fase 2 entregou o motor de regras e as oito regras estruturais — o **grupo 1** do critério de detectabilidade. Esta etapa entrega o **grupo 2**: regras cuja detecção depende de ler o texto das expressões DAX, mais a candidata **coluna sem uso**, que o `backlog.md` registra como "fronteira com o grupo 2" porque também depende dessa varredura.

Nada no projeto sabe hoje sintaxe de DAX. A única coisa parecida é `_primeira_linha_util` em `escopo.py`, que ignora comentário `//` apenas na primeira linha de uma expressão. Esta etapa, portanto, introduz um **mecanismo de detecção novo**: até aqui toda regra lia uma propriedade explícita do TMSL; a partir daqui há regras que leem texto livre escrito pelo autor.

O `riscos.md` marca o **R-03** — falsos positivos em heurística de DAX — com probabilidade **alta**. Esta etapa é onde ele se materializa, e o desenho abaixo existe sobretudo para contê-lo.

### Consequência de cronograma, registrada

Isto é trabalho de **regras**, portanto Fase 2, executado na **semana 5** — que o roadmap de 13 semanas reservou ao catálogo de fontes e à coleta da base RAG, primeiro entregável da Fase 3.

Em 08/10/2026 o projeto estava cerca de **uma semana à frente** do cronograma em tempo: terceira semana de calendário, trabalho da quarta semana concluído. Esta etapa **consome essa folga**. Ao fim dela o projeto estará em dia, não adiantado, e a Fase 3 começa na semana 6 do roadmap.

A troca é deliberada e vale ser dita ao orientador nestes termos: gastou-se a folga para fechar o grupo 2 de regras com rigor, em vez de começar a RAG com o conjunto de regras incompleto. O `status.md` reportou a folga; precisa reportar também o seu uso. Se a semana 7 atrasar, o primeiro corte segue sendo o previsto no roadmap — reduzir as regras de M, e depois abrir mão do PDF.

### A medição que determinou o desenho

Antes de decidir qualquer coisa, o P8 foi medido. São **137 expressões DAX** (93 medidas, 35 colunas calculadas, 9 partições calculadas) e **10 partições em M**:

| Medida no P8 | Valor | Consequência |
|---|---|---|
| Expressões com comentário `//` | **92 de 128** medidas e colunas | Regex sobre texto bruto é inviável por medição, não por princípio |
| Expressões com literal de string | 41 das mesmas 128 | Segundo sósia do sinal |
| Expressões com `--` ou `/* */` | 0 | DAX admite as duas; cobrir é seguro barato |
| Partições em M, não em DAX | 10 de 19 | Regra de DAX que varresse toda partição leria M |
| Divisões reais com `/`, **em escopo** | **0** | As 4 existentes estão em tabela automática, excluída |
| `DIVIDE` em escopo | 11 | O autor do P8 faz certo |
| `FILTER` em escopo | **0** | Uma regra de `FILTER` não teria validação no estudo de caso |
| `QUOTIENT` em escopo | 0 | — |
| `SUMX` / `RANKX` / `MINX` em escopo | 6 / 4 / 2 | Teto das candidatas de iteração |
| Sítios estruturais de referência a coluna | 11 relacionamentos, **16 níveis de hierarquia**, **10 `sortByColumn`**, 3 `variations` | A varredura da coluna sem uso tem oito sítios, não um |
| Roles de RLS no P8 | **0** | O ramo de RLS não pode ser validado contra arquivo real |

## 2. Decisões desta etapa

| # | Decisão | Alternativa recusada | Motivo |
|---|---|---|---|
| D-1 | **A contagem de regras deixa de ser meta e passa a ser resultado** | Perseguir as 20–25 do roadmap | Mantendo a exigência de âncora, o cenário otimista sem o grupo 3 soma ~18. Alcançar 20–25 exigiria aceitar o grupo 3, onde a heurística erra sem parser sintático, ou relaxar a âncora — as duas coisas que o projeto recusou em 29/09 e 06/10. A monografia defende o conjunto menor e usa as regras descartadas como evidência do método |
| D-2 | **Terceiro teste do critério de detectabilidade** (seção 3) | Manter os dois testes atuais | A MOD-005 passou nos dois e ainda assim marcaria a dimensão corretamente configurada. O terceiro teste é o que a impediria, e vale para toda regra futura |
| D-3 | **Um lexer**, não regex sobre texto sanitizado | Sanitizar e depois aplicar regex; regex sobre texto bruto | A regra de coluna sem uso faz afirmação **universal negativa**. Varredura que interprete mal uma expressão entre 137 faz a ferramenta recomendar apagar coluna em uso — falso positivo destrutivo. Extração de referência precisa ser exata, e por isso a referência é token de primeira classe |
| D-4 | **O lexer nunca levanta exceção**; caractere não reconhecido vira token `DESCONHECIDO` | Levantar exceção; ignorar o caractere | Ignorar esconderia a cegueira. Levantar derrubaria todas as regras de DAX de uma vez. O token torna a cegueira um dado |
| D-5 | **Expressão não tokenizada por completo não chega às regras**, e vira lacuna declarada ao usuário | Deixar cada regra decidir se se abstém; abster em silêncio | Abstenção silenciosa é o defeito da MOD-005: a ferramenta parecia ter analisado o que não analisou. E a cegueira é do lexer diante do arquivo, não de cada regra — declarar oito vezes a mesma lacuna seria pior |
| D-6 | **Três componentes**: lexer (sintaxe), varredura (modelo), regras | Um módulo só | O lexer não deve conhecer modelo, e a varredura não deve conhecer sintaxe. Cada um testável sozinho |
| D-7 | **A lacuna não interrompe a auditoria**; ela avisa | Recusar-se a declarar o grupo de DAX completo com lacuna aberta | Projeto acadêmico: avisar basta. O refinamento vai para Trabalhos Futuros |
| D-8 | **DAX-003 (`FILTER` sobre tabela inteira) fica fora desta fase** | Implementar com as outras | Zero ocorrência no P8: sem teste de regressão real nem evidência para a monografia. Fica como candidata registrada, a decidir quando P1–P7 existirem |
| D-9 | **A verificação empírica das roles precede o código** do ramo de RLS | Implementar pela especificação do TMSL com nota de verificação | É a mesma classe de risco que derrubou a MOD-005 — a propriedade existia na especificação e o Desktop não a escrevia —, e aqui o falso positivo é destrutivo |
| D-10 | **PERF-005**, ID novo | Reusar PERF-002, descartada em 06/10 | Ressuscitar ID de regra descartada confundiria o registro e o histórico |

## 3. O terceiro teste do critério de detectabilidade

O critério tem hoje duas condições, nesta ordem: **existe passagem citável no Microsoft Learn** (06/10) e **é decidível no `model.bim`** (29/09). A MOD-005 passou nas duas.

Ela lia a **ausência** de `dataCategory: "Time"` como prova de que a dimensão não estava marcada. O defeito não foi ler a propriedade errada: foi tratar ausência como prova, quando nada garantia que a propriedade estaria presente no caso contrário. O Desktop não a escreve nunca — a ausência era compatível com os dois mundos.

> **Terceiro teste — suficiência da evidência.** Antes de escrever código, a regra enumera **por escrito**:
>
> **(a) as formas da condição** — todas as maneiras de escrever aquilo que a regra procura;
> **(b) os sósias do sinal** — todas as maneiras de algo parecer o sinal sem ser;
> **(c) os sítios** — todos os lugares do arquivo onde o sinal pode morar, e de que linguagem é cada um.
>
> Só então a regra declara se afirma por **presença** ou por **ausência**. Afirmação por ausência exige (a), (b) e (c) completos, mais a garantia de que a presença seria escrita no caso contrário. Faltando qualquer um, a regra se cala e declara o falso negativo.

A cláusula (a) veio da revisão de 08/10: para saber que existe uma divisão é preciso conhecer **todas** as formas de escrever divisão — `/`, `DIVIDE`, `QUOTIENT` —, senão a regra não distingue "forma errada" de "não há divisão alguma". A cláusula (c) veio da medição: a coluna sem uso tem oito sítios, e esquecer `sortByColumn` produziria recomendação destrutiva.

O teste também é o que torna defensável dizer que uma regra se cala: calar com falso negativo declarado passa a ser consequência de um critério escrito, e não hesitação caso a caso.

## 4. Componentes

### 4.1 `core/dax.py` — o lexer

Texto entra, tokens saem. Não conhece modelo, tabela nem regra.

| Token | Conteúdo |
|---|---|
| `COMENTARIO` | `//` e `--` até fim de linha; bloco `/* */`. Emitido, não descartado, para que o teste possa afirmar sobre ele |
| `STRING` | `"..."`, com `""` como aspas literais |
| `NUMERO` | Inteiro e decimal |
| `REFERENCIA` | `Tabela[Coluna]`, `'Tabela com espaço'[Coluna]` (com `''` como apóstrofo literal), e `[Medida]` — este sem tabela, e é assim que medida se distingue de coluna |
| `IDENTIFICADOR` | Nome de função ou nome de tabela nu |
| `OPERADOR` | `/ * + - & = <> < > <= >= ^ || &&` e `IN` |
| `PARENTESE_ABRE` / `PARENTESE_FECHA` | Para profundidade e fronteira de argumento |
| `VIRGULA` | Separador de argumento |
| `DESCONHECIDO` | Caractere que o lexer não reconhece. **Nunca levanta exceção** (D-4) |

Cada token carrega `tipo`, `texto` e `posicao`. Espaço em branco é descartado.

**O que o lexer não faz:** não constrói AST, não conhece precedência, não valida. Parser sintático completo é F18, Trabalhos Futuros — e é por isso que o grupo 3 (DAX dependente de contexto) continua fora.

Funções de conveniência sobre a lista de tokens, para as regras não reimplementarem varredura: `referencias(tokens)`, `chamadas(tokens, nome)` — devolvendo a fatia de argumentos por profundidade de parêntese — e `operadores(tokens, simbolo)`.

### 4.2 `core/rules/expressoes.py` — onde o DAX mora

Modelo entra, varredura sai. Não conhece sintaxe de DAX. Respeita as exclusões de `escopo.py` e filtra por linguagem: partição só entra se `source.type == "calculated"`.

```python
class ExpressaoDax(BaseModel):
    sitio: str              # "medida" | "coluna calculada" | "particao calculada" | "role"
    objeto: str             # "_Medidas[Ticket Médio]"
    tabela: str | None
    texto: str
    tokens: list[Token]     # já tokenizada, e por completo

class LacunaDax(BaseModel):
    sitio: str
    objeto: str
    tabela: str | None
    posicao: int            # onde a tokenização parou
    trecho: str             # vizinhanças, para o usuário localizar no Desktop
    motivo: str             # "caractere não reconhecido: '§'"

class VarreduraDax(BaseModel):
    expressoes: list[ExpressaoDax]   # tokenizadas por completo
    lacunas: list[LacunaDax]
```

As duas listas vêm **juntas**, de uma função só, e as regras iteram apenas `expressoes`. Uma expressão que não tokenizou por completo **não chega às regras** — é estruturalmente impossível a ferramenta afirmar algo sobre um trecho que o relatório declara não ter analisado (D-5).

Módulo próprio, e não dentro de `escopo.py`: aquele já tem 265 linhas e seu assunto é exclusão, não enumeração. O grupo 4 (regras de M) reusa este módulo trocando o filtro para `"m"`.

### 4.3 `core/rules/dax.py` — as regras

Usam 4.1 e 4.2 e não reimplementam nenhum dos dois. A PERF-005 fica em `performance.py`, junto das suas, por categoria.

### 4.4 `core/rules/runner.py` e `base.py` — o canal de aviso

`ResultadoRegras` ganha um campo e uma propriedade:

```python
lacunas_de_expressao: list[LacunaDax] = Field(default_factory=list)

@property
def cobertura_de_expressoes(self) -> tuple[int, int]:
    """Analisadas e total — "135 de 137" vai para o cabeçalho do relatório."""
```

O contrato das regras **não muda**: elas continuam devolvendo `Iterable[Achado]`. A lacuna é propriedade da varredura, não de cada regra.

### 4.5 `core/parser_bim.py` e `core/model.py` — estendidos

Passam a ler os sítios que o terceiro teste obriga e que hoje são invisíveis:

| Sítio | Para quê | Existe no P8? |
|---|---|---|
| `roles[].tablePermissions[].filterExpression` | Condição de existência da PERF-005 | **Não** — pendente de verificação empírica (D-9) |
| `tables[].hierarchies[].levels[].column` | 16 referências estruturais a coluna | Sim |
| `tables[].columns[].sortByColumn` | 10 referências estruturais a coluna | Sim |
| `tables[].measures[].formatStringDefinition` | Sítio de DAX | Não |
| `tables[].calculationGroup.calculationItems[]` | Sítio de DAX | Não |
| `tables[].measures[].detailRowsDefinition` | Sítio de DAX | Não |

Sítio não lido é prova de ausência que não existe.

## 5. As regras, com o terceiro teste aplicado

### PERF-005 — Coluna sem uso

- **Âncora:** `guidance/import-modeling-data-reduction`, *Remove unnecessary columns* — já verificada e transcrita no `backlog.md` de 06/10. A página define os dois propósitos que justificam uma coluna, e ambos são verificáveis no `model.bim`.
- **Afirma por:** **ausência**. É a regra mais exigente do conjunto.
- **(a) Formas da condição** — uso de uma coluna é qualquer um de oito: chave de relacionamento; nível de hierarquia; `sortByColumn` de outra coluna; alvo de `variations`; referência em DAX de medida; de coluna calculada; de partição calculada; e expressão de filtro de role.
- **(b) Sósias** — nome de coluna dentro de string ou de comentário; e coluna homônima em outra tabela, de modo que referência não qualificada exige resolução por tabela.
- **(c) Sítios** — os oito acima. No P8: 11 relacionamentos, 16 níveis, 10 `sortByColumn`, 3 `variations`, 137 expressões, 0 roles.
- **Rendimento no P8:** o `backlog.md` estima 5 (chaves substitutas órfãs). **Essa estimativa não será travada em teste sem antes ser reverificada**, porque foi feita sem considerar `sortByColumn` nem hierarquia (seção 7).

### DAX-001 — Divisão com `/` em vez de `DIVIDE`

- **Âncora:** candidata `guidance/dax-divide-function-operator` — o Learn tem página dedicada à escolha entre o operador e a função, o que faria dela a âncora mais forte do conjunto. **Não verificada ainda:** a URL exata e a passagem citável precisam ser confirmadas e transcritas antes do código, como manda o critério de 06/10. Se a página não sustentar a afirmação, a regra não entra.
- **Afirma por:** **presença** do operador. Passa o terceiro teste direto.
- **(a) Formas** — divisão é `/`, `DIVIDE()` e `QUOTIENT()`. O defeito é a forma `/`.
- **(b) Sósias** — `//` de comentário, `/` dentro de string, `/` dentro de nome entre colchetes, `/` em código M.
- **(c) Sítios** — os de DAX, com `source.type == "calculated"`.
- **Rendimento no P8:** **zero**, em escopo. As 4 divisões reais estão em tabela de data automática, já excluída. **Isso é resultado, não falha:** uma regra de âncora forte que se cala corretamente num modelo que usa `DIVIDE` 11 vezes é evidência de precisão.

### DAX-002 — Iteração desnecessária

- **Âncora:** **a verificar.** Sem passagem citável, a regra não entra.
- **Afirma por:** presença, mas exige **fronteira de argumento** — é a regra que justifica a profundidade de parêntese do lexer.
- **Rendimento no P8:** até 6 candidatas (`SUMX`), a confirmar. `SUMX` sobre expressão de várias colunas é legítimo e não é achado.

### DAX-003 — `FILTER` sobre tabela inteira

**Fora desta fase** (D-8). Zero ocorrência no P8. Permanece candidata registrada no `backlog.md`.

## 6. Rendimento esperado, assumido explicitamente

O grupo 2 **quase não move a contagem do P8**: PERF-005 entre 0 e 5, DAX-001 zero, DAX-002 entre 0 e 6. É plausível que a fase inteira acrescente menos achados que a MOD-001 sozinha.

Isso é característica do modelo, não das regras. O autor do P8 usa `DIVIDE`, não usa `FILTER`, e seus defeitos são **estruturais** — tempo automático ligado, bidirecionais, floco de neve. O grupo 1 era onde eles estavam.

Duas consequências assumidas:

1. **Para a monografia é resultado.** Regra com âncora forte que se cala corretamente sustenta o relato de precisão, e conversa com D-1.
2. **Para o R-12 o prognóstico piora.** Se o grupo 2 rende pouco até num modelo problemático, o gatilho de ~40 achados em P1–P7 fica mais distante e o slot **P9** fica mais provável. Reforça converter P1–P7 logo, como já recomendava `status.md`.

## 7. Testes

Teste que falha primeiro, como nas oito regras existentes.

**Do lexer:**
- um teste por tipo de token, incluindo os escapes `''` em nome citado e `""` em string;
- um teste por sósia medido no P8: `//`, `--`, `/* */`, `/` em string, `/` em nome entre colchetes;
- **cobertura contra corpus real:** tokenizar as **137** expressões DAX do P8 e exigir **zero** token `DESCONHECIDO`. É o número verificável que a monografia cita no lugar de "usamos expressões regulares".

**Da varredura:**
- `len(expressoes) + len(lacunas)` igual ao total de sítios DAX em escopo — lacuna que desaparece da soma é lacuna escondida;
- as 10 partições em M não aparecem na varredura de DAX;
- uma expressão com caractere não reconhecido aparece em `lacunas` e **não** em `expressoes`.

**Das regras:** positivo e negativo por regra, e contagem travada no P8.

**Regressão que importa:** os **15 achados atuais não podem mudar**. Nem a extensão do parser nem as regras novas têm o direito de mexer em MOD-\* ou PERF-001/003. Os 101 testes atuais continuam passando.

**Ressalva de método sobre a contagem da PERF-005:** antes de escrever o teste, verificar coluna por coluna, nos oito sítios, que ela é de fato não usada. A contagem travada deve ser o **resultado** da verificação, não a expectativa que a motivou. Foi exatamente assim que a MOD-005 errou.

## 8. Arquivos

| Arquivo | Mudança |
|---|---|
| `core/dax.py` | **novo** — lexer, ~150–250 linhas |
| `core/rules/expressoes.py` | **novo** — varredura e lacunas |
| `core/rules/dax.py` | **novo** — DAX-001 e, se a âncora verificar, DAX-002 |
| `core/rules/performance.py` | PERF-005 |
| `core/rules/runner.py` | `lacunas_de_expressao` e `cobertura_de_expressoes` |
| `core/rules/todas.py` | importar `dax` |
| `core/parser_bim.py`, `core/model.py` | roles, hierarquias, `sortByColumn` e os sítios de DAX da seção 4.5 |
| `tests/` | lexer, varredura, regras novas, e a regressão dos 15 |
| `docs/project/backlog.md` | D-1 (contagem é resultado), o terceiro teste, DAX-003 adiada, e o refinamento da lacuna em Trabalhos Futuros |
| `docs/project/riscos.md` | R-03 com a terceira mitigação; R-12 com o prognóstico da seção 6 |
| `docs/project/status.md` | D-1 e a revisão da meta, para o orientador |

## 9. Fora de escopo

| Item | Motivo |
|---|---|
| Parser DAX com AST | F18, Trabalhos Futuros. É o que mantém o grupo 3 fora |
| Grupo 3 — DAX dependente de contexto | Sem AST a heurística erra demais (`backlog.md`, 29/09) |
| Grupo 4 — regras de M | Próxima etapa; reusa `expressoes.py` com filtro `"m"` |
| DAX-003 — `FILTER` sobre tabela inteira | D-8 |
| Interromper a auditoria por lacuna | D-7, Trabalhos Futuros |
| Interface e relatório mostrando a cobertura | Fase 4, semanas 9–10. **Requisito registrado:** a cobertura aparece junto da contagem de achados, não num apêndice — "15 achados" e "135 de 137 expressões analisadas" devem ser lidos na mesma olhada |

## 10. Pendência que bloqueia parte da implementação

**O Power BI Desktop escreve `roles[].tablePermissions[].filterExpression` no `model.bim`?** Desconhecido. O P8 não tem role nenhuma, então o ramo de RLS seria implementado contra a especificação do TMSL e não contra arquivo observado — a mesma situação que produziu o defeito da MOD-005.

**Ação (Fred, antes do ramo de RLS):** criar uma role com filtro num PBIP no Desktop, salvar e comparar o `model.bim`. Mesma verificação feita em 06/10 para a tabela de data.

Até lá, a implementação segue por todo o resto: lexer, varredura, DAX-001, e a PERF-005 nos sete sítios que não dependem de role.

## 11. Critérios de aceite

1. O lexer tokeniza as 137 expressões DAX do P8 com zero token `DESCONHECIDO`.
2. `len(expressoes) + len(lacunas)` fecha com o total de sítios em escopo, travado em teste.
3. Expressão não tokenizada por completo não chega a nenhuma regra, e aparece em `lacunas_de_expressao` com sítio, objeto, posição e trecho.
4. Cada regra nova tem âncora citável, verificada e transcrita **antes** do código, e a enumeração (a)/(b)/(c) escrita.
5. Cada regra nova tem teste positivo e negativo, e contagem travada no P8.
6. A contagem da PERF-005 no P8 é resultado de verificação sítio por sítio, não de estimativa.
7. Os 15 achados atuais não mudaram, e os 101 testes atuais continuam passando.
8. `python -m core.rules.catalogo` imprime as regras novas com as URLs do Learn.
9. `backlog.md`, `riscos.md` e `status.md` atualizados com D-1 e o terceiro teste.
