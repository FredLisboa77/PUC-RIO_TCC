# Motor de regras determinísticas e o grupo estrutural

- **Data:** 06/10/2026
- **Fase:** 2 — Leitura do PBIP e regras (semana 4)
- **Status:** Aprovado para implementação
- **Funcionalidades:** F06 (modelagem), F07 (performance estática), parte de F15

## 1. Objetivo e contexto

A semana 3 entregou a ingestão do PBIP e o parser do `model.bim` para o modelo interno (`core/model.py`). Esta etapa entrega o **motor de regras** e as **primeiras oito regras estruturais**, de modelagem e performance estática.

A ADR-003 fixa que as regras determinísticas são a **única fonte de achados** — o LLM apenas explica e recomenda, e precisa citar um trecho recuperado. Isso faz do motor de regras a origem de tudo que o pipeline produz: o que a regra não detecta não existe no relatório, e precisão e recall da ferramenta são, por construção, precisão e recall das regras.

O `backlog.md` de 29/09/2026 estabelece o **critério de detectabilidade**: entram primeiro as regras que leem propriedades explícitas do TMSL, onde o falso positivo é raro. É o grupo 1 dessa ordem que esta etapa implementa. DAX por expressão regular e M vêm na etapa seguinte, sobre um motor já provado em uso real.

## 2. Decisões desta etapa

| # | Decisão | Alternativa recusada | Motivo |
|---|---|---|---|
| D-1 | Escopo: motor + grupo estrutural | As 20–25 regras de uma vez | Entregável verificável em uma semana, e as regras de DAX não entram antes de o motor estar provado |
| D-2 | Regras são funções puras registradas por decorador | Subclasses de `Regra`; regras declarativas em YAML | Cada regra estrutural é um laço com uma condição; classe por regra é ritual sem ganho. YAML exigiria construir uma linguagem de expressão — um parser dentro do projeto, sem tipagem nem teste unitário direto, e sem valor para o TCC (o BPA do Tabular Editor já foi recusado em 22/09 por licença, R-10) |
| D-3 | Cada regra declara **URL canónica** do Learn e **termos de consulta** em inglês | Só termos de consulta; ou nada, deixando para a Fase 3 | O spike de 29/09 mostrou que *citação válida ≠ citação pertinente*: o 7B citou `model-date-tables` onde `auto-date-time` é a página que sustenta o achado. Com a URL canónica na regra, a pertinência vira número verificável por código, e não só rubrica humana |
| D-4 | **Um achado por ocorrência** | Um achado agregado por regra | O ground truth da Fase 5 anota objeto por objeto; agregar faria "3 de 4 tabelas" contar igual a "4 de 4", e esconderia falso positivo dentro do agregado |
| D-5 | Severidade é **fixa por regra** e mora no catálogo | Severidade calculada por ocorrência | Nenhuma das oito regras tem informação que justifique variar a severidade entre ocorrências |
| D-6 | O achado **não** copia os metadados da regra | Achado denormalizado, com título, severidade e URL dentro | Fonte única de verdade: a tabela de regras da monografia sai do catálogo, e nenhum achado pode divergir dele |

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
| `recomendacao_padrao` | O texto que sai no relatório quando a geração do LLM é descartada por citação inválida (exigência da ADR-003) |

### `Evidencia`

Onde está o problema, e o que a regra leu para afirmar isso:

| Campo | Conteúdo |
|---|---|
| `tipo_objeto` | `tabela` \| `coluna` \| `medida` \| `relacionamento` \| `particao` \| `modelo` |
| `objeto` | Nome qualificado: `DimProduct[ProductKey]` |
| `tabela` | Tabela do objeto, quando se aplica |
| `trecho` | O DAX, o M ou a propriedade TMSL lida |
| `detalhe` | Os valores que a regra de fato leu: `{"crossFilteringBehavior": "bothDirections"}` |

A `Evidencia` é o que vai ao prompt como evidência e ao relatório como prova. O mascaramento de strings de conexão e caminhos locais (seção 5 do plano da Fase 1) se aplica a `trecho` antes de qualquer saída — relevante para as regras de M, da etapa seguinte; nenhuma das oito regras estruturais lê expressão M.

### `Achado`

`id_regra`, `evidencia` e `mensagem` — a frase da ocorrência específica, escrita pela regra. Nada mais (D-6). Os metadados são resolvidos pelo `id_regra` contra o registro.

## 4. As oito regras

Contagens medidas no P8 (`data/pbip/P8_contoso-vendas`) em 06/10/2026, com as tabelas automáticas de data já fora do escopo das demais regras.

