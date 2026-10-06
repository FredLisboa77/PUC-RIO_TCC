# Motor de regras determinísticas e o grupo estrutural

- **Data:** 06/10/2026
- **Fase:** 2 — Leitura do PBIP e regras (semana 4)
- **Status:** Aprovado para implementação
- **Funcionalidades:** F06 (modelagem), F07 (performance estática), parte de F15

## 1. Objetivo e contexto

A semana 3 entregou a ingestão do PBIP e o parser do `model.bim` para o modelo interno (`core/model.py`). Esta etapa entrega o **motor de regras** e as **primeiras sete regras estruturais**, de modelagem e performance estática.

A ADR-003 fixa que as regras determinísticas são a **única fonte de achados** — o LLM apenas explica e recomenda, e precisa citar um trecho recuperado. Isso faz do motor de regras a origem de tudo que o pipeline produz: o que a regra não detecta não existe no relatório, e precisão e recall da ferramenta são, por construção, precisão e recall das regras.

O `backlog.md` de 29/09/2026 estabelece o **critério de detectabilidade**: entram primeiro as regras que leem propriedades explícitas do TMSL, onde o falso positivo é raro. É o grupo 1 dessa ordem que esta etapa implementa. DAX por expressão regular e M vêm na etapa seguinte, sobre um motor já provado em uso real.

## 2. Decisões desta etapa

| # | Decisão | Alternativa recusada | Motivo |
|---|---|---|---|
| D-1 | Escopo: motor + grupo estrutural | As 20–25 regras de uma vez | Entregável verificável em uma semana, e as regras de DAX não entram antes de o motor estar provado |
| D-2 | Regras são funções puras registradas por decorador | Subclasses de `Regra`; regras declarativas em YAML | Cada regra estrutural é um laço com uma condição; classe por regra é ritual sem ganho. YAML exigiria construir uma linguagem de expressão — um parser dentro do projeto, sem tipagem nem teste unitário direto, e sem valor para o TCC (o BPA do Tabular Editor já foi recusado em 22/09 por licença, R-10) |
| D-3 | Cada regra declara **URL canónica** do Learn e **termos de consulta** em inglês | Só termos de consulta; ou nada, deixando para a Fase 3 | O spike de 29/09 mostrou que *citação válida ≠ citação pertinente*: o 7B citou `model-date-tables` onde `auto-date-time` é a página que sustenta o achado. Com a URL canónica na regra, a pertinência vira número verificável por código, e não só rubrica humana |
| D-4 | **Um achado por ocorrência** | Um achado agregado por regra | O ground truth da Fase 5 anota objeto por objeto; agregar faria "3 de 4 tabelas" contar igual a "4 de 4", e esconderia falso positivo dentro do agregado |
| D-5 | Severidade é **fixa por regra** e mora no catálogo | Severidade calculada por ocorrência | Nenhuma das regras tem informação que justifique variar a severidade entre ocorrências |
| D-6 | O achado **não** copia os metadados da regra | Achado denormalizado, com título, severidade e URL dentro | Fonte única de verdade: a tabela de regras da monografia sai do catálogo, e nenhum achado pode divergir dele |
| D-7 | **A âncora é verificada antes do código.** Sem passagem citável na documentação oficial, a regra não entra | Implementar e verificar depois | Verificar primeiro custou duas páginas lidas e **eliminou três das oito regras propostas** (seção 9). Verificar depois teria custado o código delas. Sob a ADR-003, regra sem âncora é regra que o pipeline não consegue sustentar |

## 3. O contrato — `core/rules/base.py`

### `RegraMeta`

O catálogo. Um registro por regra:

| Campo | Conteúdo |
|---|---|
| `id` | `MOD-001`, `PERF-001` — prefixo por categoria |
| `titulo` | Frase curta, em português, como aparece no relatório |
| `categoria` | `modelagem` \| `performance` \| `dax` \| `m` |
| `severidade` | `alta` \| `media` \| `baixa` |
| `url_canonica` | A página do Microsoft Learn que sustenta o achado |
| `termos_consulta` | Termos de busca **em inglês**, para a recuperação com `bge-small-en` (ADR-002, C-6) |
| `recomendacao_padrao` | O texto que sai no relatório quando a geração do LLM é descartada por citação inválida (exigência da ADR-003). **Precisa conter as exceções que a própria fonte declara** — ver seção 4 |

### `Evidencia`

Onde está o problema, e o que a regra leu para afirmar isso:

