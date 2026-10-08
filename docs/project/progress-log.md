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

## 29/09/2026 — Fase 1, semana 2 — spike de LLM concluído; **Fase 1 encerrada**

Ollama 0.34.4 instalado via winget. Os dois candidatos da ADR-002 foram baixados e medidos sobre os mesmos 5 achados (`num_ctx=4096`, `temperature=0.2`). Script em `eval/spike_llm.py`, dados brutos em `eval/results/spike_llm.json`.

| Modelo | Carga | Tempo médio | Pior | Citações | VRAM |
|---|---|---|---|---|---|
| `qwen2.5:3b` | 6,7 s | 2,0 s | 2,5 s | 5/5 | ~3,4 GB |
| `qwen2.5:7b-instruct-q4_K_M` | 9,9 s | 6,0 s | 6,5 s | 5/5 | ~5,3 GB |

**Decisão: 7B como principal, 3B como contingência. A ADR-006 não será aberta** — não haverá API paga. A ADR-002 passa a VALIDADO e o **R-02, único risco de probabilidade alta e impacto alto do projeto, passa a Resolvido.**

**O orçamento de memória da ADR-002 estava correto:** o 7B ocupa ~5,3 GB dos 6,0 GB de VRAM com contexto de 4096. Cabe, sem folga, exatamente como previsto ao fixar o `num_ctx`. Os tempos ficaram uma ordem de grandeza abaixo do limite de 60 s.

**O `OLLAMA_MODELS` definido em 23/09 provou seu valor:** os 6,2 GB de modelos foram para `D:\dev\ollama-models` e nada caiu em C:. Sem aquela variável, o R-14 teria voltado hoje. O C: caiu de 38,8 para 28 GB por causa do instalador do Ollama, ainda acima do gatilho de 15 GB.

**Dois achados que os critérios da ADR-002 NÃO capturaram**, e que só apareceram ao ler as respostas:

1. **Erro factual passa pelos critérios.** O 3B escreveu "o modelo tem duas tabelas de data geradas automaticamente" quando a evidência entregue dizia quatro. Respondeu em 1,7 s, citou URL válida, e afirmou um número errado sobre o dado que recebeu. O 7B não errou em nenhum dos cinco. Isso pesa mais na escolha do 7B do que a diferença de tempo, e vira um **terceiro critério de fidelidade à evidência** na avaliação da Fase 5 — verificável por código, já que o achado é estruturado.
2. **Citação válida não é citação pertinente.** No mesmo achado o 7B citou `model-date-tables` em vez de `auto-date-time`, que é a página que de fato sustenta o achado. As duas foram fornecidas, então a citação é válida pela regra da ADR-003, mas é a menos relevante. A métrica da Fase 5 deve separar as duas coisas; pertinência exige julgamento humano e vai para a rubrica.

**Ressalva de método:** na primeira execução o 3B "reprovou" com 84,2 s no primeiro achado e 1,8 a 2,5 s nos demais. Era carregamento do modelo para a VRAM, não inferência. O script passou a fazer uma chamada de aquecimento fora da medição e a reportar a carga em separado. O critério de 60 s descreve custo por achado; um custo pago uma vez por sessão não pertence a ele. Sem essa correção, o 3B teria sido descartado por um motivo inexistente.

- **Consequência para o cronograma:** com 6 s por achado, o pipeline inteiro sobre um modelo grande fica em torno de 10 minutos na etapa de geração. O cache de resultados (F16) continua útil para a demo, mas deixa de ser necessidade.
- **Situação das fases:** Fase 1 encerrada. Fase 2 em andamento, com ingestão e parser prontos.
- **Próximo passo:** semana 4 — as regras determinísticas, começando pelas estruturais.

## 06/10/2026 — Fase 2, semana 4 — motor de regras e as oito regras estruturais

Segundo bloco de código de produto, em TDD. **100 testes passando.**

**O trabalho que mais rendeu não foi o código.** Antes de implementar, cada regra
teve a âncora conferida no Microsoft Learn. Isso eliminou três das oito regras
propostas e mudou uma quarta:

- **PERF-004** (tabela calculada em DAX) caiu porque a página que a sustentaria
  **recomenda** tabelas de data em `CALENDAR`/`CALENDARAUTO`. Em P8 seu único
  achado era a `DimCalendar`: 100% do que a regra produzia seria refutado pela
  fonte citada.
- **PERF-002** (coluna-chave agregável) caiu por falta de passagem citável. A
  frase próxima no Learn é contextual a outro exemplo, e a origem da regra era o
  BPA do Tabular Editor, recusado em 22/09 por licença (R-10). Os 5 objetos que
  ela apontava voltam no backlog como candidata "coluna sem uso".
- **MOD-004** (relacionamento entre tipos diferentes) caiu sem âncora e com
  dúvida sobre o produto permitir criar a condição.
- **PERF-001** passou a excluir a dimensão de data: 6 dos seus 7 achados em P8
  eram as colunas de calendário da `DimCalendar`, que a documentação recomenda
  acrescentar.

Entraram três regras com passagem verbatim: **MOD-005** (dimensão de data não
marcada), **MOD-006** (dimensão em floco de neve) e **MOD-007** (relacionamento
um-para-um). A regra passou a constar do `backlog.md`: sem passagem citável, a
regra não entra.

**MOD-007 nasceu de um detalhe de cardinalidade.** O P8 tem um relacionamento com
`fromCardinality: "one"` explícito — `DimGeography[CustomerKey] →
DimCustomer[CustomerKey]` é um-para-um. Disso vieram duas correções: ele não é elo
de floco de neve, porque num um-para-um nenhuma ponta é lado "muitos"; e MOD-002
não pode marcá-lo, porque a documentação diz que todo um-para-um é
obrigatoriamente bidirecional — o achado teria recomendação impossível de
cumprir. O problema real é o um-para-um, e MOD-007 o afirma com a recomendação
que a documentação de fato dá.

**O que foi entregue:**
- `core/rules/base.py` — `RegraMeta`, `Evidencia`, `Achado`. O `RegraMeta` se
  recusa a existir sem URL canónica, termos de consulta e recomendação padrão
  com texto real. O achado carrega só a ocorrência: o catálogo é fonte única.
- `core/rules/registry.py` — decorador `@regra` e registro; ID duplicado é erro
  na importação.
- `core/rules/escopo.py` — as exclusões, sob um princípio: auditar o que o autor
  escreveu. Tabelas de data automáticas, tabelas só de medidas, parâmetros
  hipotéticos, tabelas de cluster e colunas de agrupamento ficam fora, cada uma
  por predicado em TMSL e nenhuma por nome de objeto.
- `core/rules/modelagem.py` e `performance.py` — as oito regras.
- `core/rules/runner.py` — ordem estável (severidade, ID, objeto) e isolamento
  de erro por regra, com `regras_com_falha` no resultado.
- `core/rules/catalogo.py` — `python -m core.rules.catalogo` imprime a tabela de
  regras da monografia. As URLs canónicas são também as fontes que a RAG precisa
  conter (G-8).

**Validação contra o P8:** 15 achados, com as contagens travadas em teste —
MOD-001: 4, MOD-002: 3, MOD-003: 2, MOD-005: 1, MOD-006: 2, MOD-007: 1,
PERF-001: 1, PERF-003: 1. As regras encadeiam uma causa, e não só listam
sintomas: a `DimCalendar` nunca foi marcada como tabela de data, então o Power BI
gerou uma tabela de data local para a própria `DimCalendar[Data]`.

**Correção no modelo interno:** o parser passou a normalizar a cardinalidade do
relacionamento (`one`/`many` → `um`/`muitos`), que antes misturava os dois
vocabulários, e a expor `type`, `summarizeBy`, `dataCategory` e `source.type`.

**Um defeito encontrado na execução:** o runner acumulava os achados com
`list.extend` direto sobre o gerador da regra. Como `extend` acrescenta item a
item, uma regra que levantasse exceção **depois** de já ter produzido achados
deixaria metade da saída no resultado — e a falha apareceria em
`regras_com_falha` com as contagens já contaminadas. Os achados de cada regra
passam agora por uma lista local: saída parcial de regra com defeito é descartada
inteira.

