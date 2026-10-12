# Pertinência dos trechos complementares e a escolha da busca

- **Data:** 12/10/2026
- **Fase:** 3, semana 8 — subprojeto 2 da revisão de meio de projeto
- **Status:** Aprovada pelo Fred em 12/10/2026, depois da checagem de conflitos com a ADR-002, a
  spec da medição de 11/10 e o protocolo de avaliação
- **Depende de:** o índice da semana 6 (`rag/indice.py`, BM25 sobre trechos por seção), o
  contexto da geração (`core/analise/contexto.py`), o conjunto de 70 consultas
  (`eval/recuperacao/consultas.yaml`) e o cache de embeddings da variante `secao-sem`
- **Branch:** `fase3-busca-complementares`

## 1. Objetivo e contexto

Na geração da semana 7, o modelo recebe a **âncora** da regra como trecho [1] e até 4
**complementares** vindos da busca. No P8, para a PERF-001 e a PERF-003, o BM25 trouxe
páginas de funções DAX sem relação com o achado (`INFO.CALENDARCOLUMNREFERENCES`,
`RANKX`, `YEARFRAC`); a âncora segurou a explicação. A emenda de 11/10 da ADR-002 deixou a
busca combinada pronta como alternativa, a reavaliar na semana 8.

**A régua atual não responde a essa pergunta.** Ela mede se a seção âncora aparece entre
os 5 primeiros resultados: saturou em 11/10 (7 de 12 combinações com 9 em 9) e, desde a
semana 7, a âncora entra no contexto sem depender da busca. Esta etapa cria a régua que
falta — **a pertinência dos complementares** — e escolhe a busca por ela.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Como julgar a pertinência | **O Fred julga**, por amostragem combinada (*pooling*, como no TREC): as seções que as três buscas trazem como complementares, julgadas uma vez por regra |
| Unidade | **(regra, seção)** — 89 linhas no levantamento de 12/10 |
| Métrica | **Precisão dos complementares**, média por regra (macro); média simples como referência; `indeterminado` em piso e teto |
| Regra de decisão | Combinada ou semântica substitui o BM25 só se superar a macro dele por **0,10 ou mais**; empate, a mais simples (BM25, semântica, combinada) |
| Fora | Novas estratégias de busca (filtro por seção do corpus, reranqueamento) |

## 2. As buscas e o *pool* (`rag/complementares.py`)

**Três buscas** sobre os mesmos trechos do índice (seção, sem cabeçalho, corpus completo):
BM25, densa (`bge-small-en-v1.5`, vetores do cache `secao-sem`) e combinada (RRF, k = 60,
sobre os 100 primeiros de cada), com as funções que já existem em `rag/busca.py`.

**Seleção idêntica à da geração.** A escolha dos complementares — os 10 primeiros
resultados, pulando a âncora, até 4 trechos e dentro do orçamento de 1.800 palavras — sai
de `montar_contexto` para uma função pura, `escolher_complementares(ancora, resultados)`,
que a geração e a medição passam a usar. Assim a régua mede exatamente o que o modelo
recebe.

**O pool** é a união, por regra, das seções que as três buscas escolhem como complementares
nas 70 consultas. Chave: `<id_regra>|<id_pagina>#<ancora>`.

## 3. Planilha de pertinência

Reaproveita o formato do gabarito das regras (`gabarito/planilha.py`): planilha cega,
protegida, com lista suspensa, gerada por código e convertida num CSV versionado.

- **Arquivo:** `eval/gabarito/pertinencia-complementares.xlsx` (fora do Git, como a outra).
- **Aba "Instruções"** e **uma aba por regra**, com a pergunta e, no topo, a **âncora da
  regra** (página, seção e o texto, cortado em 1.500 caracteres) como referência.
- **Colunas:** `id`, `pagina`, `secao`, `titulo`, `caminho`, `inicio_do_texto` (até 600
  caracteres), `url`, `veredito`, `justificativa`.
- **Pergunta:** "Esta seção ajuda a explicar o problema da regra ou a corrigi-lo, na mesma
  linha da âncora?"
- **Vereditos:** `pertinente`, `não pertinente`, `indeterminado`; justificativa obrigatória
  em `indeterminado`.
- **Cega:** nenhuma coluna diz qual busca trouxe a seção, nem quantas vezes.
- `gerar` recusa sobrescrever; `importar [--parcial]` valida (veredito ausente ou fora da
  lista, justificativa ausente, ID faltando ou sobrando) e grava
  **`eval/recuperacao/pertinencia.csv`** (`id,id_regra,id_pagina,ancora,veredito,justificativa`).

## 4. Medição e decisão

`python -m rag.complementares medir` refaz as três buscas e cruza cada complementar com o
CSV. **Complementar sem julgamento = erro** (o pool mudou desde a geração), sem métrica.

