# Conjunto de avaliação da recuperação

- **Data:** 11/10/2026
- **Fase:** 3, semana 6 do roadmap
- **Status:** Rascunho, aguardando revisão do Fred
- **Depende de:** a base extraída em `rag/store/textos/` (spec `2026-10-09-coleta-da-base-rag-design.md`) e os PBIP P1–P7 em `data/pbip/`
- **Decisão que este desenho executa:** emenda de 09/10/2026 da ADR-002, item 2: conjunto de avaliação da recuperação derivado das âncoras, montado **antes** de escolher chunking e embeddings

## 1. Objetivo e contexto

A próxima etapa da Fase 3 escolhe o chunking, o tamanho do trecho e os embeddings, e
decide se a busca híbrida (BM25 + densa, fundidas por RRF) entra no MVP. Pela emenda da
ADR-002, essas escolhas são **medidas**. Esta spec entrega a régua: o gabarito, as 62
consultas e as funções de métrica. Nada é medido aqui. A régua fica pronta e congelada
antes da primeira medição, para que a escolha não se ajuste ao resultado.

### Fatos medidos que moldam o desenho (11/10/2026)

| Fato | Consequência |
|---|---|
| `RegraMeta.url_canonica` aponta para a página, sem `#ancora`; MOD-003 e MOD-006 usam a mesma página (`star-schema`) | A seção âncora é **deduzida** da base extraída, não digitada |
| A frase-marca de cada regra aparece em **exatamente uma** seção da sua página âncora (tabela na seção 2) | A dedução é possível e sem ambiguidade hoje; o gerador falha alto se isso mudar |
| Os 53 achados de P1–P7: PERF-001 19, PERF-003 16, MOD-003 7, DAX-001 6, MOD-006 3, MOD-007 1, MOD-001 1; **MOD-002 e MOD-005 com zero** | A média simples sobre 62 consultas mediria quase só duas regras: a métrica que decide é a **macro por regra** |
| A `mensagem` do achado é escrita em português; o `bge-small-en-v1.5` é monolíngue de inglês (ADR-002, revisão C-6) | A consulta por achado usa os termos da regra em inglês mais o tipo e o nome do objeto, não a mensagem |

### Decisões do Fred nesta etapa

- **Consulta por achado montada pelo pipeline:** é exatamente o texto que o pipeline real
  vai mandar ao índice: os termos da regra mais o contexto do achado. Recusadas: uma
  pergunta escrita à mão por achado (53 textos, escritos por quem conhece a resposta) e
  só as 9 consultas por regra (contrariaria a emenda da ADR-002).
- **Relevância = o trecho contém a frase-marca:** vale para qualquer chunking e pune o
  chunking que corta a passagem ao meio. Recusados: pertencer à seção âncora (conta como
  acerto um pedaço sem a passagem) e as duas métricas em dois níveis.
- **Escopo = conjunto + métricas:** chunking, embeddings, índice e BM25 ficam na spec
  seguinte.
- **Gerador versionado (abordagem A):** as consultas são geradas a partir dos PBIP e
  gravadas num arquivo versionado, conferido por teste, no padrão do `rag/sources.yaml`.
  Recusados: calcular as consultas na hora da medição (a régua mudaria em silêncio com
  qualquer mudança de regra) e escrever as 62 à mão (deixariam de ser a consulta real do
  pipeline).

## 2. Gabarito

**`eval/recuperacao/gabarito.yaml`**, escrito à mão e versionado: uma entrada por regra,
com `id_regra` e `frase_marca`, um trecho de até ~10 palavras da passagem que a regra cita.
As 9 frases que hoje estão em `tests/test_rag_store_real.py` passam a viver **só** aqui, e
o teste passa a lê-las deste arquivo.

A **página** vem da `url_canonica` da regra, convertida para o id do catálogo
(`learn:` + `caminho_sem_idioma(normalizar_url(url))`). A **seção** é deduzida pelo
gerador: é a única seção da página extraída cujo texto, normalizado, contém a frase-marca
normalizada. O resultado da dedução sobre a base de 11/10/2026:

| Regra | Página | Seção âncora |
|---|---|---|
| DAX-001 | `learn:dax/best-practices/dax-divide-function-operator` | `recommendations` |
| MOD-001 | `learn:power-bi/guidance/auto-date-time` | `recommendations` |
| MOD-002 | `learn:power-bi/guidance/relationships-bidirectional-filtering` | `bi-directional-relationship-guidance` |
| MOD-003 | `learn:power-bi/guidance/star-schema` | `star-schema-relevance-to-power-bi-semantic-models` |
| MOD-005 | `learn:power-bi/transform-model/desktop-date-tables` | `set-and-use-date-tables-in-power-bi-desktop` |
| MOD-006 | `learn:power-bi/guidance/star-schema` | `snowflake-dimensions` |
| MOD-007 | `learn:power-bi/guidance/relationships-one-to-one` | `recommendations` |
| PERF-001 | `learn:power-bi/guidance/import-modeling-data-reduction` | `preference-for-custom-columns` |
| PERF-003 | `learn:power-bi/transform-model/desktop-data-types` | `accuracy-of-number-type-calculations` |

