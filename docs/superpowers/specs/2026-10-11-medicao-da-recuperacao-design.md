# Medição da recuperação: chunking, embeddings e busca

- **Data:** 11/10/2026
- **Fase:** 3, semana 6 do roadmap
- **Status:** Aprovado para implementação (11/10/2026)
- **Depende de:** a régua congelada (spec `2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`: `eval/recuperacao/consultas.yaml` e `rag.avaliacao.avaliar`) e a base extraída em `rag/store/textos/`
- **Decisões que este desenho executa:** ADR-002 (embeddings `bge-small-en-v1.5`, ChromaDB persistente) e sua emenda de 09/10/2026, itens 2 e 3 (chunking e tamanho decididos por medição; busca híbrida só se superar a densa)

## 1. Objetivo e contexto

Escolher, **por medição** com a régua já congelada, o chunking, o uso de cabeçalho de
contexto e o tipo de busca (densa, BM25 ou híbrida), e medir o efeito de ter ampliado o
corpus para 1.420 páginas. O vencedor vira o índice persistente que o pipeline da semana 7
vai consultar. A recuperação é **ancorada** (emenda da ADR-002): a seção âncora da regra
entra sempre no contexto, e a busca só complementa. O que se mede aqui é a qualidade da
busca sozinha, que decide os trechos complementares.

### Fatos medidos que moldam o desenho (11/10/2026)

| Fato | Consequência |
|---|---|
| Base: 7.835 seções, 21.437 blocos, 739 mil palavras | Embeddings em CPU levam minutos, não horas |
| Palavras por seção: mediana 36, p90 245, p99 728, máximo 2.873; 212 seções com mais de 500 palavras | A estratégia "seção" precisa partir as seções longas, porque o `bge-small` trunca em 512 tokens |
| As 9 seções âncora têm de 116 a 344 palavras | Cabem inteiras num trecho de 350 palavras; numa janela de 200 palavras, algumas seriam partidas |
| Catálogo: 151 páginas de guidance e 2 âncoras fora dele (`desktop-date-tables`, `desktop-data-types`) | A variante "guidance + âncoras" tem 153 páginas |
| Nada da stack de embeddings está no `.venv`; `HF_HOME` = `D:\dev\hf-cache`; GPU RTX 2060 de 6 GB, reservada ao LLM | Torch só de CPU; o modelo baixa para D: |

### Decisões do Fred nesta etapa

- **Grade enxuta:** 2 chunkings × cabeçalho ligado/desligado × 3 buscas × 2 corpus =
  24 combinações, com um só modelo de embeddings. Recusadas: três tamanhos de janela (~40
  combinações) e um segundo modelo (bge-base).
- **Regra de decisão:** maior macro acerto@5, margem de 1/9 e preferência pela opção mais
  simples (seção 5). Recusadas: macro MRR@10 pura (escolheria complexidade por ruído) e
  macro acerto@1 (ignora os vários trechos complementares).
- **Medição em memória, ChromaDB só para o vencedor:** recusados o Chroma para todas as
  combinações (~8 coleções a descartar) e tirar o Chroma do MVP (contrariaria a ADR-002).
- **Peças do pipeline com a medição por cima (abordagem A):** chunking, embeddings e busca
  são módulos de `rag/` que o pipeline reutiliza. Recusados: um script de medição
  descartável (o pipeline reimplementaria tudo e a medição não mediria o código de
  produção) e um framework (recusado na ADR-002).

## 2. Chunking e corpus — `rag/chunking.py`

**O trecho** (`TrechoIndexado`, Pydantic): `id`, `id_pagina`, `url`, `titulo_pagina`,
`ancora` (a seção onde o trecho começa), `caminho`, `texto` e `texto_indexado`.

- `texto` é o texto puro dos blocos, sem markdown, unido por `"\n"`. **É sobre ele que a
  régua julga o acerto.**
- `texto_indexado` é o que vai para os embeddings e o BM25: o `texto`, precedido ou não do
  cabeçalho de contexto.
- `id`: `<id_pagina>#<ancora>/<n>`, com `n` contado a partir de 1 dentro da página, na ordem.
  Estável para a mesma entrada.
- `para_regua()` converte para o `rag.avaliacao.Trecho` (`texto`, `id_pagina`, `ancora`).

**Estratégia `secao`:** cada seção vira um trecho. Uma seção com mais de **350 palavras**
(~470 tokens) é partida **nas fronteiras de bloco**, acumulando blocos até o limite. Um
bloco que sozinho passe do limite (tabela ou código longo) é partido por palavras, em
pedaços de no máximo 350. Os pedaços de uma seção partida mantêm a `ancora` e o `caminho`
da seção.

