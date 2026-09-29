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
  - **Tempo automático está ligado:** o modelo tem tabelas de data geradas automaticamente, apesar de já existir uma `DimCalendar` própria. É um achado real e clássico — serve como primeiro caso de teste do detector. **Correção de 29/09/2026:** a contagem registrada aqui era 5 (1 template + 4 locais); o parser da Fase 2 mostrou que são **4** (1 `DateTableTemplate_*` + 3 `LocalDateTable_*`). Ver a entrada de 29/09.
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

## 23/09/2026 — mudança de disco (R-14)

- **Feito:** projeto inteiro movido de `C:\dev\powerbi-ai-auditor` para **`D:\dev\powerbi-ai-auditor`**. O D: tem 1,5 TB livres, contra praticamente nada em C:.
  - `.venv` **não** foi movido: um ambiente virtual guarda caminhos absolutos em `pyvenv.cfg` e nos scripts de ativação, e quebra ao mudar de pasta. Foi descartado e recriado no destino — Python 3.11.9, pip 24.0, só pip e setuptools instalados, nada a reinstalar.
  - Repositório Git verificado depois da mudança: `git fsck` sem erros, 19 arquivos rastreados, remoto `origin` intacto e `Main` sincronizada com o GitHub.
  - `data/pbip/P8_contoso-vendas/` acompanhou a mudança.
- **Atenção para a semana 2:** mover o projeto **não** resolve o R-14 sozinho. O Ollama baixa os modelos para `C:\Users\<user>\.ollama` e o Playwright instala o Chromium em `AppData\Local\ms-playwright` — os dois em C:, por padrão. Antes de instalar qualquer um, definir `OLLAMA_MODELS` e `PLAYWRIGHT_BROWSERS_PATH` apontando para D:, ou liberar espaço em C:. Sem isso, o download do modelo do spike falha.
- **Próximo passo:** configurar essas duas variáveis, e então rodar o spike de LLM (R-02).

## 23/09/2026 — R-14 mitigado, ambiente pronto para a semana 2

- **Feito:** variáveis de ambiente de usuário criadas, para que nada pesado volte a cair em C:
  - `OLLAMA_MODELS` = `D:\dev\ollama-models`
  - `PLAYWRIGHT_BROWSERS_PATH` = `D:\dev\playwright-browsers`
  - `HF_HOME` = `D:\dev\hf-cache`
- **Feito:** limpeza em C: pelo Fred. O disco saiu de **0,87 GB** para **38,8 GB livres**. R-14 passa a **Mitigado**, com gatilho de reavaliação em 15 GB.
- **Verificação do ambiente:** projeto em `D:\dev\powerbi-ai-auditor`, `git fsck` sem erros, 4 commits, 19 arquivos rastreados, `Main` sincronizada com o GitHub, `.venv` com Python 3.11.9 apontando para o D:, e `data/pbip/P8_contoso-vendas/model.bim` no lugar.
- **Pendência conhecida, sem impacto em disco:** ainda existe um `.venv` antigo dentro do OneDrive, em `Auditoria Power BI usando IA\.venv` (20 MB). Ele não está no PATH permanente — o PATH da máquina não tem nenhuma entrada de Python —, mas o VS Code o ativa automaticamente quando a janela está aberta na pasta do OneDrive. **Abrir o VS Code em `D:\dev\powerbi-ai-auditor`** resolve. A pasta `Projeto` obsoleta também segue lá, e o conteúdo dela já está no GitHub.
- **Próximo passo:** semana 2 — abrir um terminal novo (para herdar as variáveis), instalar o Ollama e rodar o spike de LLM (R-02).

## 23/09/2026 — correção: branch padrão do repositório

