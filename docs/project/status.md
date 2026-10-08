# Status do Projeto — resumo de andamento

**Projeto:** powerbi-ai-auditor — auditoria automatizada de projetos Power BI (PBIP) com IA
**TCC:** PUC-Rio · **Autor:** Fred
**Posição:** fim da semana 4 de 13 · **Atualizado em:** 08/10/2026

> Este é o resumo executivo para acompanhamento. O detalhamento técnico de cada
> dia está em [`progress-log.md`](progress-log.md); as decisões de arquitetura em
> [`../adr/`](../adr/); os riscos em [`riscos.md`](riscos.md); o escopo em
> [`backlog.md`](backlog.md).

---

## 1. Resumo em cinco linhas

As duas primeiras fases estão concluídas. A ferramenta já lê um projeto PBIP real,
normaliza o modelo semântico e aponta 15 problemas de boas práticas nele, com cada
regra ancorada numa página do Microsoft Learn. São 101 testes automatizados
passando. O maior risco técnico do projeto — rodar um LLM na GPU disponível — foi
resolvido por medição, não por estimativa. **Dois itens da semana 4 ficaram
abertos** e são o assunto que mais precisa de decisão agora: a contagem de regras
está em 8 de 20–25, e os sete projetos públicos do dataset ainda não foram
convertidos, o que mantém o risco R-12 sem avaliação.

---

## 2. Andamento por fase

| Fase | Semanas | Status | Fechamento |
|---|---|---|---|
| F1 — Viabilidade e planejamento | 1–2 | **Concluída** | 29/09/2026 — gate aprovado, spike de LLM validado |
| F2 — Leitura do PBIP e regras | 3–4 | **Concluída, com 2 pendências** | 08/10/2026 — motor de regras mergeado na `main` |
| F3 — RAG e análise com LLM | 5–8 | **A iniciar** | Revisão de meio de projeto na semana 8 |
| F4 — Interface e relatório | 9–10 | Não iniciada | — |
| F5 — Avaliação, documentação e banca | 11–13 | Não iniciada | — |

**Posição no calendário:** o projeto começou em 22/09/2026. Em 08/10/2026 estamos
na terceira semana de calendário tendo concluído o trabalho previsto para a
quarta semana do roadmap — ou seja, **cerca de uma semana à frente do cronograma em
tempo**, e atrasado em um entregável específico (seção 4).

---

## 3. O que já funciona, verificado

| Entregável | Evidência |
|---|---|
| Ingestão de PBIP (pasta ou `.zip`), com validação de estrutura | Testes sobre PBIP sintéticos montados em pasta temporária |
| Parser do `model.bim` (TMSL) para modelo interno normalizado | Lê o P8 real: 19 tabelas, 93 medidas, 106 colunas, 35 colunas calculadas, 11 relacionamentos, `compatibilityLevel` 1600 |
| Motor de regras determinísticas, com ordem estável e isolamento de erro por regra | Uma regra que falhe não derruba a auditoria, e sua saída parcial é descartada inteira |
| 8 regras estruturais, cada uma com âncora no Microsoft Learn | `python -m core.rules.catalogo` imprime o catálogo com as URLs |
| Suíte de testes | **101 testes passando**, dos quais 9 leem o PBIP real |

### As 8 regras e o que acharam no P8

O P8 é o projeto `CONTOSO — Painel de Análise de Vendas Online`, usado como
**estudo de caso** (não entra nas métricas — ver seção 5). Total: **15 achados**,
com as contagens travadas em teste de regressão.

| ID | Regra | Severidade | Achados no P8 |
|---|---|---|---|
| MOD-001 | Tempo automático de data/hora está ligado | alta | 4 |
| MOD-002 | Relacionamento com filtro bidirecional | alta | 3 |
| MOD-003 | Tabela sem relacionamento com o resto do modelo | baixa | 2 |
| MOD-005 | Dimensão de data não está marcada como tabela de data | média | 1 |
| MOD-006 | Dimensão em floco de neve | baixa | 2 |
| MOD-007 | Relacionamento um-para-um | média | 1 |
| PERF-001 | Coluna calculada em DAX | média | 1 |
| PERF-003 | Coluna de ponto flutuante somada | baixa | 1 |

**O resultado encadeia causa, e não só lista sintomas:** a `DimCalendar` nunca foi
marcada como tabela de data (MOD-005), e é justamente por isso que o Power BI
gerou uma tabela de data automática para a própria `DimCalendar[Data]` — uma das 4
ocorrências de MOD-001. Essa cadeia é o núcleo da seção de estudo de caso da
monografia.