Por busca:

- **precisão por consulta** = complementares pertinentes / complementares entregues;
- **por regra** = média das consultas da regra; **macro** = média das 9 regras; **micro** =
  sobre todas as consultas, como referência;
- **piso** (`indeterminado` = não pertinente) e **teto** (= pertinente); a decisão usa a
  versão principal, sem os indeterminados;
- registro, sem decidir: a régua antiga (acerto@5 e MRR@10 da âncora) nas 70 consultas.

**Regra de decisão** (fixada antes de medir):

1. Se a combinada ou a densa tiver macro **≥ macro do BM25 + 0,10**, ela vence; se as
   duas passarem, vence a de maior macro, e em empate a mais simples (densa antes de
   combinada).
2. Senão, o BM25 fica, e a fraqueza dos complementares vai à monografia como limitação
   declarada, com a âncora em [1] como mitigação.

**Coerência com a ADR-002:** a emenda de 09/10 (item 3) só admite a combinada se ela
superar a densa sozinha; o desempate "densa antes de combinada" preserva isso. A emenda de
11/10 escolheu o BM25 pela régua antiga e apontou a combinada como primeira alternativa se
os complementares fossem fracos — é o que esta etapa mede, com régua nova, sem desfazer a
escolha de chunking, cabeçalho e corpus.

**Limitações declaradas da medição:**

- MOD-001, MOD-002, MOD-005 e MOD-007 têm 1 ou 2 consultas cada; a precisão dessas regras
  vem de poucas consultas, e é por isso que a decisão exige margem de 0,10 na macro.
- O anotador já viu os complementares do P8 (semana 7), em que o BM25 trouxe páginas de
  funções DAX para a PERF-001 e a PERF-003. A planilha é cega quanto à busca, mas o viés
  de quem já viu o problema é declarado.
- O pool vem das três buscas medidas; uma busca nova exigiria julgar o que ela trouxer e
  não estiver no CSV (a medição recusa complementar sem julgamento).

**Saída:** `eval/results/complementares-<AAAA-MM-DD>.json` (precisões por busca, regra e
consulta; decisão e justificativa; ambiente: modelo, versões, sha256 do `consultas.yaml` e
do CSV) e uma tabela no console, em ASCII.

## 5. Se a combinada ou a densa vencer

- `python -m rag.indice construir` ganha **`--busca {bm25,densa,hibrida}`**, que
  substitui só o tipo de busca da configuração vencedora de 11/10 (chunking, cabeçalho e
  corpus ficam). O modelo `Configuracao` não muda: a origem da troca fica registrada em
  `origem-da-busca.json`, ao lado da configuração do índice, com o arquivo de resultado que
  a decidiu, e na emenda da ADR-002.
- O índice passa a precisar do ChromaDB e do embedder, como `BaseRag` já prevê.
- A auditoria do P8 roda de novo (`python -m core.auditoria`), para conferir à mão a
  pertinência dos complementares e o tempo por achado; o resultado vai ao progress-log.

Se o BM25 ficar, nada muda no índice.

## 6. Testes

TDD, sem depender de `data/` nem da base coletada, exceto os marcados:

- `escolher_complementares`: pula a âncora, respeita 4 trechos e o orçamento; a geração
  continua igual (os testes de `contexto` seguem verdes).
- Pool: união por regra, chave estável, sem duplicata.
- Planilha: cega (nenhuma célula cita busca), protegida, lista suspensa, IDs voltam
  idênticos; importação com um teste por falha; CSV só em sucesso.
- Métrica: contas feitas à mão; consulta sem complementar não entra na média (e é
  contada); `indeterminado` em piso e teto; macro ignora regra sem consulta.
- Decisão: BM25 fica com margem < 0,10; vence a de maior macro; empate pela simplicidade.
- `construir --busca`: substitui só a busca, mantém chunking, cabeçalho e corpus, e grava
  `origem-da-busca.json`; sem `--busca`, o índice sai igual ao de hoje.
- Sobre a base real (pulado sem ela): o pool gerado tem as 9 regras.

## 7. Entrega e registro

1. Ferramentas prontas e `pertinencia-complementares.xlsx` gerado (~89 linhas).
2. **O Fred julga a planilha.**
3. `importar`, `medir`; se uma alternativa vencer, `construir --busca` e o P8 de novo.
4. progress-log com as precisões, a decisão e a remedição da régua antiga; ADR-002 com a
   emenda da decisão; `status.md` e a página do orientador.

## 8. Fora do escopo

Filtro por seção do corpus, reranqueamento, mudar o modelo de embeddings ou o chunking,
mudar o número de complementares ou o orçamento, e a qualidade do texto gerado (rubrica da
Fase 5).
