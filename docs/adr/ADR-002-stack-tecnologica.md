# ADR-002 — Stack tecnológica

- **Status:** **VALIDADO** no spike de 29/09/2026 (ver o resultado no fim deste documento); **emendado em 09/10/2026** (recuperação ancorada e conjunto de avaliação da recuperação)
- **Data:** 22/09/2026 · **Revisão:** 22/09/2026 (C-1, C-2, C-6)

## Contexto
A stack precisa rodar nativamente no Windows 11, sem compilador C++, e caber em um orçamento de ~180 h de um desenvolvedor solo iniciante em IA. O ambiente real foi medido antes de fechar a decisão (ver "Ambiente verificado").

## Ambiente verificado (22/09/2026)
| Item | Medido |
|---|---|
| GPU | NVIDIA GeForce RTX 2060, **6144 MiB de VRAM**, driver 591.86 |
| Python instalado | 3.9, 3.10, **3.11.9**, 3.13 |
| Ollama | **não instalado** (instalar no spike da semana 2) |
| Git | 2.55.0.windows.5 |

## Decisão
| Camada | Escolha |
|---|---|
| Linguagem | **Python 3.11.9** (já instalado), `venv`, `pip` |
| Interface | Streamlit |
| Parser / esquema | `json` (stdlib) + Pydantic |
| Regras | Funções Python + heurísticas regex, inspiradas conceitualmente no BPA do Tabular Editor (ver ADR-004 e R-10) |
| RAG | Pipeline próprio, sem framework |
| Embeddings | `BAAI/bge-small-en-v1.5` (sentence-transformers, ~130 MB, CPU) |
| Vetores | ChromaDB persistente |
| LLM | Ollama local, **decisão em dois níveis** (abaixo); fallback para API paga via interface `LLMClient` |
| Relatório | Jinja2 → HTML → Playwright (Chromium) → PDF |
| Testes / avaliação | pytest, pandas |

### LLM: decisão em dois níveis (revisão C-1)
A versão original desta ADR supunha "GPU com ≥ 6 GB". A GPU real tem **exatamente 6 GB**, o que é o limite, não folga: um modelo 7–8B em Q4_K_M ocupa ~4,7–5,0 GB só de pesos, e o cache de contexto (KV cache) soma em cima disso. Com contexto de 8k o Ollama passa a descarregar camadas para a CPU e a latência sobe.

O spike da semana 2 testa dois candidatos:

| Nível | Modelo | Tamanho aprox. | Configuração |
|---|---|---|---|
| Qualidade | `qwen2.5:7b-instruct-q4_K_M` | ~4,7 GB | `num_ctx` fixado em **4096** |
| Velocidade | `qwen2.5:3b-instruct` ou `llama3.2:3b` | ~2 GB | Cabe inteiro na VRAM |

**Critério de decisão, nesta ordem:** (1) taxa de citação válida em 5 prompts de teste; (2) tempo por achado. A ADR-003 limita o dano de um modelo menor: como o LLM não decide se existe achado, um 3B degrada a redação, não a precisão nem o recall da auditoria.

Se os dois falharem (< 4/5 citações válidas ou > 60 s por achado), abrir **ADR-006** para adoção de API paga com teto de US$ 10 no projeto inteiro.

### Idioma do pipeline (revisão C-6)
O corpus da RAG é em inglês e o `bge-small-en-v1.5` é um modelo monolíngue de inglês, mas a interface e o relatório são em português. Portanto:

- **Consultas de recuperação em inglês**: cada regra carrega suas próprias palavras-chave em inglês (ex.: `bidirectional relationship filter ambiguity star schema`).
- **Saída do LLM em português**, instruída no prompt.

Isso mantém o embedding de 130 MB e evita trocar para um modelo multilíngue de ~2 GB (`bge-m3`).

## Alternativas descartadas no MVP
- **LangChain/LlamaIndex:** mais abstração do que um pipeline linear pede; dificulta explicar o funcionamento na banca.
- **WeasyPrint:** exige bibliotecas GTK no Windows.
- **Python 3.12/3.13:** 3.12 exigiria uma instalação sem ganho; 3.13 ainda tem atraso de wheels em pacotes de ML.
- **Modelos ≥ 13B:** não cabem em 6 GB de VRAM nem com folga em 16 GB de RAM.
- **Tabular Editor CLI para executar o BPA:** adiciona dependência .NET, as regras são escritas em LINQ dinâmico, e o repositório de regras não tem licença (ver R-10).