A página e a seção deduzidas são gravadas no arquivo gerado (seção 3), para que o
gabarito possa ser lido sem rodar nada.

**Normalização** (`rag/texto.py`, `normalizar(texto) -> str`): aspas tipográficas (`’ ‘ “ ”`)
viram aspas retas, o espaço não separável vira espaço, tudo em minúsculas, espaços
repetidos colapsados. É a função que hoje está dentro de `test_rag_store_real.py`, movida
para o código porque passa a ser usada pela dedução e pela métrica.

## 3. Consultas

**`rag/consulta.py`**, `montar_consulta(meta: RegraMeta, achado: Achado | None = None) -> str`.
Fica em `rag/` e não junto da avaliação porque é **a mesma função que o pipeline real vai
chamar**: o conjunto mede a consulta que será usada.

- **Sem achado (consulta por regra):** os `termos_consulta` da regra, unidos por `"; "`.
- **Com achado:** o mesmo texto, mais `" | "`, o tipo do objeto em inglês e o nome do
  objeto como a regra o registrou em `evidencia.objeto`. Tradução fixa do tipo:
  `tabela → table`, `coluna → column`, `medida → measure`, `relacionamento → relationship`,
  `particao → partition`, `modelo → model`.
  Exemplo: `"auto date/time; hidden auto date/time tables; ... | table DateTableTemplate_6de7..."`.
- Ficam de fora a `mensagem` (em português) e o `trecho` DAX ou M (dominaria a consulta
  com código).

**`eval/recuperacao/consultas.yaml`**, gerado por `python -m rag.avaliacao gerar` e
versionado. Contém:

- `gabaritos`: para cada regra, `id_regra`, `frase_marca`, `id_pagina`, `ancora`;
- `consultas`: 62 entradas, cada uma com
  - `id`: `REGRA/<id_regra>` para as 9 por regra, e `<projeto>/<id_regra>/<n>` para as
    53 por achado (ex.: `P5/DAX-001/3`), com `n` contado a partir de 1, na ordem da saída
    do runner, que é estável;
  - `tipo`: `regra` ou `achado`;
  - `projeto` (`P1`…`P7`, vazio nas consultas por regra), `id_regra`, `objeto` (vazio nas
    consultas por regra) e `texto`.

A consulta aponta para o gabarito pelo `id_regra`: uma regra, um gabarito.

**Fonte dos achados:** as 9 regras do registro rodadas sobre os sete PBIP de
`data/pbip/P[1-7]_*`, pelo mesmo caminho dos testes de PBIP real
(`abrir_pbip` → `ler_modelo` → `avaliar`). O P8 fica fora: é estudo de caso, não dataset de
métricas (ADR-005). Os P1–P7 são MIT, então versionar nomes de tabela e coluna deles não
tem restrição.

**Congelamento:** um teste compara o `consultas.yaml` versionado com o que o gerador produz
agora. Ele é pulado quando `data/pbip/` ou `rag/store/` não existe, como os outros testes
de dados reais. Mudou uma regra ou a base, as consultas ou o gabarito deduzido mudam, e a
mudança aparece como diff no Git, não em silêncio.

## 4. Métricas

**Interface do que será medido** (`rag/avaliacao.py`):

- `Trecho` (Pydantic): `texto: str`, `id_pagina: str`, `ancora: str | None`.
- Um recuperador é qualquer `Callable[[str, int], list[Trecho]]`: recebe o texto da consulta
  e K, devolve no máximo K trechos, em ordem. A régua não sabe nada de chunking, embeddings
  ou BM25.

**Relevância:** um trecho é relevante para uma consulta quando `normalizar(trecho.texto)`
contém `normalizar(frase_marca)` do gabarito da regra da consulta.

**Por consulta**, para K em `(1, 3, 5, 10)`; a busca é feita uma vez, com K = 10:

- **acerto@K:** 1 se há pelo menos um trecho relevante entre os K primeiros, senão 0;
- **Precision@K:** trechos relevantes entre os K primeiros, divididos por K. Com uma só
  passagem relevante por consulta, tende a ser baixa e a repetir o acerto@K; o relatório
  diz isso ao lado do número, para não ser mal lido;
- **MRR@10:** 1 sobre a posição do primeiro trecho relevante, ou 0 se não houver até a
  posição 10.

**Agregação**, por causa do desequilíbrio entre regras:

1. **Macro por regra:** a média de cada métrica dentro de cada regra, depois a média das 9
   regras. **É o número que decide entre alternativas.**
