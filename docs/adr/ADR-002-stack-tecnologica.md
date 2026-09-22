# ADR-002 — Stack tecnológica

- **Status:** Aceita (revisada em 22/09/2026 após verificação do ambiente real) · validação final no spike da semana 2
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
