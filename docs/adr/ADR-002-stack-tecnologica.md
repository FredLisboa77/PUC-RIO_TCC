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