## Critérios do spike (semana 2)
- Todas as bibliotecas instalam no Windows com Python 3.11 sem compilador C++.
- LLM local: menos de 60 s por achado e citação correta em pelo menos 4 de 5 prompts de teste.
- PDF de um HTML de exemplo gerado pelo Playwright.
- Registrar no progress-log: modelo escolhido, tempo médio, uso de VRAM e RAM.

## Resultado do spike — 29/09/2026 — ADR-002 passa a VALIDADO

Ollama 0.34.4 instalado. Os dois candidatos foram medidos sobre os mesmos 5 achados, com `num_ctx=4096` e `temperature=0.2`. Script e dados brutos: `eval/spike_llm.py`, `eval/results/spike_llm.json`.

| Modelo | Carga | Tempo médio | Pior | Citações válidas | VRAM | Veredito |
|---|---|---|---|---|---|---|
| `qwen2.5:3b` | 6,7 s | **2,0 s** | 2,5 s | 5/5 | ~3,4 GB | Aprovado nos critérios |
| `qwen2.5:7b-instruct-q4_K_M` | 9,9 s | **6,0 s** | 6,5 s | 5/5 | **~5,3 GB** | Aprovado nos critérios |

**Decisão: `qwen2.5:7b-instruct-q4_K_M` como modelo principal, `qwen2.5:3b` como contingência.** A ADR-006 **não** será aberta.

### O que o spike confirmou

O orçamento de memória previsto em 22/09 estava certo: o 7B em Q4_K_M ocupa ~5,3 GB dos 6,0 GB de VRAM com contexto de 4096. Cabe, sem folga — exatamente como a ADR-002 previa ao fixar o `num_ctx`. Aumentar o contexto empurraria camadas para a CPU.

Os tempos ficaram uma ordem de grandeza abaixo do limite de 60 s. Mesmo com ~100 achados num modelo grande, a etapa de geração fica em torno de 10 minutos, o que torna viável rodar o pipeline inteiro sem cache — o cache (F16) continua útil para a demo, mas deixa de ser necessidade.

As 10 citações de 10 foram válidas nos dois modelos: a URL citada estava sempre entre as fornecidas. A obrigatoriedade de citação da ADR-003 funciona na prática, e não apenas no desenho.

### Duas limitações dos critérios, descobertas ao ler as respostas

**1. Os critérios não detectam erro factual.** O 3B escreveu "o modelo tem duas tabelas de data geradas automaticamente" quando a evidência entregue dizia quatro. Passou nos dois critérios — respondeu em 1,7 s e citou uma URL válida — e ainda assim afirmou um número errado sobre o dado que recebeu. O 7B não cometeu esse erro em nenhum dos cinco achados.

Consequência: **acrescentar um terceiro critério de fidelidade à evidência** na avaliação da Fase 5, verificando que números e nomes citados na explicação aparecem no achado. É verificável por código, já que o achado é estruturado.

**2. Citação válida não é citação relevante.** No achado das tabelas de data automáticas, o 7B citou `model-date-tables` em vez de `auto-date-time`, que é a página que sustenta o achado. As duas foram fornecidas, então a citação conta como válida pela regra da ADR-003, mas é a menos pertinente das duas.

Consequência: a métrica de citação da Fase 5 deve distinguir **válida** (a URL está entre as recuperadas) de **pertinente** (é a fonte que sustenta aquele achado). A segunda exige julgamento humano e entra na rubrica, não no cálculo automático.

### Ressalva de método

Na primeira execução o 3B reprovou com 84,2 s no primeiro achado e 1,8 a 2,5 s nos demais. Era o carregamento do modelo do disco para a VRAM, não inferência. O script passou a fazer uma chamada de aquecimento fora da medição, e a carga é reportada em separado. O critério de 60 s da ADR-002 descreve custo por achado, e um custo pago uma vez por sessão não pertence a ele.

## Emenda de 09/10/2026 — recuperação ancorada e conjunto de avaliação derivado das âncoras

### Contexto

Três fatos mudaram desde a decisão original:

1. **O corpus cresceu.** O catálogo de fontes (G-8) tem 1.420 páginas a indexar, das
   quais 1.276 são referência de funções DAX e M e 151 são guidance. Uma busca só por
   palavras-chave sobre esse corpus pode trazer a página de uma função qualquer e
   deixar de fora a passagem que sustenta a regra.
2. **O spike de 29/09 já mostrou a falha.** O 7B citou `model-date-tables` em vez de
   `auto-date-time`, a âncora da regra, porque as duas estavam entre os trechos
   recuperados (seção "Duas limitações dos critérios", acima). A citação era válida e
   não era pertinente.