- **Pendência:** confirmar empiricamente que a marcação de tabela de data aparece
  como `dataCategory: "Time"` no TMSL — marcar a `DimCalendar` no Desktop, salvar
  o PBIP e comparar o `model.bim`. A regra está no catálogo com nota de
  verificação até lá. **Fechada em 08/10/2026 — a suposição estava errada; ver a
  entrada daquele dia.**
- **Atenção ao R-12:** o conjunto rende 15 achados no P8, um modelo visivelmente
  problemático. O gatilho da semana 4 é "menos de ~40 achados em P1–P7". Rodar as
  oito regras sobre P1–P7 assim que os PBIP existirem deixou de ser tarefa da
  semana 8.
**A revisão final achou seis defeitos de precisão que o P8 não exibe**, todos
corrigidos com teste que falhou primeiro. Os dois que mais importam:

- **A dimensão de data de chave substituta inteira era invisível.** `dimensao_de_data`
  só reconhecia relacionamento `dateTime → dateTime`, e a convenção de data
  warehouse usa inteiro no formato `aaaammdd`. Com a dimensão invisível, PERF-001
  voltava a marcar as colunas de calendário que a documentação recomenda
  acrescentar — o defeito que derrubou PERF-004, reaberto por outra porta, e que
  teria contaminado a medição de P1–P7 desta semana. Agora são três sinais: o
  relacionamento entre datas, `dataCategory: "Time"`, e partição calculada
  começando em `CALENDAR`/`CALENDARAUTO`.
- **Uma dimensão calculada com uma medida pendurada saía inteira da auditoria.**
  Toda coluna de tabela calculada é `calculatedTableColumn`, então o único sinal
  que separava a `_Medidas` de uma dimensão de verdade era ter medida. O limite
  de uma coluna resolveu.

Os outros quatro: MOD-006 tratava um-para-um e muitos-para-muitos como cadeia de
floco de neve e emitia mensagem com buraco no lugar do nome da tabela; a busca da
severidade na ordenação estava fora do isolamento de erro, de modo que um
`id_regra` digitado errado matava a auditoria inteira; `"annotations": null`
derrubava as oito regras de uma vez; e MOD-002 afirmava "filtra nos dois
sentidos" sobre relacionamento inativo, que não filtra nada até
`USERELATIONSHIP`. As 15 ocorrências do P8 não mudaram com nenhuma das correções.

- **Próximo passo:** as regras de DAX por padrão textual (grupo 2 do critério de
  detectabilidade), sobre o motor já provado.

## 08/10/2026 — Fase 2, semana 4 — MOD-005 reescrita sobre evidência no arquivo

- **Feito:** a pendência da entrada de 06/10 virou um defeito. A verificação
  empírica mostrou que a suposição estava errada: **o Power BI Desktop não grava
  a marcação de tabela de data no `model.bim`.** Num PBIP salvo pelo Desktop,
  `dataCategory` aparece só em coluna, nunca em tabela, e `isDateTable` não
  aparece em lugar nenhum. O TOM representa a marcação como
  `Table.DataCategory`, mas isso só chega ao arquivo por Tabular Editor ou pelo
  endpoint XMLA.

  A regra lia a ausência de `dataCategory: "Time"` como prova de não-marcação.
  Como essa propriedade nunca está lá, ela marcaria também a dimensão
  **corretamente** marcada — um falso positivo garantido em qualquer PBIP vindo
  do Desktop, que é todo o escopo de entrada do MVP.

- **A prova que substituiu a suposição é indireta e vem da própria
  documentação:** marcar a tabela faz o Power BI **remover** a tabela de data
  automática que havia criado para aquela coluna. Então uma `variations` da
  coluna de data apontando para uma tabela de data automática
  (`__PBI_LocalDateTable`) prova, no arquivo, que a marcação não aconteceu. O
  vínculo está em `defaultHierarchy.table`, dentro da `variations` da coluna.

- **Com o Tempo automático de data/hora desligado, a regra cala.** Não há
  nenhum sinal no arquivo, e afirmar sem evidência era exatamente o defeito
  anterior. Falso negativo declarado na nota de verificação do catálogo, e
  travado em teste (`test_mod005_cala_quando_nao_ha_prova_no_arquivo`). Na
  prática o alcance é pequeno: a condição que esconde MOD-005 é o tempo
  automático desligado, que é o próprio objeto de MOD-001.
  `dataCategory: "Time"`, quando presente, continua valendo como marcação
  explícita — e aí a regra também se cala.

