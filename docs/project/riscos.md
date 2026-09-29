# Registro de Riscos

Probabilidade (P) e Impacto (I): B/M/A. Atualizar na Revisão Semanal.
Última atualização: **29/09/2026** (spike de LLM concluído; R-02 resolvido).

| ID | Risco | P | I | Mitigação | Gatilho | Status |
|---|---|---|---|---|---|---|
| R-01 | Microsoft torna TMDL padrão e os novos saves deixam de gerar `model.bim` | M | A | Manter o preview desligado; congelar a versão do Power BI Desktop usada no dataset; a interface `load_model()` permite acrescentar TMDL depois | PBIP salvo sem `model.bim` | Aberto |
| R-02 | LLM local insuficiente na GPU de 6 GB | **A** | A | Spike executado em 29/09/2026: `qwen2.5:7b-instruct-q4_K_M` roda em ~5,3 GB dos 6 GB de VRAM, a 6,0 s por achado (limite: 60 s) e 5/5 citações válidas. `qwen2.5:3b` fica de contingência a 2,0 s. A ADR-006 não será aberta | — | **Resolvido** |
| R-03 | Heurísticas regex em DAX/M geram falsos positivos | A | M | Regras conservadoras; teste positivo e negativo por regra; falsos positivos entram na avaliação em vez de serem escondidos | Precisão < 0,7 na semana 8 | Aberto |
| R-04 | Ground truth tardio ou enviesado | M | A | Montar o GT na semana 8, antes de ver os resultados finais; justificar cada linha com referência; não fabricar problemas | GT incompleto na semana 9 | Aberto |
| R-05 | Termos de uso de SQLBI/DAX Guide restringem a cópia | **B** | M | Lista curta e curada (10–15 artigos); cópia local em `rag/store/` fora do Git; citação com URL e data | Termos proibirem armazenamento local | Aberto |
| R-06 | PBIP com dados sensíveis (conexões, caminhos) | **B** | A | `.gitignore` na raiz **antes** do primeiro commit de conteúdo; dataset passa a ser de amostras públicas MIT (ADR-005); nunca ler `cache.abf`; mascarar conexões antes do LLM e do relatório | Qualquer segredo em commit | **Mitigado** |
| R-07 | Estouro de prazo (180 h, trabalho solo) | M | A | Cortes pré-definidos, nesta ordem: (1) PDF, (2) regras M, (3) filtros avançados da UI | Atraso de mais de 1 semana | Aberto |
| R-08 | Dependências com problema de instalação no Windows | B | M | Python 3.11.9 com wheels prontos. `pydantic`, `pytest` e Ollama instalados sem compilador em 29/09/2026. Obstáculo real encontrado e resolvido: o Norton intercepta TLS e o `pip` precisou apontar para a raiz confiada pelo sistema (ver README) | Falha ao instalar ChromaDB, sentence-transformers ou Playwright | **Mitigado** (parcial) |
| R-09 | Poucos PBIP públicos para demo | B | B | `microsoft/powerbi-desktop-samples`, licença MIT confirmada, é a base do dataset (ADR-005) | — | **Resolvido** |
| R-10 | `TabularEditor/BestPracticeRules` não tem arquivo de licença | M | M | Usar apenas como referência conceitual com citação da URL; nunca copiar os `BPARules-*.json` nem reproduzir o texto das regras; ancorar cada regra numa página do Learn (ADR-004) | Qualquer trecho copiado literalmente | Aberto |
| R-11 | Projeto dentro do OneDrive (sincronização de `.venv`, ChromaDB e Chromium) | B | M | Cópia de trabalho movida para fora do OneDrive em 22/09/2026 e realocada para `D:\dev\powerbi-ai-auditor` em 23/09/2026 (ver R-14); GitHub é o backup | Erro de arquivo bloqueado ou sincronização lenta | **Mitigado** |
| R-12 | Amostras públicas da Microsoft têm poucos problemas, reduzindo a significância da avaliação | M | M | Em 29/09/2026 o P8 saiu do dataset e virou estudo de caso (ADR-005, 2ª emenda), o que **desfez** a mitigação anterior. Resta o slot **P9**, a decidir na semana 4 | Menos de ~40 achados em P1–P7 na semana 4 | **Aberto** (era Mitigado) |
| R-13 | Extrator de HTML do Learn quebra com mudança de layout do site | B | M | Guardar o HTML bruto em `rag/store/raw/` para reprocessar sem rebaixar; testes sobre 3 páginas de referência | Extração devolve texto vazio ou com navegação | Aberto |
| R-14 | Disco C: praticamente sem espaço (chegou a 0 byte livre em 23/09/2026, de 475 GB) | A | A | Projeto movido para `D:\dev\powerbi-ai-auditor`; `OLLAMA_MODELS`, `PLAYWRIGHT_BROWSERS_PATH` e `HF_HOME` apontados para o D:; limpeza em C: feita pelo Fred em 23/09/2026, devolvendo o disco a **38,8 GB livres**. Reavaliar se C: cair abaixo de 15 GB | Menos de 15 GB livres em C:; erro "No space left on device" | **Mitigado** |

## Mudanças nesta revisão (29/09/2026, tarde — spike)
- **R-02** passa a **Resolvido**. Era o único risco com probabilidade alta e impacto alto do projeto. O 7B cabe na VRAM com folga de ~0,7 GB e responde 10x mais rápido que o limite. Não há mais dependência de API paga.
- **R-08** (dependências com problema de instalação no Windows) passa a **Mitigado** na parte já exercitada: `pydantic`, `pytest` e o Ollama instalaram sem compilador C++. Restam ChromaDB, `sentence-transformers` e Playwright, que serão exercitados nas semanas 5, 6 e 10.
- **R-14** segue **Mitigado**, e o spike o comprovou na prática: os 6,2 GB de modelos foram para `D:\dev\ollama-models` e nada caiu em C:. O C: caiu de 38,8 para 28 GB por causa do instalador do Ollama — ainda acima do gatilho de 15 GB.

## Mudanças nesta revisão (29/09/2026, manhã)
- **R-02** mantém P=A, mas o **impacto cai de A para M**: foi confirmado que não há restrição ao uso de API paga, então o fallback deixa de ser um plano incerto e passa a ser uma troca de configuração com custo limitado a US$ 10.
- **R-12** volta de **Mitigado para Aberto**: o P8 saiu do dataset de métricas e virou estudo de caso, desfazendo a mitigação de 23/09. A contingência P9 segue disponível, com o mesmo gatilho na semana 4.
- **R-03** ganha uma mitigação adicional: o critério de seleção de regras passou a priorizar detectabilidade (ver `backlog.md`, decisão de 29/09/2026), o que tende a reduzir falsos positivos por construção.

## Mudanças na revisão de 22/09/2026
- **R-02** subiu de P=M para **P=A**: a GPU foi medida e tem exatamente 6144 MiB de VRAM, que é o limite para um modelo 7–8B quantizado, não folga.
- **R-05** caiu de P=M para **P=B**: o `robots.txt` de sqlbi.com e dax.guide foi verificado e não bloqueia páginas de artigo.
- **R-06** caiu de P=A para **P=B** e passou a **Mitigado**: o dataset virou amostra pública MIT (ADR-005) e o `.gitignore` da raiz foi criado e testado com `git check-ignore`.
- **R-09** passou a **Resolvido**: fonte MIT identificada.
- **R-10**, **R-11**, **R-12**, **R-13** são novos.
- **R-14** registrado em 23/09/2026, ao copiar o primeiro PBIP: o disco C: chegou a 0 byte livre.