---

## 4. Pendências abertas da semana 4 — precisam de decisão

### 4.1 Contagem de regras: 8 de 20–25

O roadmap previa "20–25 regras determinísticas" na semana 4. A meta **não mudou**
(`backlog.md`), mas a ordem de implementação passou a seguir o critério de
**detectabilidade**, decidido em 29/09/2026: entram primeiro as regras cujo
problema é identificável de forma confiável no `model.bim`.

| Grupo | Conteúdo | Situação |
|---|---|---|
| 1 | Regras estruturais (modelagem, performance estática) | **Completo — são as 8 entregues** |
| 2 | Regras de DAX com padrão textual inequívoco | **Próximo passo** |
| 3 | Regras de DAX dependentes de contexto | Só se sobrar orçamento (sem parser sintático, a heurística erra muito) |
| 4 | Regras de M | No MVP, mas são o primeiro corte sob pressão de prazo (R-07) |

**Por que 8 e não mais no grupo 1:** em 06/10/2026 passou a valer uma segunda
condição, anterior à detectabilidade — uma regra só entra se existir **passagem
citável do Microsoft Learn** que a sustente, lida antes de qualquer código. Isso
**eliminou 3 das 8 regras estruturais propostas**, uma delas porque a página que a
sustentaria recomendava exatamente o que a regra marcaria como defeito. A exigência
custou a leitura de cinco páginas e evitou escrever o código de três regras
indefensáveis.

Em 08/10/2026 a mesma exigência derrubou uma nona versão de regra, por um motivo
novo: MOD-005 lia uma propriedade (`dataCategory: "Time"`) que **o Power BI Desktop
nunca escreve** no arquivo. Ela tinha âncora e era decidível no TMSL, mas marcaria
como defeituosa também a dimensão corretamente configurada. Foi reescrita sobre
evidência que de fato existe no arquivo.

> **Consequência para a metodologia da monografia:** o critério de detectabilidade
> precisa de um terceiro teste, além de "existe âncora no Learn" e "é decidível no
> TMSL" — **a propriedade que a regra lê é escrita pela ferramenta que gera a
> entrada.** Das 8 regras, MOD-005 foi a única a passar nos dois primeiros e falhar
> no terceiro, e a falha só apareceu por verificação contra um arquivo real.

### 4.2 Dataset P1–P7 não convertido, e o risco R-12 sem avaliação

O entregável da semana 4 incluía "relatório de achados em JSON para todos os PBIP".
**Só o P8 foi analisado.** Os sete projetos públicos da Microsoft (P1–P7, licença
MIT) ainda não foram convertidos para PBIP.

Isso mantém em aberto o **R-12** — o risco de maior impacto hoje:

> *As amostras públicas da Microsoft têm poucos problemas, reduzindo a
> significância da avaliação.*

O gatilho definido para a semana 4 é **menos de ~40 achados em P1–P7**, e ele não
pôde ser medido. A referência concreta é desfavorável: se o P8, um modelo
reconhecidamente problemático, rende 15 achados com as 8 regras, é improvável que
os sete projetos da Microsoft somem 40 sem as regras de DAX.

**Contingência prevista:** o slot **P9** — um segundo projeto próprio no dataset.

**Recomendação:** converter P1–P7 e rodar as 8 regras sobre eles **antes de
avançar na Fase 3**, em vez de esperar a semana 8 como no plano original. É uma
medição de poucas horas que decide se o P9 entra, e essa decisão fica mais cara a
cada semana.

---

## 5. Decisão de método que o orientador deve conhecer

Em 29/09/2026 o P8 **saiu do dataset de métricas e virou estudo de caso
qualitativo** (ADR-005, 2ª emenda). O dataset de avaliação voltou a ser P1–P7,
todos MIT.

| | |
|---|---|
| **Ganho** | Toda métrica da monografia passa a ser reprodutível por terceiros, e a ressalva "apenas P1–P7" desaparece |
| **Custo** | O R-12 voltou de *Mitigado* para **Aberto**: a inclusão do P8 era exatamente a mitigação desse risco |

Foi uma troca deliberada de significância estatística por reprodutibilidade. É a
decisão de método mais consequente do projeto até aqui, e é ela que torna a
pendência 4.2 urgente.

---

## 6. Riscos