| ID | Regra | Detecção no TMSL | P8 | Sev. |
|---|---|---|---|---|
| MOD-001 | Tempo automático de data ligado | annotations `__PBI_TemplateDateTable` / `__PBI_LocalDateTable` | 4 | alta |
| MOD-002 | Relacionamento bidirecional | `crossFilteringBehavior: bothDirections` | 4 | alta |
| MOD-003 | Tabela sem relacionamento | tabela ausente de `relationships` | 2 | baixa |
| MOD-004 | Relacionamento entre colunas de tipos diferentes | `dataType` das duas pontas do relacionamento | 0 | alta |
| PERF-001 | Coluna calculada em DAX | `type: calculated` na coluna | 7 | media |
| PERF-002 | Coluna-chave agregável | nome termina em `Key`/`ID` e `summarizeBy ≠ none` | 5 | media |
| PERF-003 | Coluna de ponto flutuante somada | `dataType: double` com `summarizeBy: sum` | 1 | baixa |
| PERF-004 | Tabela calculada em DAX | `partitions[].source.type: calculated` | 1 | baixa |

Total: **24 achados em P8**, de 19 tabelas das quais 11 ficam em escopo.

**MOD-001 é a única regra que olha fora do escopo.** As tabelas automáticas de data são o achado dela, e insumo de nenhuma outra (seção 5). As demais sete regras operam sobre `tabelas_em_escopo(modelo)`, e MOD-002 e MOD-004 ignoram relacionamentos com qualquer ponta fora do escopo.

**MOD-004 detecta zero em P8, e isso é intencional.** É determinística e sem falso positivo possível; incluí-la demonstra que o motor não produz achado onde não há problema. O caso positivo vem de fixture sintética.

As oito somam-se à meta de 20–25 regras do MVP; as restantes são de DAX e M.

## 5. Exclusões — `core/rules/escopo.py`

Sem exclusões, as regras marcariam padrões legítimos e afogariam o relatório em objetos que o próprio Power BI gerou. Vale um princípio único: **auditar o que o autor escreveu.** O P8 exibe todos os casos, e cada exclusão tem um predicado explícito em TMSL — nenhuma é por nome de objeto.

**Exclusões de tabela** — compõem `tabelas_em_escopo(modelo)`:

| Exclusão | Predicado | Por quê | Efeito no P8 |
|---|---|---|---|
| Tabelas automáticas de data | annotation `__PBI_TemplateDateTable` ou `__PBI_LocalDateTable` | São o achado da MOD-001, não insumo das outras. Suas colunas calculadas são geradas pelo produto | PERF-001 cai de 35 para 11 |
| Tabelas apenas de medidas | ao menos uma medida e nenhuma coluna de dados (todas `calculatedTableColumn`) | `_Medidas` tem 92 medidas, zero relacionamento e é tabela calculada, com partição `Row("Coluna", BLANK())` — padrão consagrado, não defeito | Remove 1 falso positivo de MOD-003 e 1 de PERF-004 |
| Tabelas de parâmetro hipotético | partição calculada cuja expressão começa em `GENERATESERIES` | Assinatura canónica do parâmetro hipotético (`Parâmetro` = `GENERATESERIES(0, 1, 0.05)`): não tem relacionamento por natureza | Remove 1 falso positivo de MOD-003 e 1 de PERF-004 |
| Tabelas de análise geradas | annotation `ClusterMappingTable` | Geradas pelos recursos de agrupamento e clustering; o autor não as escreveu | Remove 2 falsos positivos de MOD-003 e 2 de PERF-002 |

**Exclusão de coluna** — `coluna_gerada_por_analise()`:

| Exclusão | Predicado | Por quê | Efeito no P8 |
|---|---|---|---|
| Colunas de agrupamento e cluster | annotation `GroupingDesignState` na coluna | O DAX dessas colunas é escrito pela interface de grupos e clusters, não pelo autor: `DimCalendar[Data (clusters)]`, `DimCustomer[Faixa de Renda]`, `DimPromotion[Grupos]` | PERF-001 cai de 11 para 7 |

A exclusão de parâmetro hipotético existe por si, e não pelo acaso de a tabela `Parâmetro` também ter uma medida: um parâmetro sem medida nenhuma continua fora do escopo, e o teste usa esse caso.

As exclusões ficam num módulo próprio, com teste próprio. Nenhuma regra reimplementa esse julgamento. Como o parser guarda o TMSL de origem em `bruto`, as annotations estão acessíveis sem reabrir o arquivo — o campo existe para isso.

**Riscos residuais, declarados.** Vão para o ground truth da Fase 5 e para o capítulo de limitações (seção 11 do plano da Fase 1):