- **Problema encontrado:** o repositório tinha dois branches que diferiam apenas por maiúscula. Todo o trabalho estava em `Main`, enquanto o branch padrão do GitHub era `main`, que continha só o "Initial commit" de 08/09/2026 com um README de duas linhas. Na prática, quem abrisse a página do repositório — orientador, banca — via um projeto vazio. As duas histórias eram desconexas: o commit raiz do trabalho (`b7d1735`) não descendia de `b317951`.
- **Decisão (Fred):** consolidar tudo em `main`, o nome convencional, e eliminar a ambiguidade.
- **Feito:** branch local renomeado de `Main` para `main` (via nome temporário, porque o Git no Windows trata os dois como o mesmo ref); `origin/main` sobrescrito com o histórico real usando `--force-with-lease` ancorado no SHA remoto conhecido, para abortar caso o remoto tivesse mudado; branch `Main` apagado do remoto **depois** de confirmar que `main` já tinha os 19 arquivos.
- **Descartado:** o commit `b317951` e seu README de duas linhas, cujo conteúdo já está coberto pelo README atual. Ele permanece como objeto solto no repositório local até a próxima coleta de lixo do Git, caso precise ser recuperado.
- **Estado final:** um único branch `main`, padrão do repositório, local e remoto em `a573cec`, `git fsck` sem erros.
- **Lição para as próximas sessões:** conferir o `default_branch` do GitHub, não só a árvore do commit enviado. Um push bem-sucedido não garante que o trabalho esteja visível na página do repositório.

## 29/09/2026 — Fase 1, semana 2 — quatro decisões de escopo e método

Quatro pontos que estavam em aberto foram decididos. Nenhum exigiu mudança de código — não há código ainda —, mas os quatro mudam documentação de planejamento.

**1. P8 sai do dataset de métricas e vira estudo de caso.** O dataset volta a ser P1–P7, todos MIT. O P8 passa a seção própria da monografia, acompanhando o achado de tempo automático ligado de ponta a ponta. Ganho: toda métrica passa a ser reprodutível por terceiros e a ressalva "apenas P1–P7" desaparece. **Custo: o R-12 volta a Aberto**, porque a inclusão do P8 era exatamente a mitigação desse risco. Contingência P9 mantida, com o gatilho na semana 4. Registrado na 2ª emenda da ADR-005 e em `eval/dataset.md`.

**2. Sem restrição ao uso de API paga.** O fallback do R-02 deixa de ser um plano incerto: se o spike reprovar os dois modelos locais, a ADR-006 abre e a troca é uma linha de configuração, com teto de US$ 10. O impacto do R-02 cai de A para M — a probabilidade continua alta, mas a consequência deixou de ser grave. Isso **não** antecipa a decisão: o spike continua sendo feito com os modelos locais primeiro, porque LLM local gratuito ainda é o resultado mais interessante para o trabalho.

**3. Seleção de regras por detectabilidade, não por cota.** A meta de 20 a 25 regras continua, mas as cotas por categoria viram estimativa. A prioridade passa a ser o que se detecta de forma confiável a partir do `model.bim`: primeiro regras estruturais (modelagem e performance estática), depois DAX com padrão textual inequívoco, por fim DAX dependente de contexto. Uma regra com precisão baixa é pior que uma regra ausente. Registrado em `backlog.md`; o R-03 ganha essa mitigação por construção.

**4. Limitações declaradas com mais detalhe.** Nova seção 11 no plano da Fase 1, com quatro limitações destrinchadas: heurística de DAX (com tabela do que alcança e do que não alcança), performance estática versus medida, escopo do artefato analisado, e alcance estatístico das conclusões — incluindo o viés de anotador único no ground truth, que antes não estava registrado. O texto foi escrito para ir íntegro ao capítulo de metodologia.

- **Problemas:** nenhum.
- **Atenção:** a decisão 1 piorou o R-12 de propósito, trocando significância estatística por reprodutibilidade. Se a semana 4 mostrar poucos achados em P1–P7, o P9 deixa de ser opcional.
- **Próximo passo:** inalterado — instalar o Ollama e rodar o spike de LLM (R-02, critérios na ADR-002).

## 29/09/2026 — Fase 2, semana 3 — ingestão e parser do model.bim