| Campo | Conteúdo |
|---|---|
| `tipo_objeto` | `tabela` \| `coluna` \| `medida` \| `relacionamento` \| `particao` \| `modelo` |
| `objeto` | Nome qualificado: `DimProduct[ProductKey]` |
| `tabela` | Tabela do objeto, quando se aplica |
| `trecho` | O DAX, o M ou a propriedade TMSL lida |
| `detalhe` | Os valores que a regra de fato leu: `{"crossFilteringBehavior": "bothDirections"}` |

A `Evidencia` é o que vai ao prompt como evidência e ao relatório como prova. O mascaramento de strings de conexão e caminhos locais (seção 5 do plano da Fase 1) se aplica a `trecho` antes de qualquer saída — relevante para as regras de M, da etapa seguinte; nenhuma das regras estruturais lê expressão M.

### `Achado`

`id_regra`, `evidencia` e `mensagem` — a frase da ocorrência específica, escrita pela regra. Nada mais (D-6). Os metadados são resolvidos pelo `id_regra` contra o registro.

## 4. As sete regras, com âncora verificada

Contagens medidas no P8 (`data/pbip/P8_contoso-vendas`) em 06/10/2026. Todas as âncoras foram lidas no Learn nesta data; a passagem citável está transcrita abaixo da tabela.

| ID | Regra | Detecção no TMSL | P8 | Sev. |
|---|---|---|---|---|
| MOD-001 | Tempo automático de data ligado | annotations `__PBI_TemplateDateTable` / `__PBI_LocalDateTable` | 4 | alta |
| MOD-002 | Relacionamento bidirecional | `crossFilteringBehavior: bothDirections` | 4 | alta |
| MOD-003 | Tabela sem relacionamento | tabela ausente de `relationships` | 2 | baixa |
| MOD-005 | Dimensão de data não marcada como tabela de data | é o lado "um" de relacionamento `dateTime → dateTime` e não tem `dataCategory: "Time"` | 1 | media |
| MOD-006 | Dimensão em floco de neve | tabela no lado "um" de um relacionamento e no lado "muitos" de outro | 2 | baixa |
| PERF-001 | Coluna calculada em DAX | `type: calculated` na coluna | 1 | media |
| PERF-003 | Coluna de ponto flutuante somada | `dataType: double` com `summarizeBy: sum` | 1 | baixa |

Total: **15 achados em P8**, de 19 tabelas das quais 11 ficam em escopo.

### Âncoras

**MOD-001** — `guidance/auto-date-time` e `guidance/import-modeling-data-reduction`: *"If the Auto date/time option isn't relevant to your projects, disable the global Auto date/time option"*; *"The hidden tables are in fact calculated tables that increase the size of the model."*

**MOD-002** — `guidance/relationships-bidirectional-filtering`: *"Generally, we recommend that you minimize the use of bi-directional relationships. That's because they can negatively impact on model query performance, and possibly deliver confusing experiences for your report users."* A recomendação padrão precisa citar os três cenários que a página admite (um-para-um, ponte muitos-para-muitos, análise dimensão-a-dimensão) e a alternativa que ela prefere nos dois últimos: `CROSSFILTER` na definição da medida, em vez da propriedade do relacionamento.

**MOD-003** — `guidance/star-schema`: *"We also recommend that you strive to deliver the right number of tables with the right relationships in place."* **É a âncora mais fraca do conjunto**: recomendação geral, não artigo dedicado. Daí a severidade baixa. Se a Fase 3 mostrar que o trecho recuperado não sustenta a explicação, a regra é candidata a sair.

**MOD-005** — `transform-model/desktop-date-tables`: *"If you prefer to continue to use the Classic time intelligence functions in Power BI then you must mark your date table as a date table"*; *"when you mark a table as a date table, Power BI Desktop removes the built-in (automatically created) date table."* A recomendação padrão precisa registrar a ressalva da própria página: com a *Calendar-based time intelligence* (preview) a marcação pode não ser necessária. Em P8 a ressalva não se aplica — `DATEADD` aparece em 5 medidas, isto é, inteligência temporal clássica está em uso.

**MOD-006** — `guidance/star-schema`: *"Generally, the benefits of a single model table outweigh the benefits of multiple model tables."* A página lista os quatro custos do floco de neve e admite que pode ser escolha deliberada (*"perhaps because your source data does"*) — a recomendação padrão precisa dizer isso.

