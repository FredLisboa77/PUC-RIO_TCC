# Avaliação da geração (rubrica humana) e consolidação dos resultados

- **Data:** 13/10/2026
- **Fase:** 5, semana 11 — subprojeto 1 de 3 (os outros: monografia, semana 12; demonstração,
  semana 13)
- **Status:** Aguardando revisão do Fred
- **Depende de:** `run_audit` e o cache (`core/auditoria.py`, `core/analise/cache.py`), o padrão
  do `gabarito/` (planilha protegida, CSV oficial, medição), os resultados já medidos em
  `eval/results/`
- **Branch:** `fase5-avaliacao`, criada a partir da `main` (`f583029`)
- **Funcionalidade do planejamento:** F15 (avaliação: Precision@K, MRR, precisão/recall,
  **rubrica**)

## 1. Objetivo e enquadramento

A detecção (gabarito na tag `regras-gt`), a recuperação e a pertinência dos complementares já
estão medidas. Falta a **geração**: dado um achado, o LLM explica e cita bem? Até aqui só houve a
leitura à mão dos 15 achados do P8 em 11/10/2026 — e o P8 é estudo de caso, fora das métricas
(ADR-005). Aquela leitura mostrou que 2 de 15 recomendações erradas passaram nos três critérios
automáticos; daí a rubrica humana com item próprio de recomendação correta (confirmado em
12/10/2026).

Este subprojeto entrega os números de resultados da monografia: a rubrica da geração em P1–P7 e
um **consolidado** que reúne, com intervalo de confiança, tudo o que já foi medido.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Divisão da Fase 5 | Três subprojetos: avaliação (este), monografia, demonstração — nessa ordem |
| Achados na rubrica | **Todos os 61 de P1–P7** (sem amostra); o P8 fica no estudo de caso |
| Versão das regras | **`main` atual** (com as correções da MOD-003 e da PERF-001): a rubrica mede a geração, cujo código é o mesmo da tag; a versão das regras só decide quais achados recebem explicação, e isso é declarado. O resultado oficial da **detecção** continua sendo o da tag |
| Escala | Três vereditos **sim / não / indeterminado** por achado, justificativa obrigatória no "não" |
| Ferramenta | Pacote próprio `avaliacao_geracao/`, no molde do `gabarito/`; anotação em planilha cega |

## 2. A rodada avaliada

- `python -m avaliacao_geracao auditar` roda `run_audit` completo, com `ClienteComCache`, em
  cada projeto de P1–P7 (`data/pbip/P[1-7]_*`) e grava os JSONs em
  `eval/geracao/auditorias/<projeto>.json`.
- O cache garante que repetir o comando reproduz os mesmos textos nesta máquina. O comando
  informa quantas respostas vieram do cache; se alguma **não** veio, avisa que o texto daquele
  achado pode ter mudado em relação a uma rodada anterior.
- **Id do achado:** `projeto|regra|objeto` (estável entre rodadas).
- **Impressão digital:** sha256 de `explicacao + "\n" + recomendacao` do achado gerado. Liga o
  veredito ao texto julgado: a importação recusa a linha se o texto em disco mudou.
- **Fora do git:** `eval/geracao/` e a planilha (`eval/gabarito/`, já ignorada). Os JSONs da
  auditoria carregam seções do Learn como contexto; os termos do Learn permitem cópia local,
  não redistribuição, e o repositório é público. **No git:** o CSV oficial dos vereditos e os
  resultados — o bastante para conferir os números sem redistribuir o texto do Learn.

## 3. A planilha de anotação

`python -m avaliacao_geracao gerar` grava `eval/gabarito/rubrica-geracao-P1-P7.xlsx`.

- **Uma linha por achado com explicação gerada** (`situacao == "gerado"`), ordenada por
  projeto, regra e objeto. Achados `sem_fundamentacao` não entram (seção 5, taxa de descarte).
- **Colunas de leitura (protegidas):** id, projeto, regra, título da regra, objeto, mensagem da
  regra, explicação, recomendação, trechos citados (para cada citação: `[n] título — seção`,
  URL com âncora, texto) e **referência da regra** (URL canônica e o texto do trecho âncora,
  que é sempre o trecho de origem `ancora` no contexto do achado).
- Textos de trecho cortados em **3.000 caracteres** com `[…]` (a célula do Excel tem limite e a
  leitura fica viável); o link leva ao texto completo. Caracteres ilegais do Excel removidos,
  como no gabarito.
- **Cega aos sinais automáticos:** `cita_ancora`, divergências de fidelidade, `do_cache`,
  tempos e tokens **não** aparecem — senão a comparação humano × automático (seção 5) não vale.
- **Colunas de anotação (livres):** `pertinente`, `fiel`, `recomendacao_correta` (lista
  `sim / não / indeterminado`), `justificativa`, `observacao`.
