# Correção da MOD-003 e da PERF-001 a partir do gabarito

- **Data:** 12/10/2026
- **Fase:** 3, semana 8 — etapa seguinte ao gabarito das regras (PR #6)
- **Status:** Aguardando revisão do Fred
- **Depende de:** o gabarito (`gabarito/`, `eval/ground_truth.csv`) e a tag `regras-gt`
- **Branch:** `fase3-correcao-regras`, criada a partir de `fase3-gabarito-regras`

## 1. Objetivo e enquadramento

O gabarito mediu as 9 regras em P1–P7 com as regras congeladas na tag `regras-gt`
(`eval/results/regras-2026-10-12.json`, o **resultado oficial**). Duas regras saíram com
defeito que tem sinal estrutural no `model.bim` e apoio na documentação:

- **MOD-003** marca 6 tabelas que o Fred julgou isoladas de propósito (precisão 0,14);
- **PERF-001** deixa de marcar 6 colunas calculadas de tabelas de data importadas pelo
  Power Query (recall 0,75).

Esta etapa corrige as duas. Como as correções foram **motivadas pelo conjunto de teste**,
a medição depois delas **não substitui** o resultado oficial: entra na monografia como
**análise de erros**, com ameaça à validade declarada (protocolo do R-04,
`eval/dataset.md`). A validação honesta fica para um projeto que as regras não viram (P9 ou
Fase 5).

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Corrigir as regras | Sim, MOD-003 e PERF-001 |
| DAX-001 | **Não muda**: a página da âncora usa o padrão `IF(d <> 0, n / d, BLANK())` como exemplo a trocar por DIVIDE; os 3 vereditos foram revistos para `viola` (já no PR #6) |
| `Logo` e `Indicators` (MOD-003) | **Limitação declarada** (opção A): sem sinal estrutural seguro; uma heurística acertaria 2 casos ajustando a regra ao gabarito |
| Como reportar | Opção A: resultado oficial na tag `regras-gt`; medição pós-correção como análise de erros |

## 2. MOD-003 — dois objetos isolados por natureza

Hoje `fora_de_escopo` (`core/rules/escopo.py`) já exclui a tabela de data automática, a
tabela só de medidas, a de parâmetro hipotético e a gerada por análise. Entram dois
predicados novos, ambos estruturais (nunca por nome):

| Predicado | Sinal no `model.bim` | Casos em P1–P8 |
|---|---|---|
| `grupo_de_calculo(t)` | a tabela tem a propriedade `calculationGroup` | P1: `Date Role`, `Time Intelligence` |
| `tabela_de_parametro_de_campo(t)` | alguma coluna tem `extendedProperties` com `name: "ParameterMetadata"` e `value.kind == 2` | P2: `Toggle for breakdown`, `Toggle for variance to plan` |

O `kind == 2` é o que separa o parâmetro de campo do parâmetro hipotético: o `Parâmetro`
do P8 também tem `ParameterMetadata`, mas sem `kind`, e já é excluído por `GENERATESERIES`.

**Os dois entram em `fora_de_escopo`**, e portanto valem para todas as regras de nível de
tabela, não só para a MOD-003 — pela mesma razão que a tabela de medidas: não têm
relacionamento por natureza nem papel no star schema.

**Escopo das regras de DAX (`dax_escrito_pela_ferramenta`):** só o **parâmetro de campo**
entra — as tuplas `NAMEOF` da tabela são escritas pelo Power BI Desktop. O **grupo de
cálculo** fica de fora: o DAX dos itens de cálculo é do autor, e excluí-lo cegaria regras
de DAX futuras. (A varredura atual não lê `calculationItems`; isso não muda aqui.)

**Limitação declarada:** `Logo` (P6) e `Indicators` (P4) — tabelas digitadas à mão
("Inserir dados") para a apresentação — continuam como falsos positivos. Registro na
`nota_de_verificacao` da MOD-003, no progress-log e na linha do R-03 em `riscos.md`.

## 3. PERF-001 — exclusão só da tabela de data calculada em DAX

Hoje a regra pula **toda** dimensão de data (`dimensao_de_data`). As duas páginas que
sustentam a exceção dizem o mesmo, e a exceção vale só para tabela gerada em DAX:

- *auto-date-time*: "When your data source already defines a date dimension table, use
  this table […]. Otherwise, you can generate date tables in your model by using the DAX
  CALENDAR or CALENDARAUTO functions. You can then add calculated columns […]."
- *model-date-tables*: "You can generate a date table in your model by creating a
  calculated table using either the CALENDAR or CALENDARAUTO DAX function. […] You can
  then extend the calculated table with calculated columns […]."

**Nova exclusão:** a coluna é pulada só se a tabela é dimensão de data **e** tem partição
com `tipo_origem == "calculated"` (tabela calculada em DAX, com CALENDAR, CALENDARAUTO ou
envolvida em ADDCOLUMNS). Dimensão de data importada pelo Power Query volta a ser auditada.
Docstring e `recomendacao_padrao` da regra são atualizadas com a citação.

**Efeito esperado em P1–P8** (levantado por script de leitura): +12 achados — P1 3, P2 1,
P3 1, P4 7; P5–P8 sem mudança (a `Date` de P5 é calculada e não tem coluna calculada).

## 4. O que muda em outros pontos do código

- **`tests/test_rules_performance.py`:** `test_perf001_ignora_coluna_da_dimensao_de_data`
  monta uma dimensão **sem partição calculada** (como a importada) e passa a esperar o
  achado; o teste com
  `CALENDAR` continua esperando a exclusão.
- **P8 (`tests/test_pbip_real.py`):** sem mudança esperada — nenhuma coluna nova na
  PERF-001 e nenhum grupo de cálculo ou parâmetro de campo novo fora de escopo. O teste
  confirma.
- **Conjunto da recuperação (`eval/recuperacao/consultas.yaml`):** é gerado a partir dos
  achados de P1–P7 e `test_rag_avaliacao_real.py` exige que esteja em dia. Será **regerado**
  (`python -m rag.avaliacao gerar`): saem as 4 consultas da MOD-003 corrigidas, entram as 12
  da PERF-001. A medição da recuperação de 11/10/2026 fica como está — foi feita sobre o
  conjunto da tag `regras-gt`; remedir a recuperação é tarefa do subprojeto 2 (busca
  combinada), que já vai medir de novo.

## 5. Medição pós-correção

`python -m gabarito medir` grava `eval/results/regras-<AAAA-MM-DD>.json` e, no mesmo dia,
**sobrescreveria o resultado oficial**. Ganha a opção **`--rotulo <texto>`**:
`medir --rotulo pos-correcao` grava `regras-<data>-pos-correcao.json`. Sem rótulo, o
comportamento atual.

A medição usa o **mesmo** `eval/ground_truth.csv`, sem reanotar (§5 da spec do gabarito:
o gabarito descreve os modelos, não as regras).

**Esperado** (o número sai do `medir`, sem ajuste): MOD-003 com 4 FP a menos (precisão
1/3 = 0,33, R-03 ainda dispara, agora explicado pela limitação); PERF-001 com as 12 colunas
de data marcadas — as 6 julgadas `viola` viram VP; as demais aparecem como FP ou
indeterminado, conforme o veredito do Fred.

## 6. Testes

TDD, com as fábricas do `conftest`:

- `grupo_de_calculo`: tabela com `calculationGroup` → verdadeiro; sem → falso.
- `tabela_de_parametro_de_campo`: `kind: 2` → verdadeiro; `ParameterMetadata` sem `kind`
  (parâmetro hipotético) → falso; sem `extendedProperties` → falso.
- MOD-003 não marca grupo de cálculo nem parâmetro de campo isolados; continua marcando
  tabela comum isolada.
- `dax_escrito_pela_ferramenta`: parâmetro de campo verdadeiro, grupo de cálculo falso.
- PERF-001 marca coluna calculada em dimensão de data importada (partição `m`) e não marca
  em dimensão de data calculada (partição `calculated`).
- `medir --rotulo` grava no arquivo com sufixo e não toca no sem sufixo.
- Suíte inteira verde, incluindo P8 e o conjunto da recuperação regerado.

## 7. Registro

- `progress-log.md`: entrada com as correções, a medição pós-correção lado a lado com a
  oficial e a limitação da MOD-003.
- `riscos.md`: linha do R-03 com o resultado oficial (MOD-003 0,14), a correção e a
  limitação declarada.
- `eval/dataset.md`: já registra (12/10) que as correções pós-tag são análise de erros.
- `status.md`: linha da Fase 3.

## 8. Fora do escopo

Heurística para tabelas digitadas à mão (`Logo`, `Indicators`); mudança na DAX-001;
leitura de `calculationItems` pela varredura de DAX; remedir a recuperação; os 9 menores
adiados da revisão do gabarito; o segundo anotador (pendente de decisão do Fred).