- **O que não mudou:** `dimensao_de_data` segue usando `dataCategory: "Time"`
  como um dos três sinais de identificação da dimensão. Ali é heurística de
  reconhecimento, não prova de marcação — a presença informa, a ausência não
  conclui nada, e os outros dois sinais cobrem o caso do Desktop.

- **Validação:** 101 testes passando, os 9 do PBIP real incluídos. As 15
  ocorrências do P8 e a contagem de MOD-005 em 1 não mudaram: a `DimCalendar`
  nunca foi marcada, e é justamente por isso que o Power BI gerou a tabela de
  data local para a própria `DimCalendar[Data]` — a cadeia causal do estudo de
  caso agora é lida pela regra na mesma evidência que a sustenta.

- **A lição, para a monografia:** o critério de detectabilidade precisa de um
  terceiro teste, além de "existe âncora no Learn" e "é decidível no TMSL": **a
  propriedade que a regra lê é escrita pela ferramenta que gera a entrada.** Das
  oito regras, essa foi a única que passou nos dois primeiros e falhou no
  terceiro, e a falha só apareceu por verificação contra um arquivo real.

- **Fechamento da branch:** a Fase 2 soma 20 commits de conteúdo, de `16527cf`
  (design do motor de regras) a `c09f49d` (a correção de MOD-005), mais este
  registro de fechamento. Os três primeiros — design,
  verificação das âncoras e plano — foram feitos na `main`; a branch
  `fase2-motor-de-regras` nasceu em `96b2ac2` e trouxe os 17 commits de
  implementação, de `25befe9` a `c09f49d`. Mergeada na `main` em 08/10/2026 por
  fast-forward, consistente com o histórico linear do projeto, e verificada no
  resultado do merge: 101 testes passando.

  Porque o merge foi fast-forward, nenhum commit menciona a branch. A referência
  `origin/fase2-motor-de-regras` foi **deliberadamente preservada** no remoto,
  apontando para `c09f49d`, como registro do recorte da fase — e este parágrafo
  é o registro dentro do repositório, que sobrevive a qualquer limpeza futura de
  branches.

- **Próximo passo:** as regras de DAX por padrão textual (grupo 2 do critério de
  detectabilidade), sobre o motor já provado.

## 08/10/2026 — Fase 2, semana 4 — rendimento do grupo 2 no P8, verificado

A spec do grupo 2 proibiu afirmar precisão a partir da sondagem que o
dimensionou: aquela sondagem usava expressão regular, antes de o lexer
existir, e é boa para desenhar regra, não para medir rendimento. Esta entrada
é a remedição com o instrumento real — `core/dax.py` e o que ele alimenta —
contra o P8, e o registro explícito de qual afirmação cada número sustenta.

**DAX-001 — recontada com o lexer.** A regra devolve zero achados no P8. O
controle — todo operador `/` nas 105 expressões em escopo, inclusive as de
denominador constante que a regra deixa passar de propósito — também devolve
zero: não há nenhuma barra no escopo, constante ou não. O zero é, portanto,
**confirmado pelo lexer e pelo controle ao mesmo tempo**: não é só a regra
que cala, é o próprio sinal que não existe no texto auditado.

O arquivo tem, sim, quatro divisões reais — `INT(([MonthNo] + 2) / 3)`,
repetida nas quatro tabelas de data automáticas, denominador constante,
exatamente o caso que a documentação recomenda com o operador. Elas não
entram na conta porque `tabelas_em_escopo` exclui essas tabelas antes de a
varredura de DAX rodar — é exclusão de escopo, deliberada e já testada, não
lacuna do lexer nem cegueira de `_e_constante`. Achado novo desta medição: a
própria Microsoft segue, no template que o Power BI gera, a mesma regra que
DAX-001 cobra do autor.

