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

## 23/09/2026 — Fase 1, semana 1 — G-2 concluído (primeiro PBIP real)

- **Feito:** PBIP salvo pelo Fred a partir do `CONTOSO - Painel de Análise de Vendas Online.pbix` e copiado para `data/pbip/P8_contoso-vendas/` (o `.pbix` foi para `data/pbix/`). Excluídos da cópia: `cache.abf` (172 MB de cache de dados) e `localSettings.json`.

**Validação da ADR-001 — confirmada em projeto real:**

| Verificação | Resultado |
|---|---|
| `.SemanticModel/model.bim` existe | **Sim** |
| `.SemanticModel/definition/` existe | **Não** → salvou em TMSL, preview de TMDL desligado |
| `definition.pbism` → `version` | **4.2** |
| `model.bim` → `compatibilityLevel` | **1600** (`powerBI_V3`) |
| Codificação do `model.bim` | UTF-8 sem BOM, 883 KB |

**Inventário do modelo (PBIP_ID: P8):**

| Objeto | Qtd |
|---|---|
| Tabelas | 19 |
| Medidas | 93 (92 concentradas na tabela `_Medidas`) |
| Colunas | 106, sendo 35 calculadas |
| Relacionamentos | 11 |
| Hierarquias | 4 |
| Perspectivas / roles (RLS) | 0 / 0 |

- **Problemas:** nenhum. Duas observações:
  - **Tempo automático está ligado:** o modelo tem 5 tabelas de data geradas automaticamente (`DateTableTemplate_*` e 4 `LocalDateTable_*`), apesar de já existir uma `DimCalendar` própria. É um achado real e clássico — serve como primeiro caso de teste do detector.
  - A camada de relatório saiu em **PBIR** (`definition/version.json` = 2.0.0, 26 páginas em `definition/pages/`), e não no `report.json` único do formato legado. Sem impacto no MVP: a camada de relatório é **F19, Trabalhos Futuros**.

**Árvore do PBIP (pastas com muitos itens resumidas):**

```
Painel de Vendas (PBIP)
+---Painel de Vendas.Report
|   +---.pbi
|   +---StaticResources
|   |   +---RegisteredResources
|   |   |   \---(46 itens, omitidos)
|   |   \---SharedResources
|   |       \---BaseThemes
|   |           \---CY20SU09.json
|   +---definition
|   |   +---bookmarks
|   |   |   +---Bookmark57e284ad897508f20213.bookmark.json
|   |   |   \---bookmarks.json
|   |   +---pages
|   |   |   \---(26 itens, omitidos)
|   |   +---report.json
|   |   \---version.json
|   +---.platform
|   \---definition.pbir
+---Painel de Vendas.SemanticModel
|   +---.pbi
|   |   \---editorSettings.json
|   +---.platform
|   +---definition.pbism
|   +---diagramLayout.json
|   \---model.bim
+---.gitignore
\---Painel de Vendas.pbip
```

- **Decisão tomada (Fred, 23/09):** o projeto entra oficialmente no dataset de avaliação como **P8**, antecipando a contingência do R-12. ADR-005 emendada e `eval/dataset.md` atualizado de 7 para 8 projetos. Custo assumido: P8 não é reprodutível por terceiros, então toda métrica da monografia deve aparecer também na forma "apenas P1–P7".
- **Verificação de privacidade (exigida pelo R-12) — nada a mascarar:** única fonte externa é `Sql.Databases("localhost\")` sobre o banco público `ContosoRetailDW`, sem host real e sem credenciais; varredura do PBIP inteiro por nome de usuário, `C:\Users`, `OneDrive`, e-mails e menções à instituição não achou nenhuma ocorrência.

- **PROBLEMA SÉRIO — disco C: chegou a 0 byte livre** durante a cópia (475 GB, todos ocupados). Um `cat` falhou com "No space left on device". Contorno aplicado: o `.pbix` de 174 MB foi removido de `data/pbix/` — o original continua na pasta do autor e o pipeline lê o PBIP, não o PBIX — o que devolveu 163 MB. Registrado como **R-14**, e **bloqueia a semana 2**: Ollama e modelos pedem de 5 a 10 GB, e ainda faltam ChromaDB e o Chromium do Playwright.
- **Próximo passo:** liberar espaço em C: (meta: 20 GB livres) **antes** de qualquer coisa. Depois, semana 2 — instalar o Ollama e rodar o spike de LLM (R-02, critérios na ADR-002).