3. **A âncora de cada achado é conhecida.** Todo achado vem de uma regra, e toda regra
   tem `url_canonica` verificada. A coleta (spec `2026-10-09-coleta-da-base-rag-design.md`)
   guarda as âncoras de seção (`#ancora`) de cada página.

### Decisão

1. **Recuperação ancorada em dois níveis.** Para cada achado, a **seção âncora da regra
   entra sempre** como primeiro trecho do contexto. A busca no índice **complementa** com
   outros trechos, nunca substitui a âncora. A validação de citação da ADR-003 segue
   igual; a métrica de citação **pertinente** da Fase 5 passa a ter um gabarito
   objetivo: a seção âncora.
2. **Conjunto de avaliação da recuperação derivado das âncoras, montado antes de
   escolher chunking e embeddings.** Gabarito: para cada regra, a página, a seção e a
   frase-marca da passagem citada. Consultas: uma por regra (9) e uma por achado de
   P1–P7 (53), cada uma com a seção âncora da sua regra como trecho relevante.
   Precision@K e MRR são medidos sobre ele, e é ele que decide chunking, tamanho de
   trecho e o efeito de ter ampliado o corpus — decisão de 09/10 tomada sem medição.
3. **Busca híbrida como alternativa a medir, não como decisão.** Palavra exata (BM25)
   mais embeddings, fundidas por *Reciprocal Rank Fusion* (Cormack, Clarke & Büttcher,
   2009). Texto técnico tem nomes exatos (`DIVIDE`, `CALCULATE`) que um modelo pequeno
   de embeddings pode não distinguir; BM25 é linha de base forte em recuperação
   *zero-shot* (Thakur et al., 2021, BEIR). Entra no MVP **só** se superar a busca
   densa sozinha no conjunto do item 2.

### Consequências

- (+) O trecho que sustenta cada achado está garantido no contexto, independentemente
  da qualidade da busca. A falha observada no spike deixa de ser possível para a fonte
  principal.
- (+) As decisões de chunking e de embeddings passam a ser medidas, não supostas.
- (+) O tamanho do corpus deixa de ser risco para a citação principal; passa a afetar
  só os trechos complementares, e isso é medido.
- (−) Uma consulta de avaliação gerada a partir da própria regra favorece a âncora: o
  número de Precision@K mede a recuperação **dado** o termo da regra, não uma pergunta
  livre. A monografia deve dizer isso ao reportar o número.
- (−) O conjunto tem 62 consultas e 9 gabaritos distintos, porque cada regra tem uma
  âncora. É suficiente para comparar alternativas entre si, não para afirmar desempenho
  geral da recuperação.

## Emenda de 11/10/2026 — recuperação escolhida por medição

### O que foi medido

Com a régua congelada antes de qualquer medição (spec
`2026-10-11-conjunto-de-avaliacao-da-recuperacao-design.md`: 9 gabaritos, 62 consultas,
acerto de um trecho = conter a frase-marca), foram medidas 24 combinações (spec
`2026-10-11-medicao-da-recuperacao-design.md`): chunking por seção (até 350 palavras) ou
por janela (200 palavras, passo 150), com ou sem cabeçalho de contexto, busca densa
(`bge-small-en-v1.5`), BM25 ou híbrida (RRF, k = 60), sobre o corpus completo (1.420
páginas) ou só guidance + âncoras (153). Regra de decisão fixada antes: maior macro
acerto@5 no corpus completo; a menos de 1/9 dela, vence a mais simples. Trechos acima de
512 tokens (~0,8%: JSON, datas, código) são partidos pelo contador de tokens do modelo.
Resultado em `eval/results/recuperacao-2026-10-11.json`, reproduzido idêntico numa
segunda execução.

| Corpus completo | acerto@1 | acerto@5 | MRR@10 |
|---|---|---|---|
| seção, sem cabeçalho, densa | 0,431 | 0,889 | 0,617 |
| seção, sem cabeçalho, **BM25** | 0,444 | **1,000** | 0,613 |
| seção, sem cabeçalho, híbrida | 0,556 | 1,000 | 0,687 |
| seção, com cabeçalho, densa | 0,403 | 1,000 | 0,643 |
| seção, com cabeçalho, BM25 | 0,500 | 1,000 | 0,635 |
| seção, com cabeçalho, híbrida | 0,500 | 1,000 | 0,694 |
| janela, sem cabeçalho, densa | 0,418 | 0,889 | 0,620 |
| janela, sem cabeçalho, BM25 | 0,444 | 0,861 | 0,605 |
| janela, sem cabeçalho, híbrida | 0,549 | 0,986 | 0,677 |
| janela, com cabeçalho, densa | 0,382 | 1,000 | 0,645 |
| janela, com cabeçalho, BM25 | 0,477 | 0,889 | 0,646 |
| janela, com cabeçalho, híbrida | 0,556 | 1,000 | 0,737 |