**O que esta medição autoriza:** dizer que, no P8, DAX-001 não tem nenhuma
divisão para marcar, nem dentro nem fora do seu critério de corte — zero
verdadeiro, causa "ausência de defeito". **O que não autoriza:** dizer que a
regra "é precisa". Precisão pede um corpus com divisão de denominador
variável para testar se a regra marca quando deveria, e o P8 não tem esse
caso — a verificação de precisão aguarda a Fase 5.

**PERF-005 — a medição que a rejeitou, conferida à mão.** `usos_de_coluna`
segue dando 36 pares (tabela, coluna) sem uso nos oito sítios. Cinco foram
escolhidas de propósito e conferidas no `model.bim`, sítio por sítio:

- `DimEmployee[EmployeeKey]` (chave substituta órfã) — só aparece na
  definição da própria coluna e no esquema de Perguntas e Respostas
  (`ConceptualProperty`); nenhum relacionamento, hierarquia, `sortByColumn`,
  `variations` ou referência em DAX.
- `DimCalendar[Trimestre]` (coluna de calendário) — é calculada a partir de
  `DimCalendar[Nº do Trimestre]`, mas nada referencia `Trimestre` de volta; o
  `sortByColumn` que a acompanha aponta para `Nº do Trimestre`, não para ela.
- `DimStore[StoreName]`, `DimCustomer[Education]`, `DimCustomer[Occupation]`
  (atributos reportáveis) — todas só aparecem na própria definição e no
  Power Query de origem; nenhuma nos oito sítios.

Nenhuma das cinco tinha uso que a resolução deixou de ver. Conferidas também
três colunas que a resolução dá como usadas, para o erro oposto — marcar uso
que não existe, que esconderia coluna genuinamente órfã: `DimStore[StoreKey]`
(relacionamento com `FactOnlineSales` e DAX de medida), `DimCalendar[Nº do
Trimestre]` (alvo do `sortByColumn` de `Trimestre` e DAX de coluna calculada)
e `FactOnlineSales[UnitPrice]` (DAX de seis medidas de faturamento) — as três
têm uso real no arquivo. **A medição não está contaminada em nenhuma das duas
direções**, e a rejeição da PERF-005 (08/10/2026, pela cláusula (c) do
terceiro teste do critério de detectabilidade) permanece sustentada pelo que
ela mede.

**O que esta medição não autoriza:** nada sobre a camada de relatório, que a
ferramenta não lê — e é exatamente esse domínio inobservável que rejeitou a
regra. A conferência mostra que a resolução lê corretamente os oito sítios
que ela lê; não abriu um único visual, porque não pode. A estimativa de
~24% de precisão registrada em `core/rules/referencias.py` segue **não
reverificada** por esta tarefa, e só uma comparação contra ground truth na
Fase 5 poderia confirmá-la ou derrubá-la.

Achado lateral: dos oito sítios, dois nunca marcam nada neste corpus —
`hierarquia`, porque as quatro hierarquias do modelo pertencem às tabelas de
data automáticas, fora de escopo; e `dax de role`, porque o P8 não tem role
nenhuma (`modelo.roles == []`). Não é defeito — é característica deste
corpus, e fica registrado para que ninguém leia os 36 como se os oito sítios
tivessem pesado igualmente. É o mesmo risco, em classe, que a entrada de
08/10/2026 sobre a MOD-005 já registrou mais acima neste arquivo: uma
propriedade especificada contra a documentação do TMSL, e exercida só por
teste de unidade, pode não corresponder ao que a ferramenta de origem
realmente escreve ou aciona. Aqui o risco é baixo porque os dois sítios são
aditivos — um esquecido faria a PERF-005 marcar demais, nunca de menos — e a
regra que dependeria deles nem existe mais.

**DAX-002 (iteração desnecessária) — a âncora verificada antes de decidir.**
A sondagem original contou 6 `SUMX`, 4 `RANKX` e 2 `MINX` em escopo; o lexer
confirma as três contagens. As seis ocorrências de `SUMX` foram classificadas
à mão: todas multiplicam `FactOnlineSales[SalesQuantity]` por
`FactOnlineSales[UnitPrice]` linha a linha (uma delas soma um termo antes de
multiplicar) — nenhuma é substituível por `SUM` sobre uma única coluna.
**Seis em seis são iteração legítima; zero são candidatas a DAX-002.** Isso
não sustenta nem rejeita a regra: só diz que o P8 não a exercitaria. DAX-002
continua não implementada, agora por decisão informada por essa
classificação, e não por falta de verificação.

