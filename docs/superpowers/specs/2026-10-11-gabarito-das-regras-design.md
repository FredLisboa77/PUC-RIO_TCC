# Gabarito das regras em P1–P7 (ground truth)

- **Data:** 11/10/2026
- **Fase:** 3, semana 8 do roadmap — primeiro dos três subprojetos da revisão de meio de projeto
- **Status:** Aguardando revisão do Fred
- **Depende de:** as 9 regras (`core/rules/`), o parser (`core/parser_bim.py`), o lexer de DAX (`core/dax.py`) e os PBIP P1–P7 em `data/pbip/` (ADR-005)
- **Planejamento:** `fase1-viabilidade-e-planejamento.md` — semana 8 ("**ground truth** dos PBIP, feito por você"; entrega `ground_truth.csv`), F15 (precisão e recall) e §11.4 (viés de anotador único, mitigado por referência documental em cada linha)

## 1. Objetivo e contexto

Medir **precisão e recall de cada regra** em P1–P7 contra um gabarito humano, para que a
avaliação da monografia não dependa só da contagem de achados. O gabarito decide duas
coisas que estão abertas:

- **R-12 / P9:** P1–P7 renderam 53 achados, acima do gatilho de ~40, mas 16 vêm da PERF-003,
  a regra de precisão mais dependente de dado. Sem ela seriam 37. A decisão sobre o P9 vai
  ao orientador com o número de achados **confirmados**, não brutos.
- **R-03:** precisão abaixo de 0,7 em alguma regra é o gatilho do risco de falsos positivos.

A revisão de meio de projeto da semana 8 foi dividida em três subprojetos, cada um com seu
ciclo: **(1) este gabarito**, (2) a busca combinada para os trechos complementares e (3) o
documento da revisão de meio de projeto para o orientador.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Quem anota | **O Fred julga**; o código prepara a planilha, valida e calcula. O gabarito fica independente de quem escreveu as regras |
| Alcance do recall | **Por regra, dentro do que cada regra cobre**: o universo é todo candidato do tipo certo, e a pergunta é a condição da âncora. Problemas fora das 9 regras não entram |
| Visão do resultado da ferramenta | **Julgamento cego, numa passada só**: a planilha lista todos os candidatos sem dizer quais a ferramenta marcou; precisão e recall saem do cruzamento posterior |
| Meio de anotação | **Planilha `.xlsx` gerada pelo código**, com lista suspensa, convertida num `eval/ground_truth.csv` versionado |
| Organização | Pacote novo **`gabarito/`**, com candidatos gerados **independentemente da lógica das regras** — senão o recall mediria a regra contra ela mesma |

## 2. Unidade de julgamento e candidatos (`gabarito/candidatos.py`)

**Unidade:** uma linha = (projeto, regra, objeto). O objeto usa **exatamente o nome que a
regra põe em `Evidencia.objeto`** — é a chave do cruzamento. A DAX-001 julga **por
expressão**, como a regra, que emite um achado por expressão com todas as ocorrências; a
linha lista cada divisão da expressão.

**ID estável:** `<id_regra>|<projeto>|<objeto>`, por exemplo `MOD-003|P2|DimDate`.

| Regra | Candidatos | Fatos neutros na linha |
|---|---|---|
| MOD-001 | todas as tabelas | se é oculta, anotações da tabela, nº de colunas |
| MOD-002 | todos os relacionamentos que não são um-para-um | direção do filtro cruzado, cardinalidades dos dois lados, se está ativo |
| MOD-003 | todas as tabelas | nº de relacionamentos em que aparece, nº de medidas, nº de colunas, se é oculta |
| MOD-005 | todas as tabelas com ao menos uma coluna de data | as colunas de data e, para cada uma, a tabela para onde aponta a `variations`, se houver |
| MOD-006 | todas as tabelas | tabelas que a filtram e tabelas que ela filtra (pela direção dos relacionamentos) |
| MOD-007 | todos os relacionamentos | cardinalidades dos dois lados, direção do filtro |
| PERF-001 | todas as colunas calculadas | expressão DAX |
| PERF-003 | todas as colunas de ponto flutuante | tipo de dado, `summarizeBy`, tabela |
| DAX-001 | todas as expressões DAX em escopo que contêm o operador `/` | sítio (medida, coluna calculada…), expressão, e o denominador de cada `/` |