- **Definições** (também numa aba "Instruções" da planilha):
  - **pertinente** — pelo menos um trecho citado é de fato a passagem da documentação que
    sustenta o achado (não basta existir entre os trechos fornecidos);
  - **fiel** — o que a explicação afirma é sustentado pelos trechos citados ou pelos fatos do
    achado, sem nada inventado (números, nomes, comportamentos);
  - **recomendacao_correta** — a recomendação resolve o problema neste modelo, sem erro
    técnico.
- `gerar` recusa sobrescrever uma planilha existente (só com `--forcar`).

## 4. Importação

`python -m avaliacao_geracao importar [--parcial]` lê a planilha e grava o CSV oficial
`eval/rubrica_geracao.csv` (colunas: `id, impressao, pertinente, fiel, recomendacao_correta,
justificativa, observacao`).

Recusa, listando **todas** as linhas com problema de uma vez e sem gravar nada:
veredito fora da lista; algum "não" sem justificativa; impressão digital que não bate com o
achado da auditoria em disco; id duplicado; id que não existe na auditoria. Sem `--parcial`,
todas as linhas precisam dos três vereditos; com `--parcial`, linhas sem veredito são puladas.

## 5. Métricas

`python -m avaliacao_geracao medir` grava `eval/results/geracao-<data>.json`.

- **Por item** (`pertinente`, `fiel`, `recomendacao_correta`), no formato do gabarito:
  principal = sim / (sim + não); piso = indeterminado conta como não; teto = indeterminado
  conta como sim; **intervalo de Wilson 95%** sobre a principal (`None` sem denominador).
- **Recortes:** total, por regra, por categoria.
- **Utilizável como está** (derivado): os três itens "sim"; principal sobre as linhas sem
  nenhum indeterminado, com piso e teto.
- **Taxa de descarte** (automática, dos JSONs): `sem_fundamentacao` / total, por motivo.
- **Humano × automático:** duas tabelas 2×2 sobre as linhas sem indeterminado no item humano —
  `cita_ancora` × `pertinente` e "sem divergência" × `fiel` — com concordância simples e kappa
  de Cohen (Cohen, 1960).
- O resultado registra o commit, a data e as contagens de entrada.

## 6. Consolidação

`python -m avaliacao_geracao consolidar` grava `eval/results/consolidado-<data>.json`, a
**fonte única** das tabelas de resultados da monografia:

| Bloco | Origem | Acréscimo |
|---|---|---|
| `regras` (oficial) | `eval/results/regras-2026-10-12.json` (tag `regras-gt`) | Wilson 95% da precisão e do recall principais, por regra, por categoria e no total — o arquivo oficial não muda |
| `regras_pos_correcao` (análise de erros) | `eval/results/regras-2026-10-12-pos-correcao.json` | o mesmo Wilson; rotulado como análise de erros |
| `recuperacao` | `eval/results/recuperacao-2026-10-11.json` | os números da configuração escolhida |
| `complementares` | `eval/results/complementares-2026-10-12.json` | a macro das três buscas e a decisão |
| `geracao` | o `geracao-<data>.json` mais recente | — |

Cada bloco registra o arquivo de origem. Origem ausente: mensagem dizendo qual, nada gravado.

`avaliacao_geracao/estatistica.py` tem `wilson(sucessos, total, z=1.96)` e `kappa(tabela_2x2)`.

## 7. Erros

| Situação | O que acontece |
|---|---|
| `auditar` com o Ollama fora do ar | Aborta no aquecimento (ADR-003); nada gravado como rodada avaliada |
| `auditar` com respostas fora do cache | Grava e avisa quantas não vieram do cache |
| Planilha inválida | Lista todas as linhas com problema; nada gravado |
| `gerar` com planilha existente | Recusa sem `--forcar` |
| `consolidar` sem origem | Diz qual falta; nada gravado |

Tudo como mensagem e código 1; nunca traceback.

## 8. Testes

- **Estatística:** Wilson contra valores de referência (inclusive 0 de 0 → `None`, 0 de n,
  n de n) e kappa contra exemplo de livro.
- **Planilha:** gerada de auditorias em memória; sinais automáticos ausentes; colunas protegidas;
  corte em 3.000; caracteres ilegais; recusa de sobrescrever.
- **Importação:** cada recusa da seção 4 e o `--parcial`.
- **Métricas:** principal/piso/teto, Wilson, recortes, utilizável, descarte, tabelas 2×2 e kappa.
- **Consolidação:** com origens sintéticas, inclusive origem ausente.
- **Fumaça do comando** `auditar` com LLM falso e PBIP sintético.

## 9. Fluxo de trabalho

1. Implementação e testes; `auditar` em P1–P7 (~10 min); `gerar`.
2. **Anotação pelo Fred** (~3,5–4 h), com `importar --parcial` quando quiser.
3. `importar`, `medir`, `consolidar`; registro no progress-log e no status.

## 10. Fora deste subprojeto

| Item | Destino |
|---|---|
| Segundo anotador / kappa entre anotadores | Limitação declarada (decisão de 12/10/2026) |
| P9 | Não acionado |
| Texto da monografia e estudo de caso do P8 | Subprojeto 2 |
| Roteiro e ensaio da demonstração | Subprojeto 3 |
