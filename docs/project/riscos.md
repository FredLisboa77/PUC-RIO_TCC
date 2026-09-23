# Registro de Riscos

Probabilidade (P) e Impacto (I): B/M/A. Atualizar na Revisão Semanal.
Última atualização: **23/09/2026** (G-2 concluído; projeto movido para D:).

| ID | Risco | P | I | Mitigação | Gatilho | Status |
|---|---|---|---|---|---|---|
| R-01 | Microsoft torna TMDL padrão e os novos saves deixam de gerar `model.bim` | M | A | Manter o preview desligado; congelar a versão do Power BI Desktop usada no dataset; a interface `load_model()` permite acrescentar TMDL depois | PBIP salvo sem `model.bim` | Aberto |
| R-02 | LLM local insuficiente na GPU de 6 GB | **A** | A | Spike da semana 2 com dois níveis (7B q4 com `num_ctx=4096` e 3B); ADR-003 limita o dano porque o LLM não decide achados; fallback para API com teto de US$ 10 | > 60 s por achado **ou** < 4/5 citações válidas | Aberto |
| R-03 | Heurísticas regex em DAX/M geram falsos positivos | A | M | Regras conservadoras; teste positivo e negativo por regra; falsos positivos entram na avaliação em vez de serem escondidos | Precisão < 0,7 na semana 8 | Aberto |
| R-04 | Ground truth tardio ou enviesado | M | A | Montar o GT na semana 8, antes de ver os resultados finais; justificar cada linha com referência; não fabricar problemas | GT incompleto na semana 9 | Aberto |
| R-05 | Termos de uso de SQLBI/DAX Guide restringem a cópia | **B** | M | Lista curta e curada (10–15 artigos); cópia local em `rag/store/` fora do Git; citação com URL e data | Termos proibirem armazenamento local | Aberto |
| R-06 | PBIP com dados sensíveis (conexões, caminhos) | **B** | A | `.gitignore` na raiz **antes** do primeiro commit de conteúdo; dataset passa a ser de amostras públicas MIT (ADR-005); nunca ler `cache.abf`; mascarar conexões antes do LLM e do relatório | Qualquer segredo em commit | **Mitigado** |
| R-07 | Estouro de prazo (180 h, trabalho solo) | M | A | Cortes pré-definidos, nesta ordem: (1) PDF, (2) regras M, (3) filtros avançados da UI | Atraso de mais de 1 semana | Aberto |
| R-08 | Dependências com problema de instalação no Windows | B | M | Python 3.11.9, já instalado, com wheels prontos; evitar bibliotecas que exijam compilação | Falha no spike | Aberto |
| R-09 | Poucos PBIP públicos para demo | B | B | `microsoft/powerbi-desktop-samples`, licença MIT confirmada, é a base do dataset (ADR-005) | — | **Resolvido** |
| R-10 | `TabularEditor/BestPracticeRules` não tem arquivo de licença | M | M | Usar apenas como referência conceitual com citação da URL; nunca copiar os `BPARules-*.json` nem reproduzir o texto das regras; ancorar cada regra numa página do Learn (ADR-004) | Qualquer trecho copiado literalmente | Aberto |
| R-11 | Projeto dentro do OneDrive (sincronização de `.venv`, ChromaDB e Chromium) | B | M | Cópia de trabalho movida para fora do OneDrive em 22/09/2026 e realocada para `D:\dev\powerbi-ai-auditor` em 23/09/2026 (ver R-14); GitHub é o backup | Erro de arquivo bloqueado ou sincronização lenta | **Mitigado** |
| R-12 | Amostras públicas da Microsoft têm poucos problemas, reduzindo a significância da avaliação | M | M | Contingência antecipada em 23/09/2026: P8 próprio já incluído no dataset (ADR-005, emenda). Slot P9 continua de reserva para a semana 4 | Menos de ~40 achados no dataset inteiro na semana 4 | **Mitigado** |
| R-13 | Extrator de HTML do Learn quebra com mudança de layout do site | B | M | Guardar o HTML bruto em `rag/store/raw/` para reprocessar sem rebaixar; testes sobre 3 páginas de referência | Extração devolve texto vazio ou com navegação | Aberto |
| R-14 | Disco C: praticamente sem espaço (0 byte livre em 23/09/2026, de 475 GB) | A | A | Projeto inteiro movido para `D:\dev\powerbi-ai-auditor` em 23/09/2026 (D: tem 1,5 TB livres). **Mitigação incompleta:** o Ollama grava os modelos em `C:\Users\<user>\.ollama` e o Playwright grava o Chromium em `AppData\Local\ms-playwright` — ambos em C: por padrão. Antes da semana 2, apontar os dois para D: via `OLLAMA_MODELS` e `PLAYWRIGHT_BROWSERS_PATH`, ou liberar espaço em C: | Qualquer erro "No space left on device"; download de modelo falhando na semana 2 | **Parcialmente mitigado** |

## Mudanças nesta revisão (22/09/2026)
- **R-02** subiu de P=M para **P=A**: a GPU foi medida e tem exatamente 6144 MiB de VRAM, que é o limite para um modelo 7–8B quantizado, não folga.
- **R-05** caiu de P=M para **P=B**: o `robots.txt` de sqlbi.com e dax.guide foi verificado e não bloqueia páginas de artigo.
- **R-06** caiu de P=A para **P=B** e passou a **Mitigado**: o dataset virou amostra pública MIT (ADR-005) e o `.gitignore` da raiz foi criado e testado com `git check-ignore`.
- **R-09** passou a **Resolvido**: fonte MIT identificada.
- **R-10**, **R-11**, **R-12**, **R-13** são novos.
- **R-14** registrado em 23/09/2026, ao copiar o primeiro PBIP: o disco C: chegou a 0 byte livre.