Primeiro código de produto do projeto, escrito em TDD: teste primeiro, visto falhar, depois a implementação mínima. **15 testes passando.**

**Ambiente — um obstáculo resolvido:** o `pip` falhava com `CERTIFICATE_VERIFY_FAILED`. Causa: o **Norton intercepta TLS** nesta máquina (o certificado do PyPI vem emitido por "Norton Web/Mail Shield"). O Windows confia nessa raiz, mas o `pip` usa o bundle do `certifi`, que não a contém. Solução: apontar o `pip` para a mesma raiz já confiada pelo sistema (`ProgramData/Norton/Antivirus/wscert.pem`), gravada em `.venv/pip.ini` — **sem** desabilitar verificação de certificado. Como o `.venv` não é versionado, isso se perde ao recriá-lo; está documentado no README.

**O que foi entregue:**
- `core/ingest.py` — abre pasta local ou `.zip`, localiza a `.SemanticModel` e valida a estrutura. Os erros são escritos para o usuário final, não para o desenvolvedor. O caso TMDL tem mensagem própria, explicando como desligar o preview e avisando que a conversão é irreversível (ADR-001).
- `core/model.py` — esquemas Pydantic do modelo interno: `ModeloSemantico`, `Tabela`, `Coluna`, `Medida`, `Particao`, `Relacionamento`. Cada objeto guarda em `bruto` o dicionário TMSL de origem, para que uma regra possa consultar propriedade ainda não normalizada sem reabrir o arquivo.
- `core/parser_bim.py` — lê o `model.bim` para esses esquemas. Trata a armadilha que a ADR-001 previa: **DAX e M vêm ora como string, ora como lista de linhas**, e são normalizados para uma string só. Não falha por propriedade ausente ou desconhecida.
- `tests/` — 11 testes com fixtures sintéticas (construídas por `escrever_pbip`, em `conftest.py`) e 4 contra o P8 real, que são pulados quando `data/` não existe.
- `pytest.ini`, `requirements.txt`.

**Validação contra o PBIP real (P8):** o parser reproduziu o inventário de 23/09 exatamente — 19 tabelas, 93 medidas, 106 colunas (35 calculadas), 11 relacionamentos, `compatibilityLevel` 1600, e 92 das 93 medidas na tabela `_Medidas`.

**CORREÇÃO — tabelas de data automáticas são 4, não 5.** O registro de 23/09 dizia "5 tabelas de data geradas (`DateTableTemplate_*` e 4 `LocalDateTable_*`)". A contagem correta é **1 `DateTableTemplate_*` + 3 `LocalDateTable_*` = 4**, confirmada de três formas independentes: as tabelas do modelo, a annotation `__PBI_LocalDateTable=true` (3 ocorrências) e as `variations` das colunas de data (3). Corrigido na ADR-005, no `eval/dataset.md` e na entrada de 23/09. Um teste agora trava esse número.

**Detalhe que reforça o achado:** uma das tabelas automáticas foi gerada sobre a coluna `Data` da própria `DimCalendar` — ou seja, o Power BI criou uma tabela de data para a tabela de data. As outras duas vieram de `DimPromotion[StartDate]` e `DimPromotion[EndDate]`. Também há **4 relacionamentos bidirecionais** no modelo, que devem virar o segundo caso de teste do detector.

- **Dívida técnica assumida:** três testes do parser (coluna calculada, partição M, propriedades desconhecidas) passaram na primeira execução, porque a implementação anterior já os cobria. Documentam comportamento em vez de tê-lo dirigido, e ficam como testes de regressão.
- **Pendência inalterada:** o spike de LLM da semana 2 (R-02) não foi feito. Ele não bloqueia a Fase 2, mas continua sendo o que fecha a Fase 1.
- **Próximo passo:** semana 4 — as regras determinísticas, começando pelas estruturais (tempo automático e relacionamentos bidirecionais já têm caso real para teste), conforme o critério de detectabilidade.