**14 riscos registrados.** Situação em 08/10/2026:

| Status | Riscos |
|---|---|
| **Resolvido** | R-02 (LLM na GPU de 6 GB), R-09 (poucos PBIP públicos) |
| **Mitigado** | R-06 (dados sensíveis), R-08 (dependências no Windows, parcial), R-11 (OneDrive), R-14 (disco C: cheio) |
| **Aberto** | R-01, R-03, R-04, R-05, R-07, R-10, R-12, R-13 |

### Os dois que merecem atenção agora

**R-12 — significância da avaliação** · P=M, I=**Alto** · ver seção 4.2.
É o risco de maior impacto em aberto, e o único cujo gatilho já venceu sem medição.

**R-03 — falsos positivos em heurísticas de DAX** · P=Alta, I=M.
O risco se materializa justamente no **grupo 2**, que é o próximo passo. Duas
mitigações já estão de pé: teste positivo e negativo por regra, e a exigência de
âncora verificada, que no grupo estrutural eliminou a única regra dependente de
convenção de nomenclatura. O episódio do MOD-005 mostra que a exigência funciona
— e que precisa do terceiro teste descrito em 4.1.

### Riscos que já custaram trabalho real

Vale registrar que três riscos não ficaram no papel: o **R-14** chegou a deixar o
disco C: com 0 byte livre, exigindo mover o projeto para `D:\`; o **R-11** exigiu
tirar a cópia de trabalho do OneDrive; e o **R-02**, único risco de probabilidade e
impacto altos, foi resolvido com medição — o modelo de 7B ocupa ~5,3 GB dos 6 GB de
VRAM e responde em 6,0 s por achado, contra um limite de 60 s.

---

## 7. Decisões de arquitetura registradas

| ADR | Assunto | Consequência |
|---|---|---|
| [ADR-001](../adr/ADR-001-formato-model-bim.md) | `model.bim` (TMSL), não TMDL | Leitura com a biblioteca padrão do Python, sem dependências; elimina o maior risco técnico da Fase 2 |
| [ADR-002](../adr/ADR-002-stack-tecnologica.md) | Stack, com o ambiente real medido | GPU de 6 GB é limite exato, não folga: modelos de 13B+ descartados |
| [ADR-003](../adr/ADR-003-orquestracao-sequencial-e-deteccao-hibrida.md) | As regras são a única fonte de achados | O LLM só explica e recomenda, e **precisa citar** um trecho recuperado |
| [ADR-004](../adr/ADR-004-coleta-da-base-rag.md) | Coleta pelas páginas públicas do Learn | O repositório `MicrosoftDocs/powerbi-docs` não existe publicamente (404) — o plano original era inviável |
| [ADR-005](../adr/ADR-005-dataset-de-avaliacao.md) | Dataset de amostras MIT da Microsoft | Com 2 emendas; a 2ª é a decisão da seção 5 |

---

## 8. Próximos passos

| # | Passo | Por quê agora |
|---|---|---|
| 1 | **Converter P1–P7 e rodar as 8 regras** | Decide o R-12 e o slot P9. Gatilho da semana 4 já vencido; custa poucas horas e encarece a cada semana (seção 4.2) |
| 2 | Formalizar o terceiro teste do critério de detectabilidade | A lição do MOD-005 deve valer **antes** de escolher as regras de DAX, não depois (seção 4.1) |
| 3 | Regras de DAX por padrão textual (grupo 2) | Caminho para a meta de 20–25, sobre o motor já provado |
| 4 | Iniciar a Fase 3: catálogo de fontes (`sources.yaml`) e coleta | Entregável da semana 5. As URLs canónicas das 8 regras já são, por construção, parte do catálogo que a RAG precisa conter |

---

## 9. Como verificar o que está aqui

```powershell
# clonar e preparar
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest                            # 101 testes (os 9 do PBIP real são pulados sem data/)
python -m core.rules.catalogo     # as 8 regras com as URLs do Microsoft Learn
```

Os 9 testes que leem o PBIP real são **pulados** automaticamente numa cópia limpa
do repositório, porque `data/` não é versionado — o PBIP contém o modelo de um
projeto real. São eles que travam as 15 ocorrências medidas.

**Repositório:** <https://github.com/FredLisboa77/PUC-RIO_TCC>
A Fase 2 foi desenvolvida na branch `fase2-motor-de-regras`, preservada no remoto
como registro do recorte da fase.