2. **Micro:** a média sobre as 62 consultas, como referência.
3. **Por tipo:** as 9 consultas por regra contra as 53 por achado, para ver se o contexto
   do achado ajuda ou atrapalha.

**Erros listados:** toda consulta sem acerto em K = 10 e toda consulta cujo primeiro acerto
veio depois da posição 1, com o `id`, a posição do primeiro acerto ("não apareceu" quando
não houve) e o `id_pagina#ancora` do primeiro trecho devolvido. É dessa lista que sai a
explicação dos números na monografia.

**Saída:** `avaliar(buscar, conjunto) -> RelatorioRecuperacao` (Pydantic, com os três cortes
e a lista de erros) e `formatar_relatorio(relatorio) -> str`. Gravar o resultado de uma
medição em `eval/results/` fica para a spec seguinte, junto das medições.

## 5. Componentes, erros e testes

### 5.1 Componentes

| Arquivo | Responsabilidade |
|---|---|
| `rag/texto.py` | `normalizar` |
| `rag/consulta.py` | `montar_consulta` |
| `rag/avaliacao.py` | Modelos (`Gabarito`, `Consulta`, `ConjuntoAvaliacao`, `Trecho`, `RelatorioRecuperacao`); leitura do `gabarito.yaml` e do `consultas.yaml`; `deduzir_secao`, `gerar`, `avaliar`, `formatar_relatorio`; comando `python -m rag.avaliacao gerar` |
| `eval/recuperacao/gabarito.yaml` | Escrito à mão: as 9 frases-marca |
| `eval/recuperacao/consultas.yaml` | Gerado: gabaritos deduzidos e 62 consultas; cabeçalho "gerado — não editar à mão" |
| `tests/test_rag_store_real.py` | Passa a ler as frases do `gabarito.yaml` e a usar `rag.texto.normalizar` |

No padrão do G-8: núcleo puro, com arquivo e rede nas bordas. `gerar` recebe injetados o
registro de regras, a leitura de uma página extraída e a lista de achados por projeto, de
modo que os testes rodam sobre base e projetos sintéticos. `eval/` continua sem ser pacote
Python: só guarda dados e documentos.

### 5.2 Erros que falham alto

| Situação | Comportamento |
|---|---|
| Frase-marca em nenhuma seção da página âncora | Falha nomeando a regra e a página |
| Frase-marca em mais de uma seção | Falha nomeando a regra e as seções |
| Regra do registro sem gabarito, ou gabarito de regra inexistente | Falha nomeando o id |
| Página âncora sem JSON extraído | Falha indicando rodar `python -m rag.coleta` e `python -m rag.extracao` |
| `data/pbip/` sem algum de P1–P7 | Falha nomeando o projeto que falta |
| Consulta cuja regra não tem gabarito, em `avaliar` | Falha antes de medir qualquer consulta |
| Recuperador devolve mais de K trechos | Falha: é bug do recuperador e não pode virar métrica |

### 5.3 Testes (pytest, sem rede)

1. **`normalizar`:** aspas tipográficas casam com aspas retas; espaço não separável;
   maiúsculas; espaços repetidos.
2. **`montar_consulta`:** termos unidos por `"; "`; cada tipo de objeto traduzido; nome do
   objeto preservado como está; a mesma entrada dá a mesma saída.
3. **Métricas, com recuperador falso de resultado fixo:** acerto@K, Precision@K e MRR@10
   conferidos com contas feitas à mão em casos pequenos; macro diferente de micro quando
   as regras têm números diferentes de consultas; corte por tipo; lista de erros com a
   posição e com "não apareceu"; recuperador que devolve mais de K trechos falha.
4. **`gerar` sobre dados sintéticos:** seção deduzida; falha para frase ausente e para frase
   ambígua; ids de consulta estáveis e na ordem do runner; consulta por regra para regra
   sem achado.
5. **Dados reais** (pulados sem `rag/store/` e `data/pbip/`): o `consultas.yaml` versionado
   é igual ao que o gerador produz; 62 consultas e 9 gabaritos; MOD-003 e MOD-006 em seções
   diferentes; toda regra do registro tem gabarito.

## 6. Fora de escopo

- Chunking, embeddings, índice (ChromaDB), BM25 e RRF.
- Gravação de resultados de medição em `eval/results/`.
- A escolha do K do pipeline e do número de trechos complementares.
- Consultas escritas à mão ou perguntas livres; a limitação que isso deixa (a consulta
  favorece a âncora) já está declarada na emenda da ADR-002 e vai para a monografia.

## 7. Registros a fazer junto com a implementação

- `progress-log.md`: entrada com o gabarito deduzido, a contagem de consultas por regra e
  por tipo e as decisões desta spec.
- `status.md` e a página do orientador: próximo passo passa a ser a medição de chunking e
  embeddings.