**Fora da linha, para manter a cegueira:** o veredito da ferramenta, a severidade, a
mensagem e o `detalhe` do achado. Os fatos são os mesmos para candidato marcado e não
marcado, e saem do `ModeloSemantico` e do lexer, nunca das funções de regra.

**Ressalva declarada:** os candidatos saem do mesmo parser que alimenta as regras. Um
objeto que o parser não lê fica fora dos dois lados — a monografia declara, ao lado do
viés de anotador.

## 3. Planilha (`gabarito/planilha.py`)

`python -m gabarito gerar` cria **`eval/gabarito/anotacao-P1-P7.xlsx`**. O arquivo fica fora
do Git (ele é o rascunho; o gabarito oficial é o CSV), e por isso `eval/gabarito/` entra no
`.gitignore`.

- **Aba "Instruções":** o protocolo de anotação — julgar pela âncora, não pelo gosto;
  `indeterminado` só quando o modelo não traz a informação necessária (ex.: distribuição dos
  valores na PERF-003); justificativa obrigatória em `viola` e `indeterminado`; referência
  quando o julgamento usa fonte além da âncora.
- **Uma aba por regra** (nome = ID da regra). No topo, a **pergunta da âncora** em português
  e o link do Learn. Abaixo, uma linha por candidato de todos os projetos, ordenadas por
  projeto e objeto.
- **Colunas:** `id`, `projeto`, `objeto`, os fatos neutros da regra (§2), `veredito`,
  `justificativa`, `referencia`.
- **`veredito`** tem validação de dados com lista suspensa: `viola`, `não viola`,
  `indeterminado`.
- **Proteção:** a aba fica protegida (sem senha), com só `veredito`, `justificativa` e
  `referencia` desbloqueadas — evita editar um fato ou um ID por engano.
- **`gerar` recusa sobrescrever** um `.xlsx` existente: é o arquivo com os vereditos.

### Perguntas das abas

| Regra | Pergunta |
|---|---|
| MOD-001 | Esta tabela foi gerada pelo Tempo automático de data/hora? |
| MOD-002 | Este relacionamento filtra nos dois sentidos sem que o cenário exija isso, segundo a orientação de relacionamentos bidirecionais? |
| MOD-003 | Esta tabela deveria se relacionar com o resto do modelo, segundo o star schema? (Tabela de medidas ou de parâmetros isolada de propósito: não viola.) |
| MOD-005 | Esta tabela funciona como dimensão de data e não está marcada como tabela de data? |
| MOD-006 | Esta tabela é o elo intermediário de uma dimensão em floco de neve que deveria ser desnormalizada? |
| MOD-007 | Este relacionamento é um-para-um entre tabelas que descrevem a mesma entidade? |
| PERF-001 | Esta coluna calculada poderia ser criada no Power Query ou na origem, como a orientação de redução de dados recomenda? |
| PERF-003 | Esta coluna de ponto flutuante é somada de forma que a imprecisão do tipo possa afetar o resultado? |
| DAX-001 | Alguma divisão desta expressão tem denominador que pode ser zero ou BLANK, caso em que a documentação recomenda DIVIDE? |

## 4. Importação (`python -m gabarito importar`)

Lê o `.xlsx` e valida, sem gravar nada se houver qualquer problema:

1. todo candidato atual tem veredito, e só valores da lista;
2. `viola` e `indeterminado` têm `justificativa` não vazia;
3. os IDs da planilha são **exatamente** os candidatos atuais — nenhum faltando, nenhum
   sobrando (pega um modelo alterado depois da geração).

Falha → código 1 e a **lista das linhas problemáticas** (aba, linha, ID, motivo). Sucesso →
grava **`eval/ground_truth.csv`**: UTF-8, separador vírgula, cabeçalho
`id,projeto,id_regra,objeto,veredito,justificativa,referencia`, ordenado por `id`.
Versionado: é o gabarito oficial, também da Fase 5.

**`importar --parcial`:** aceita vereditos em branco, aplica as outras validações às
linhas preenchidas e só informa o progresso por regra (ex.: `MOD-003: 41/59`). Não grava o
CSV.