**Estratégia `janela`:** o texto da página inteira, seção após seção, em janelas de
**200 palavras** (~256 tokens) com passo de **150** (sobreposição de 50). A janela pode
atravessar seções; a `ancora` e o `caminho` são os da seção em que ela começa. A última
janela da página pode ser menor. Uma página com menos de 200 palavras vira uma janela só.
Com a sobreposição de 50 palavras, toda frase de até 50 palavras cabe inteira em alguma
janela.

**Cabeçalho de contexto** (ligado ou desligado): a linha `<titulo_pagina> › <caminho>`
antes do texto, em `texto_indexado`. Exemplo: `Understand star schema and the importance for
Power BI › Snowflake dimensions`. Nunca entra em `texto`.

**Corpus:**
- `completo`: as 1.420 páginas com `indexar: true`;
- `guidance`: as 153 páginas cuja `origem` inclui `toc:power-bi/guidance` ou alguma
  `regra:*`. É um filtro sobre os trechos do corpus completo, sem recalcular nada.

**Limites em palavras, não em tokens:** o chunking fica uma função pura, sem depender do
tokenizador. Um teste de dados reais mede, com o tokenizador do `bge-small`, o maior número
de tokens entre os trechos da estratégia `secao`; se algum passar de 512, o limite de 350
palavras é reduzido antes da medição, e a mudança é registrada.

## 3. Embeddings — `rag/embeddings.py`

- `BAAI/bge-small-en-v1.5` via sentence-transformers, **torch só de CPU**, versões fixadas
  no `requirements.txt` (escolhidas no plano). A GPU fica para o LLM.
- Vetores normalizados: a similaridade de cosseno vira produto escalar.
- **Consultas** recebem o prefixo que o modelo recomenda para busca de passagens:
  `Represent this sentence for searching relevant passages: `. É fixo, fora da grade.
- **Cache em disco:** `rag/store/embeddings/<nome>-<hash>.npy`, um arquivo por
  combinação de chunking e cabeçalho. O hash cobre o nome do modelo e todos os
  `texto_indexado` em ordem: mudou o chunking, o extrator ou o modelo, o cache não casa e é
  recalculado. Arquivo ilegível ou com forma errada é recalculado, com aviso.
- O modelo (~130 MB) baixa uma vez para `D:\dev\hf-cache`. É a única rede desta etapa.
- Interface: `Embedder` (Protocol) com `vetores(textos) -> np.ndarray` e
  `vetor_consulta(texto) -> np.ndarray`, para que os testes usem uma implementação falsa e
  determinística.

## 4. Busca — `rag/busca.py`

Cada busca é uma fábrica que recebe os trechos (e os vetores, na densa) e devolve um
`rag.avaliacao.Buscador`, a interface que a régua já aceita.

- **Densa:** produto escalar da consulta com todos os trechos permitidos; os K maiores.
- **BM25:** `rank-bm25` (`BM25Okapi`). Tokenização: minúsculas e sequências de letras e
  dígitos (`[a-z0-9]+`). Sem stemming. O índice é montado sobre o `texto_indexado`.
- **Híbrida:** RRF com k = 60 (Cormack, Clarke & Büttcher, 2009) sobre os 100 primeiros de
  cada lista: `pontuação(d) = Σ 1 / (60 + posição)`.
- **Filtro de corpus:** um conjunto de `id_pagina` permitidos, aplicado antes do ranking nas
  três buscas.
- Empates de pontuação são resolvidos pela ordem dos trechos, para que o ranking seja
  determinístico.

## 5. Medição e regra de decisão — `rag/medicao.py`

`python -m rag.medicao`:

1. Lê o conjunto (`eval/recuperacao/consultas.yaml`) e as páginas extraídas; monta os
   trechos das 2 estratégias, com e sem cabeçalho; calcula ou lê do cache os embeddings.
2. **Oráculo:** para cada chunking, um recuperador que devolve só os trechos da seção
   âncora de cada regra precisa dar **acerto@1 = 1,0 nas 9 regras**. Prova que o chunking
   não parte a frase-marca. Falhou, a medição para.
3. Mede as 24 combinações com `rag.avaliacao.avaliar`.
4. Aplica a regra de decisão e imprime a tabela: uma linha por combinação, com macro
   acerto@1/3/5/10, macro MRR@10, micro acerto@5 e acerto@5 por tipo.
5. Grava `eval/results/recuperacao-<AAAA-MM-DD>.json` com, por combinação, a configuração,
   as métricas (macro, micro, por tipo, por regra) e a **lista de erros explícita**; o
   ambiente (modelo, versões de torch, sentence-transformers e rank-bm25, número de trechos
   por chunking, `versao_extrator`, sha256 do `consultas.yaml`); e a decisão com a
   justificativa. O relatório avisa que o Precision@K da janela conta passagens repetidas
   pela sobreposição; a decisão não usa Precision@K.

**Regra de decisão**, fixada antes de medir:

1. **Candidatas: só as 12 combinações do corpus completo**, que é o decidido em 09/10. As do
   corpus `guidance` medem o efeito da ampliação. Se alguma superar a melhor do corpus
   completo por **1/9 ou mais** em macro acerto@5, a medição **avisa**, e a decisão sobre o
   corpus é do Fred.
2. **Melhor** = a maior macro acerto@5. **Empatadas** = as candidatas a menos de 1/9 dela.
3. Entre as empatadas, vence a de **menor complexidade**: híbrida +1, janela +1,
   cabeçalho +1 (densa e BM25 valem 0). Persistindo o empate: maior macro MRR@10; depois a
   ordem fixa densa, BM25, híbrida; depois seção antes de janela; depois sem cabeçalho antes
   de com.

## 6. Índice do vencedor — `rag/indice.py`

`python -m rag.indice construir`:

- Lê a configuração vencedora do resultado mais recente em `eval/results/`.
- Grava os trechos em `rag/store/indice/trechos.jsonl` e os vetores numa coleção ChromaDB
  persistente em `rag/store/chroma/` (métrica de cosseno), com `id_pagina`, `ancora`,
  `caminho` e `url` como metadados. Os vetores vêm do cache, sem recalcular.
- Se o vencedor usa BM25 (sozinho ou na híbrida), o BM25 é remontado em memória a partir do
  `trechos.jsonl` ao carregar.
- `carregar_buscador() -> Buscador`: a busca que o pipeline vai usar.
- **Conferência:** o Chroma usa vizinhos aproximados (HNSW), então o ranking pode diferir do
  exato em casos raros. O teste compara a **métrica**: a macro acerto@5 com o buscador
  carregado do índice é igual à medida em memória para o vencedor.

## 7. Erros, testes e execução

### 7.1 Erros que falham alto

| Situação | Comportamento |
|---|---|
| `rag/store/textos/` ou `eval/recuperacao/consultas.yaml` ausente | Falha indicando o comando a rodar antes |
| Falha ao baixar ou carregar o modelo | Falha nomeando o modelo e o `HF_HOME` |
| Oráculo abaixo de 1,0 | A medição para, listando regra e chunking |
| Cache de embeddings ilegível ou com forma errada | Recalcula, com aviso |
| `rag.indice construir` sem resultado de medição | Falha indicando rodar `python -m rag.medicao` |
| Configuração vencedora sem cache de embeddings | Falha indicando rodar `python -m rag.medicao` |

### 7.2 Testes (pytest, sem rede)

1. **Chunking** sobre páginas sintéticas: partição nas fronteiras de bloco; bloco maior que
   o limite; seção curta inteira; janelas com sobreposição e última janela menor; página
   curta numa janela só; cabeçalho só no `texto_indexado`; ids estáveis; filtro do corpus
   `guidance` pela `origem`.
2. **Embeddings:** cache gravado e reaproveitado; invalidado quando muda um texto ou o nome
   do modelo; arquivo corrompido recalculado. Com um `Embedder` falso, sem modelo.
3. **Buscas** com vetores feitos à mão: ordem da densa; BM25 favorecendo o termo exato;
   conta do RRF; filtro de páginas; desempate determinístico; nunca mais de K.
4. **Regra de decisão** sobre resultados sintéticos: margem de 1/9; preferência pela mais
   simples; desempate por MRR e pela ordem fixa; aviso quando o corpus `guidance` supera o
   completo; nenhuma candidata do corpus `guidance` escolhida sozinha.
5. **Dados reais** (pulados sem `rag/store/`; os que usam o modelo rodam com
   `HF_HUB_OFFLINE=1` e são pulados se o modelo não estiver no cache): o oráculo nas duas
   estratégias; o máximo de tokens dos trechos `secao` ≤ 512; a equivalência da métrica com o
   índice Chroma.

### 7.3 Execução real (passo do plano)

1. Instalar as dependências e baixar o modelo.
2. `python -m rag.medicao` — conferir o oráculo, a tabela e o JSON.
3. `python -m rag.indice construir` e o teste de equivalência.

Cada passo salvo: commit e números no `progress-log.md`. Embeddings, Chroma e trechos ficam
em `rag/store/`, fora do Git; o JSON de resultado vai para o Git.

## 8. Fora de escopo

- Geração com o LLM, prompt e validação de citação (semana 7).
- Rerankers e outros modelos de embeddings.
- O número de trechos complementares no prompt.
- Recoleta da base.

## 9. Registros a fazer junto com a implementação

- `requirements.txt`: torch (CPU), sentence-transformers, rank-bm25, chromadb e numpy,
  versões fixadas.
- ADR-002: emenda com o resultado e a escolha.
- `progress-log.md`: a tabela da medição, o oráculo, o vencedor e a justificativa.
- `status.md` e a página do orientador: a recuperação escolhida e o próximo passo
  (geração com citação, semana 7).