- **PERF-004 marca `DimCalendar`**, tabela de data construída em DAX. É achado defensável — o Learn recomenda a tabela de data vinda da origem ou do Power Query —, mas há prática estabelecida que considera `CALENDAR`/`CALENDARAUTO` aceitável. Severidade baixa por isso.
- **MOD-003 marca `Tabela de Regressão Linear`**, tabela de Power Query sem relacionamento. É achado real, não falso positivo, mas depende de intenção que o `model.bim` não registra.
- As exclusões por annotation são **específicas do que o Power BI gera hoje**. Uma versão futura que mude o nome de uma annotation reabre o falso positivo em silêncio. Os testes de P8 travam as contagens e é por lá que a quebra apareceria.

## 6. O motor

### `core/rules/registry.py`

O decorador `@regra(...)` e o registro. ID duplicado é erro **na importação**, não em tempo de execução.

### `core/rules/runner.py`

`avaliar(modelo: ModeloSemantico) -> ResultadoRegras`.

- Itera o registro em ordem de ID e concatena os achados.
- **Ordenação determinística** da saída: severidade (alta → baixa), depois ID da regra, depois nome do objeto. A avaliação da Fase 5 compara listas; ordem instável viraria diferença falsa entre execuções.
- **Isolamento de erro:** uma regra que levanta exceção não derruba a auditoria. O runner captura, registra e segue.
- Por isso o retorno é um `ResultadoRegras` com `achados` e `regras_com_falha`, e não uma lista nua: a interface precisa poder dizer "19 de 20 regras executadas" em vez de entregar menos achados em silêncio.
- Em teste, qualquer regra em `regras_com_falha` é falha do teste. O isolamento protege o usuário final, não a suíte.

### `core/rules/catalogo.py`

`python -m core.rules.catalogo` imprime o catálogo em Markdown — ID, título, categoria, severidade, URL. A tabela de regras do capítulo de metodologia passa a ser gerada, não mantida à mão.

Um teste trava a condição que torna isso confiável: toda regra registrada tem `url_canonica` não vazia, `termos_consulta` não vazios e `recomendacao_padrao` com texto real. **Regra sem âncora não entra no registro.**

## 7. Testes

TDD, como na semana 3: teste primeiro, visto falhar, depois a implementação mínima. Três camadas.

1. **Uma fixture sintética por regra** — mínima, com o caso positivo e o negativo. É aqui que MOD-004 ganha seu caso positivo, e que cada exclusão da seção 5 é provada: um `model.bim` com uma tabela só de medidas produz zero achado de MOD-003.
2. **Testes do motor, independentes das regras** — ID duplicado rejeitado; regra que explode é isolada e aparece em `regras_com_falha`; ordenação estável; catálogo completo.
3. **Regressão contra o P8**, pulada quando `data/` não existe, como os quatro testes atuais. Trava as oito contagens da seção 4. Se uma mudança futura fizer PERF-001 saltar de 7 para 35, o teste acusa que as exclusões quebraram.

## 8. Arquivos

**Novos:** `core/rules/base.py`, `core/rules/registry.py`, `core/rules/escopo.py`, `core/rules/modelagem.py`, `core/rules/performance.py`, `core/rules/runner.py`, `core/rules/catalogo.py`, `tests/test_rules_motor.py`, `tests/test_rules_escopo.py`, `tests/test_rules_modelagem.py`, `tests/test_rules_performance.py`.

**Tocados:** `tests/conftest.py` — `escrever_pbip` passa a aceitar relacionamentos e annotations nas fixtures; `tests/test_pbip_real.py` — as contagens do P8.

`core/model.py` ganha apenas o que faltar. `Tabela.hierarquias` não é necessária para estas oito regras e não entra.

## 9. Fora de escopo

- Regras de DAX e de M — etapa seguinte, grupos 2 a 4 do critério de detectabilidade.
- `core/pipeline.py` e `run_audit()` — a orquestração vem com a Fase 3, quando houver RAG para orquestrar. Nesta etapa o motor é chamado pelos testes.
- Severidade calculada por ocorrência (D-5).
- Configuração para ligar e desligar regras: ninguém pediu.
- Teto de achados por regra: considerado e recusado na decisão de granularidade (D-4), porque truncaria o ground truth justamente nos modelos extremos.

## 10. Critérios de aceite

1. `pytest` verde, com os 15 testes atuais intactos.
2. As oito regras registradas, cada uma com URL canónica do Learn verificada, termos de consulta em inglês e recomendação padrão.
3. `avaliar()` sobre o P8 produz exatamente as 24 ocorrências da seção 4, com `regras_com_falha` vazio.
4. `python -m core.rules.catalogo` imprime as oito regras.
5. Cada exclusão da seção 5 provada por fixture sintética.
6. `progress-log.md` e `README.md` atualizados; a ADR-003 citada onde a recomendação padrão é exigida.