**PERF-001** — `guidance/import-modeling-data-reduction`, seção *Preference for custom columns*: *"It's therefore less efficient to add table columns as calculated columns than Power Query computed columns (defined in M). Whenever possible, preference creating custom columns in Power Query."* A mesma seção declara as exceções — fórmula que avalia medidas, ou que exige funcionalidade só existente em DAX — e elas precisam entrar na recomendação padrão, senão o relatório afirma mais do que a fonte.

**PERF-003** — `connect-data/desktop-data-types`, seção *Accuracy of number type calculations*: *"Rarely, calculations that sum the values of a column of Decimal number data type can return unexpected results. This result is most likely with columns that have large amounts of both positive numbers and negative numbers […] To avoid unexpected results, you can change the column data type from Decimal number to Fixed decimal number or Whole number."* O "rarely" e a condição de sinais mistos justificam a severidade baixa e precisam aparecer na recomendação.

### Pendência empírica de MOD-005

A detecção assume que a marcação de tabela de data aparece no TMSL como `dataCategory: "Time"` na tabela, o que é consistente com a propriedade `Table.DataCategory` do TOM e com o P8 (nenhuma tabela marcada, nenhuma com `dataCategory`). **Isso ainda não foi confirmado em documento nem em arquivo.** Confirmação barata: marcar a `DimCalendar` como tabela de data no Desktop, salvar como PBIP e comparar o `model.bim`. De bônus, mostra o Power BI apagando as tabelas de data automáticas — figura para o estudo de caso. Se o sinal for outro, só muda o predicado de MOD-005.

### O que o P8 ganhou com este conjunto

As regras encadeiam uma causa, e não só listam sintomas: a `DimCalendar` nunca foi marcada como tabela de data (MOD-005), então o Power BI gerou uma tabela de data local para a própria `DimCalendar[Data]` — uma das quatro de MOD-001. E dois dos quatro relacionamentos bidirecionais de MOD-002 são exatamente os elos da cadeia floco de neve de MOD-006 (`FactOnlineSales → DimProduct → DimProductSubcategory → DimProductCategory`). O estudo de caso passa a ter uma narrativa, não um inventário.

## 5. Exclusões — `core/rules/escopo.py`

Sem exclusões, as regras marcariam padrões legítimos e afogariam o relatório em objetos que o próprio Power BI gerou. Vale um princípio único: **auditar o que o autor escreveu.** O P8 exibe todos os casos, e cada exclusão tem um predicado explícito em TMSL — nenhuma é por nome de objeto.

**Exclusões de tabela** — compõem `tabelas_em_escopo(modelo)`:

| Exclusão | Predicado | Por quê | Efeito no P8 |
|---|---|---|---|
| Tabelas automáticas de data | annotation `__PBI_TemplateDateTable` ou `__PBI_LocalDateTable` | São o achado da MOD-001, não insumo das outras. Suas colunas calculadas são geradas pelo produto | PERF-001 cai de 35 para 11 |
| Tabelas apenas de medidas | ao menos uma medida e nenhuma coluna de dados (todas `calculatedTableColumn`) | `_Medidas` tem 92 medidas, zero relacionamento e é tabela calculada, com partição `Row("Coluna", BLANK())` — padrão consagrado, não defeito | Remove 1 falso positivo de MOD-003 |
| Tabelas de parâmetro hipotético | partição calculada cuja expressão começa em `GENERATESERIES` | Assinatura canónica do parâmetro hipotético (`Parâmetro` = `GENERATESERIES(0, 1, 0.05)`): não tem relacionamento por natureza | Remove 1 falso positivo de MOD-003 |
| Tabelas de análise geradas | annotation `ClusterMappingTable` | Geradas pelos recursos de agrupamento e clustering; o autor não as escreveu | Remove 2 falsos positivos de MOD-003 |

**Exclusões de coluna:**

| Exclusão | Predicado | Por quê | Efeito no P8 |
|---|---|---|---|
| Colunas de agrupamento e cluster | annotation `GroupingDesignState` na coluna | O DAX dessas colunas é escrito pela interface de grupos e clusters, não pelo autor: `DimCalendar[Data (clusters)]`, `DimCustomer[Faixa de Renda]`, `DimPromotion[Grupos]` | PERF-001 cai de 11 para 7 |

**Exclusão específica de PERF-001 — a dimensão de data:**