## 5. Métricas (`python -m gabarito medir`)

Cruza `eval/ground_truth.csv` com os achados que as regras produzem **agora** em P1–P7.

**Consistência primeiro:** todo achado precisa casar com um ID do gabarito. Achado sem
candidato = furo no gerador de candidatos → código 1, sem métrica.

**Por regra**, a matriz de confusão: VP (marcou, `viola`), FP (marcou, `não viola`), FN (não
marcou, `viola`), VN (não marcou, `não viola`); os indeterminados contados à parte, entre
marcados e não marcados. Três versões de precisão e de recall:

- **principal:** sem os indeterminados;
- **piso:** indeterminados contra a regra (marcado indeterminado = FP; não marcado = FN);
- **teto:** indeterminados a favor (marcado = VP; não marcado = VN).

Divisão por zero (regra sem achado ou sem violação) → `null` no JSON e `—` no console,
nunca 0 nem 1.

**Agregados:** por categoria (modelagem, performance, DAX) e total, em **micro** (somando as
matrizes) e **macro** (média por regra, cada regra pesa o mesmo); por projeto, como
referência.

**Gatilhos dos riscos:**

- **R-03:** cada regra com precisão principal < 0,7 é sinalizada.
- **R-12:** número de **VP** em P1–P7 contra o gatilho de 40, com e sem a PERF-003.

**Saída:** `eval/results/regras-<AAAA-MM-DD>.json` (matrizes, métricas, gatilhos e a lista
de divergências) e uma tabela no console, em ASCII.

**Divergências para releitura:** a lista dos FP e FN com a justificativa do Fred. Cada uma
vira, depois, uma decisão (corrigir a regra, declarar a limitação ou aceitar). **Corrigir
regras está fora desta spec**: é decisão do Fred depois de ver os números, para que o
gabarito não seja ajustado ao resultado.

**Independência ao longo do tempo:** o gabarito descreve os modelos, não as regras. Regra
alterada depois → `medir` de novo contra o **mesmo** CSV, sem reanotar. Só modelo novo (P9)
pede anotação.

## 6. Organização

```
gabarito/
  __init__.py
  __main__.py      # python -m gabarito gerar | importar [--parcial] | medir
  candidatos.py    # universo e fatos neutros por regra (§2)
  planilha.py      # gravar e ler o .xlsx (§3, §4)
  metricas.py      # matrizes, agregados, gatilhos (§5)
```

**Dependência nova:** `openpyxl`, versão fixada em `requirements.txt` (biblioteca pura em
Python, sem compilador).

## 7. Testes

TDD, sem depender de `data/`, exceto os marcados:

- **Candidatos:** para cada regra, um modelo sintético (fábricas do `conftest`) e o
  universo esperado; **todo achado da regra casa com um candidato** nos sintéticos; o mesmo
  teste sobre P1–P7, pulado sem `data/`.
- **Cegueira:** nenhuma célula da planilha gerada contém severidade, mensagem ou indicação
  de que o candidato foi marcado.
- **Planilha:** gerar e reler devolve os mesmos IDs; a lista suspensa e a proteção existem;
  `gerar` recusa sobrescrever.
- **Importação:** um teste por falha (veredito ausente, valor fora da lista, `viola` sem
  justificativa, ID faltando, ID sobrando); `--parcial` com progresso; CSV gravado só em
  sucesso.
- **Métricas:** matrizes com contas feitas à mão; piso e teto com `indeterminado`; `null`
  sem divisor; macro e micro; gatilhos do R-03 e do R-12; recusa com achado sem candidato.

## 8. Entrega e registro

1. Ferramentas prontas e `anotacao-P1-P7.xlsx` gerado.
2. **O Fred preenche a planilha** (≈ 400–450 linhas), em quantas sessões quiser, usando
   `importar --parcial` para acompanhar.
3. `importar` grava o CSV; `medir` produz os números; progress-log registra as métricas, os
   gatilhos e as divergências.

## 9. Fora do escopo

Corrigir regras; problemas de boas práticas fora das 9 regras; segundo anotador e medida de
concordância; a busca combinada (subprojeto 2); o documento da revisão de meio de projeto
(subprojeto 3).