**Validação:** 189 testes passando (os 186 anteriores, mais os três que
travam esta medição: o controle de DAX-001 sem nenhuma barra em escopo, a
classificação das seis `SUMX`, e a conferência à mão das cinco colunas
escolhidas e das três usadas).

**Fechamento da etapa: documentos de projeto atualizados.** `backlog.md`,
`riscos.md`, `status.md` e `README.md` passam a refletir o estado final do
grupo 2, nesta mesma entrada — não numa segunda entrada da mesma data.

- **O que foi entregue:** `backlog.md` ganhou o **D-1** (a contagem de
  20–25 regras deixa de ser meta e passa a ser resultado, com a aritmética
  que leva a ~18 no cenário otimista sem o grupo 3), a âncora da DAX-001
  transcrita com data de acesso, a DAX-002 e a DAX-003 registradas como
  candidatas (a primeira aguardando âncora, com o zero de seis `SUMX` contra
  ela; a segunda adiada por zero ocorrência de `FILTER` no P8), e **F25** em
  Trabalhos Futuros — recusar-se a declarar o grupo de DAX completo enquanto
  houver lacuna aberta (D-7). `riscos.md` ganhou a terceira mitigação do
  R-03 (o lexer, com a cobertura medida abaixo) e o prognóstico da seção 6 da
  spec sobre o R-12. `status.md` foi reescrito com as 9 regras, os 189
  testes, o uso da folga da semana 5, e R-12 como o risco mais urgente do
  projeto — sem nenhuma afirmação de precisão alem das que esta entrada e a
  anterior autorizam (DAX-001: zero confirmado, não "regra precisa"; PERF-005:
  ~24% é a precisão **projetada** que fundamentou a rejeição, não medida de
  uma regra que existe). `README.md` ganhou a contagem de regras, de testes
  e a Fase 3 como em andamento.

- **O terceiro teste, e de onde veio:** formulado nesta mesma etapa (seção 3
  da spec de 08/10/2026), a partir da lição da MOD-005 (06/10) — ela passava
  nas duas condições já em vigor (âncora citável, decidibilidade no TMSL) e
  ainda marcaria a dimensão corretamente configurada. O terceiro teste exige
  suficiência de evidência em três cláusulas — (a) todas as formas da
  condição, (b) todos os sósias do sinal, (c) todos os sítios onde o sinal
  pode morar — e afirmação por ausência exige as três completas. Na MOD-005
  ele **corrigiu** a regra; na PERF-005, registrada mais acima nesta entrada,
  foi o primeiro caso em que **rejeitou** uma regra inteira, antes do código,
  mesmo sendo a de maior rendimento esperado da etapa.

- **O número de cobertura do lexer**, medido contra o P8: **137 de 137**
  expressões DAX (93 medidas, 35 colunas calculadas, 9 partições calculadas)
  tokenizadas com **zero** token `DESCONHECIDO` — o número que substitui
  "usamos expressões regulares" na monografia. A varredura que alimenta as
  regras cobre **105 de 105** expressões em escopo de autor, com **0
  lacunas** — as 32 expressões restantes (137 − 105) pertencem a tabelas
  fora de escopo (automáticas, de cluster, de parâmetro hipotético), não a
  falha do lexer.

- **Pendências que seguem abertas:**
  - A verificação empírica de se o Power BI Desktop grava
    `roles[].tablePermissions[].filterExpression` no `model.bim` (D-9).
    Menos urgente do que quando foi registrada, porque a PERF-005 — a regra
    que dependia dela — foi recusada; mas o sítio já é lido por
    `usos_de_coluna` e pode sustentar regra futura de RLS.
  - A conversão de P1–P7 para PBIP. Deixou de ser recomendação e passou a
    **bloqueio** para a decisão da Fase 3: com a PERF-005 recusada e a
    DAX-001 em zero, o grupo 2 não somou nenhum achado ao P8, e o gatilho de
    ~40 achados em P1–P7 (semana 4) continua sem poder ser medido — ver
    `riscos.md`, R-12.