A página `guidance/auto-date-time` não só admite a tabela de data em DAX, ela a recomenda, e recomenda também o que PERF-001 marcaria: *"you can generate date tables in your model by using the DAX CALENDAR or CALENDARAUTO functions. You can then **add calculated columns** to support the known time filtering and grouping requirements."*

Seis dos sete achados de PERF-001 em P8 eram exatamente isso — `Ano`, `Nº do Mês`, `Mês`, `Nº do Trimestre`, `Trimestre`, `Semestre` na `DimCalendar`. Então **a dimensão de data sai do escopo de PERF-001**, identificada pela mesma rotina `dimensao_de_data(modelo)` que MOD-005 usa para encontrá-la. PERF-001 cai de 7 para 1 (`DimEmployee[Salário]`).

Note a assimetria deliberada: `dimensao_de_data()` é **alvo** de MOD-005 e **exclusão** de PERF-001. É a mesma identificação estrutural servindo a dois propósitos opostos, e por isso vive no módulo de escopo, não dentro de uma regra.

A exclusão de parâmetro hipotético existe por si, e não pelo acaso de a tabela `Parâmetro` também ter uma medida: um parâmetro sem medida nenhuma continua fora do escopo, e o teste usa esse caso.

Nenhuma regra reimplementa esse julgamento. Como o parser guarda o TMSL de origem em `bruto`, as annotations estão acessíveis sem reabrir o arquivo — o campo existe para isso.

**Riscos residuais, declarados.** Vão para o ground truth da Fase 5 e para o capítulo de limitações (seção 11 do plano da Fase 1):

- **MOD-003 marca `Tabela de Regressão Linear`**, tabela de Power Query sem relacionamento. É achado real, não falso positivo, mas depende de intenção que o `model.bim` não registra. Somado à âncora fraca, é a regra mais frágil do conjunto.
- As exclusões por annotation são **específicas do que o Power BI gera hoje**. Uma versão futura que mude o nome de uma annotation reabre o falso positivo em silêncio. Os testes de P8 travam as contagens e é por lá que a quebra apareceria.

## 6. O motor

### `core/rules/registry.py`

O decorador `@regra(...)` e o registro. ID duplicado é erro **na importação**, não em tempo de execução.

### `core/rules/runner.py`

`avaliar(modelo: ModeloSemantico) -> ResultadoRegras`.

- Itera o registro em ordem de ID e concatena os achados.
- **Ordenação determinística** da saída: severidade (alta → baixa), depois ID da regra, depois nome do objeto. A avaliação da Fase 5 compara listas; ordem instável viraria diferença falsa entre execuções.
- **Isolamento de erro:** uma regra que levanta exceção não derruba a auditoria. O runner captura, registra e segue.
- Por isso o retorno é um `ResultadoRegras` com `achados` e `regras_com_falha`, e não uma lista nua: a interface precisa poder dizer "6 de 7 regras executadas" em vez de entregar menos achados em silêncio.
- Em teste, qualquer regra em `regras_com_falha` é falha do teste. O isolamento protege o usuário final, não a suíte.

### `core/rules/catalogo.py`

`python -m core.rules.catalogo` imprime o catálogo em Markdown — ID, título, categoria, severidade, URL. A tabela de regras do capítulo de metodologia passa a ser gerada, não mantida à mão. O mesmo catálogo alimenta o `rag/sources.yaml` da semana 5 (G-8): as URLs canónicas das regras são, por construção, as páginas que a base RAG precisa conter.

Um teste trava a condição que torna isso confiável: toda regra registrada tem `url_canonica` não vazia, `termos_consulta` não vazios e `recomendacao_padrao` com texto real. **Regra sem âncora não entra no registro** (D-7).

## 7. Testes

TDD, como na semana 3: teste primeiro, visto falhar, depois a implementação mínima. Três camadas.

1. **Uma fixture sintética por regra** — mínima, com o caso positivo e o negativo. É aqui que cada exclusão da seção 5 é provada: um `model.bim` com uma tabela só de medidas produz zero achado de MOD-003, e uma dimensão de data com colunas calculadas produz zero achado de PERF-001.
2. **Testes do motor, independentes das regras** — ID duplicado rejeitado; regra que explode é isolada e aparece em `regras_com_falha`; ordenação estável; catálogo completo.
3. **Regressão contra o P8**, pulada quando `data/` não existe, como os quatro testes atuais. Trava as sete contagens da seção 4. Se uma mudança futura fizer PERF-001 saltar de 1 para 35, o teste acusa que as exclusões quebraram.

## 8. Arquivos