### Decisão

**Recuperação do MVP: chunking por seção, sem cabeçalho, busca BM25, corpus completo**
— a vencedora pela regra fixada antes de medir (macro acerto@5 = 1,000, complexidade 0).
O Fred decidiu, depois de ver o resultado, **manter a regra** em vez de trocá-la, para que
a medição continue valendo como evidência.

- O item 3 da emenda de 09/10 se resolve assim: a busca híbrida **não entra** no MVP —
  empatou em acerto@5 e a regra prefere a mais simples.
- O `bge-small-en-v1.5` e o ChromaDB continuam instalados e o índice da vencedora guarda
  os vetores, mas **a consulta do MVP não usa embeddings**.
- Na semana 7, o pipeline monta a consulta com `rag.consulta.montar_consulta` e busca com
  `rag.indice.carregar_buscador()`; a seção âncora da regra continua entrando sempre no
  contexto (emenda de 09/10, item 1).

### Limitações declaradas

- (−) **Efeito teto:** 7 das 12 candidatas chegam a acerto@5 = 1,000 (e 8 empatam a menos
  de 1/9), porque as consultas
  carregam os termos da regra (viés já previsto na emenda de 09/10). A métrica que decide
  quase não discrimina.
- (−) **Uma consulta decide:** a densa fica fora do empate só porque `REGRA/MOD-005` acha
  a âncora na posição 7. A MOD-005 tem uma consulta e pesa 1/9 na macro.
- (+) **A ampliação do corpus não atrapalhou:** o corpus guidance não superou o completo
  em acerto@5 (as duas melhores ficam em 1,000).
- **A reavaliar:** se a geração da semana 7 mostrar trechos complementares fracos, a
  híbrida (melhor acerto@1 e MRR entre as simples) é a primeira alternativa, já medida e
  pronta em `rag.busca`.

## Emenda de 12/10/2026 — busca escolhida pela pertinência dos complementares

A régua de 11/10 (âncora entre os 5 primeiros) saturou e deixou de medir o que a busca
decide: desde a semana 7 a âncora entra sempre como trecho [1], e a busca só escolhe os
**complementares** (trechos 2 a 5). Uma régua nova mediu a **pertinência** deles: o Fred
julgou, às cegas quanto à busca, as 89 seções (regra, seção) que BM25, densa e combinada
entregam nas 70 consultas (*pooling*), e a precisão foi calculada sobre a mesma seleção que a
geração usa (`escolher_complementares`). Regra fixada antes de medir: densa ou combinada
substitui o BM25 só com macro ≥ macro do BM25 + 0,10. Spec:
`docs/superpowers/specs/2026-10-12-pertinencia-dos-complementares-design.md`; resultado:
`eval/results/complementares-2026-10-12.json`.

| Precisão dos complementares | BM25 | Densa | Combinada |
|---|---|---|---|
| **Macro (70 consultas, decide)** | **0,62** | 0,67 | 0,65 |
| Micro | 0,39 | 0,45 | 0,45 |
| Macro só das consultas de achado (registro) | 0,49 | 0,62 | 0,54 |
| Régua antiga: acerto@5 / MRR@10 (registro) | 1,000 / 0,613 | 0,889 / 0,613 | 1,000 / 0,687 |

**Decisão: o BM25 fica.** Nenhuma alternativa supera a macro dele por 0,10 (densa +0,05;
combinada +0,03). O índice não muda.

### Limitações declaradas

- (−) **A PERF-001 não tem complementar pertinente em nenhuma busca:** 31 das 32 seções
  julgadas são não pertinentes (a outra, indeterminada), e a precisão é 0 nas três. A
  consulta da PERF-001 carrega a expressão DAX da coluna, e as três buscas se agarram aos
  nomes de função. **O defeito está na consulta, não no tipo de busca** — trocar a busca não
  o resolveria. A âncora em [1] continua sendo o que sustenta a explicação desse achado.
- (−) **A decisão muda conforme o conjunto de consultas.** Só com as consultas de achado (as
  que o pipeline faz), a densa supera o BM25 por 0,13. A regra aprovada antes de medir usa as
  70 consultas, em que as 9 consultas da regra pesam ~41% da macro; o Fred manteve essa regra
  (decisão de 12/10, antes do julgamento). A divergência é declarada, não resolvida a
  posteriori.
- (−) Anotador único, que já tinha visto os complementares fracos do P8; MOD-001, MOD-002,
  MOD-005 e MOD-007 com 1 ou 2 consultas cada.
