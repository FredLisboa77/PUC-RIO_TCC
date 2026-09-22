# Progress Log

## 22/09/2026 — Fase 1, semana 1 — planejamento
- **Feito:** planejamento da Fase 1 (análise PBIP, TMDL × model.bim, stack, matriz de funcionalidades, arquitetura, estrutura de repositório, roadmap de 13 semanas); ADR-001 a ADR-003; riscos e backlog.
- **Problemas:** status de licença das fontes não confirmado; estrutura PBIP não validada com projeto real.
- **Próximo passo:** aprovação do gate.

## 22/09/2026 — Fase 1, semana 1 — verificação e gate
- **Feito — verificação das pendências:**
  - Estrutura da pasta `.SemanticModel`, tabela de versões do `definition.pbism`, status de preview do TMDL, irreversibilidade da conversão e natureza do `cache.abf` conferidos contra o Microsoft Learn (página atualizada em 30/05/2026). Todos confirmados → ADR-001 passa a **Aceita**.
  - Ambiente medido: GPU **RTX 2060 com 6144 MiB de VRAM**, Python **3.11.9** já instalado, Ollama **ausente**, Git 2.55.
  - `MicrosoftDocs/powerbi-docs` **não existe publicamente** (404). Plano de coleta da RAG corrigido → ADR-004.
  - `robots.txt` do learn.microsoft.com, sqlbi.com e dax.guide verificados: coleta das páginas de interesse é permitida.
  - `toc.json` de `/power-bi/guidance` baixado: **142 artigos** disponíveis, contagem real em vez de estimativa.
  - `TabularEditor/BestPracticeRules` **sem arquivo de licença** → uso apenas como referência conceitual (R-10).
  - `microsoft/powerbi-desktop-samples` é **MIT** e tem variedade de domínios → base do dataset (ADR-005).
- **Feito — organização do repositório:**
  - Removido o repositório Git vazio (0 commits) da pasta externa do TCC.
  - Cópia de trabalho movida do OneDrive para `C:\dev\powerbi-ai-auditor` (R-11). `Diversos/` ficou no OneDrive como material pessoal, fora do repositório público.
  - Criada a árvore de pastas planejada; documentos da Fase 1 movidos para `docs/adr/` e `docs/project/`.
  - Criado o `.gitignore` na raiz e testado com `git check-ignore` em `data/`, `outputs/`, `rag/store/`, `.env`, `.venv/` e `Diversos/` (R-06).
  - ADR-002 revisada (Python 3.11, LLM em dois níveis, idioma do pipeline); ADR-004 e ADR-005 criadas; riscos R-10 a R-13 registrados.
  - Ambiente virtual criado com Python 3.11 dentro do projeto.
- **Problemas:** nenhum bloqueante. O repositório `PUC-RIO_TCC` é **público**, o que foi levado em conta ao decidir o que commitar.
- **Próximo passo (semana 1):** salvar 1 PBIP real em TMSL, confirmar `model.bim` e a `version` do `definition.pbism`, e colar a saída de `tree /F /A` aqui.
- **Pendente para a semana 2:** instalar Ollama e rodar o spike de LLM (critérios na ADR-002).