**Novos:** `core/rules/base.py`, `core/rules/registry.py`, `core/rules/escopo.py`, `core/rules/modelagem.py`, `core/rules/performance.py`, `core/rules/runner.py`, `core/rules/catalogo.py`, `tests/test_rules_motor.py`, `tests/test_rules_escopo.py`, `tests/test_rules_modelagem.py`, `tests/test_rules_performance.py`.

**Tocados:** `tests/conftest.py` — `escrever_pbip` passa a aceitar relacionamentos e annotations nas fixtures; `tests/test_pbip_real.py` — as contagens do P8.

`core/model.py` ganha apenas o que faltar: `Tabela.data_category` (MOD-005 precisa dele) e as annotations acessíveis por `bruto`, que já estão. `Tabela.hierarquias` não é necessária e não entra.

## 9. Fora de escopo

### Regras descartadas na verificação de âncoras (D-7)

Três das oito regras propostas no design original caíram ao conferir a documentação. O registro fica aqui porque o motivo de cada uma é resultado do trabalho, não desperdício dele:

| Regra | Por que caiu | Destino |
|---|---|---|
| **PERF-004** — tabela calculada em DAX | A página que a sustentaria **recomenda** o que a regra marcaria: *"you can generate date tables in your model by using the DAX CALENDAR or CALENDARAUTO functions"*. Em P8, seu único achado era a `DimCalendar` — 100% do que a regra produzia seria refutado pela fonte citada | Descartada. Sob a ADR-003, o trecho recuperado contradiria o achado |
| **PERF-002** — coluna-chave agregável | Nenhuma passagem do Learn sustenta "coluna-chave não deve ser agregável" de forma geral. A única frase próxima (*"we recommend that you set the column default summarization property to `Do Not Summarize`"*) é contextual ao exemplo de número de pedido convertido de texto. A regra vinha do BPA do Tabular Editor, recusado em 22/09 por licença (R-10). A variante estrutural — coluna em relacionamento com `summarizeBy ≠ none` — dá **zero** em P8 | Descartada como afirmação. Os 5 objetos que apontava (chaves substitutas órfãs) voltam no backlog como candidata **"coluna sem uso"**, com âncora verbatim em *Remove unnecessary columns* |
| **MOD-004** — relacionamento entre tipos diferentes | Sem âncora: nem `desktop-create-and-manage-relationships` nem `desktop-data-types` declaram exigência de tipos iguais. E a producibilidade é duvidosa — o editor de relacionamentos do Desktop valida os tipos, então a condição talvez não exista em modelo real, e o caso positivo só viveria num `model.bim` forjado à mão | Descartada. Fica no backlog com a pergunta a resolver: o produto permite criar esse relacionamento? |

### Fora de escopo por decisão

- Regras de DAX e de M — etapa seguinte, grupos 2 a 4 do critério de detectabilidade.
- `core/pipeline.py` e `run_audit()` — a orquestração vem com a Fase 3, quando houver RAG para orquestrar. Nesta etapa o motor é chamado pelos testes.
- Severidade calculada por ocorrência (D-5).
- Configuração para ligar e desligar regras: ninguém pediu.
- Teto de achados por regra: considerado e recusado na decisão de granularidade (D-4), porque truncaria o ground truth justamente nos modelos extremos.

### Consequência para o R-12

O conjunto saiu de 8 regras e 24 achados em P8 para **7 regras e 15 achados** — ganho de precisão, perda de volume. O R-12 (poucos achados em P1–P7) piora com isso. A pendência de baixar os 7 PBIX já é da semana 4; assim que existirem, rodar as sete regras sobre eles transforma o R-12 de palpite em número e decide se o P9 deixa de ser opcional.

## 10. Critérios de aceite

1. `pytest` verde, com os 15 testes atuais intactos.
2. As sete regras registradas, cada uma com a URL canónica da seção 4, termos de consulta em inglês e recomendação padrão **contendo as exceções que a fonte declara**.
3. `avaliar()` sobre o P8 produz exatamente as 15 ocorrências da seção 4, com `regras_com_falha` vazio.
4. `python -m core.rules.catalogo` imprime as sete regras.
5. Cada exclusão da seção 5 provada por fixture sintética.
6. A pendência empírica de MOD-005 (`dataCategory: "Time"`) resolvida, ou a regra marcada como provisória no catálogo.
7. `progress-log.md`, `backlog.md` e `README.md` atualizados; a ADR-003 citada onde a recomendação padrão é exigida.
