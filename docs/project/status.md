# Status do Projeto — resumo de andamento

**Projeto:** powerbi-ai-auditor — auditoria automatizada de projetos Power BI (PBIP) com IA
**TCC:** PUC-Rio · **Autor:** Fred
**Posição:** semana 6 de 13 — Fase 2 encerrada; P1–P7 convertidos e medidos · **Atualizado em:** 09/10/2026

> Este é o resumo executivo para acompanhamento. O detalhamento técnico de cada
> dia está em [`progress-log.md`](progress-log.md); as decisões de arquitetura em
> [`../adr/`](../adr/); os riscos em [`riscos.md`](riscos.md); o escopo em
> [`backlog.md`](backlog.md).

---

## 1. Resumo em cinco linhas

As duas primeiras fases estão concluídas, a segunda já incluindo o grupo de regras
de DAX que o roadmap original reservava para o início da Fase 3. A ferramenta já lê
um projeto PBIP real, normaliza o modelo semântico e aponta 15 problemas de boas
práticas nele, com cada uma das **9 regras** ancorada numa página do Microsoft
Learn. São **196 testes** automatizados passando. O maior risco técnico do
projeto — rodar um LLM na GPU disponível — foi resolvido por medição, não por
estimativa. A contagem de regras **deixou de ser meta e passou a ser resultado**
(D-1): o critério de detectabilidade, com um terceiro teste formulado nesta etapa,
rejeitou uma regra de alto valor esperado (PERF-005) por falta de evidência
suficiente — e **essa rejeição, não a contagem, é o resultado que a monografia
defende**. Os sete projetos públicos do dataset foram convertidos em 09/10/2026 e
renderam **53 achados**, acima do gatilho de ~40 do R-12 — mas 16 deles vêm da
regra de precisão mais dependente de dado, e sem ela seriam 37. A decisão sobre o
projeto de contingência P9 precisa considerar as duas contas (seção 4.2).

---

## 2. Andamento por fase

| Fase | Semanas | Status | Fechamento |
|---|---|---|---|
| F1 — Viabilidade e planejamento | 1–2 | **Concluída** | 29/09/2026 — gate aprovado, spike de LLM validado |
| F2 — Leitura do PBIP e regras | 3–5 | **Concluída** | 08/10/2026 — motor de regras e 9 regras (8 estruturais, já na `main`, mais o grupo 2 de DAX na branch `fase2-regras-de-dax`, a integrar) |
| F3 — RAG e análise com LLM | 6–8 | **A iniciar** | Revisão de meio de projeto na semana 8 |
| F4 — Interface e relatório | 9–10 | Não iniciada | — |
| F5 — Avaliação, documentação e banca | 11–13 | Não iniciada | — |

**Posição no calendário, e o uso da folga que a atualização anterior reportou:**
o projeto começou em 22/09/2026. Na atualização de 06/10/2026 estávamos cerca de
uma semana à frente do cronograma em tempo — terceira semana de calendário,
trabalho da quarta semana do roadmap já concluído. **Esta etapa consumiu essa
folga.** O grupo 2 de regras de DAX é trabalho da Fase 2, mas foi executado na
**semana 5 do roadmap**, que estava reservada ao primeiro entregável da Fase 3 (o
catálogo de fontes `rag/sources.yaml`). A troca foi deliberada: gastar a folga
para fechar o conjunto de regras com rigor — formulando e aplicando o terceiro
teste do critério de detectabilidade antes de escrever código — em vez de começar
a Fase 3 com o conjunto de regras incompleto. **Ao final desta etapa o projeto
está em dia com o roadmap, não mais adiantado**, e a Fase 3 começa na semana 6.
Se a semana 7 atrasar, o primeiro corte continua sendo o já previsto — reduzir as
regras de M, depois abrir mão do PDF (R-07).

---

## 3. O que já funciona, verificado

| Entregável | Evidência |
|---|---|
| Ingestão de PBIP (pasta ou `.zip`), com validação de estrutura | Testes sobre PBIP sintéticos montados em pasta temporária |
| Parser do `model.bim` (TMSL) para modelo interno normalizado, agora incluindo hierarquias, `sortByColumn`, `variations` e roles de RLS | Lê o P8 real: 19 tabelas, 93 medidas, 106 colunas, 35 colunas calculadas, 11 relacionamentos, `compatibilityLevel` 1600 |
| Motor de regras determinísticas, com ordem estável e isolamento de erro por regra | Uma regra que falhe não derruba a auditoria, e sua saída parcial é descartada inteira |
| Lexer de DAX (`core/dax.py`) — leitura de texto livre, não mais hipótese | **137 de 137** expressões DAX do P8 tokenizadas, **zero** token `DESCONHECIDO` — o número que substitui "usamos expressões regulares" |
| Varredura de DAX com lacuna declarada (`core/rules/expressoes.py`) | **105 de 105** expressões em escopo de autor cobertas, **0 lacunas** no P8; o runner agora declara essa cobertura junto dos achados |
| 9 regras, cada uma com âncora no Microsoft Learn (8 estruturais + DAX-001) | `python -m core.rules.catalogo` imprime o catálogo com as URLs |
| Suíte de testes | **196 testes passando**, dos quais os que leem o PBIP real continuam travando as 15 ocorrências medidas |

### As 9 regras e o que acharam no P8

O P8 é o projeto `CONTOSO — Painel de Análise de Vendas Online`, usado como
**estudo de caso** (não entra nas métricas — ver seção 5). Total: **15 achados,
sem mudança nesta etapa** — a regra nova (DAX-001) rendeu zero no P8 —, com as
contagens travadas em teste de regressão.

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
| DAX-001 | Divisão com o operador `/` onde o denominador pode ser zero ou BLANK | média | 0 — confirmado pelo lexer e por um controle sobre toda barra em escopo; causa é ausência do padrão no texto, não cegueira da regra (ver seção 4.1) |

**O resultado encadeia causa, e não só lista sintomas:** a `DimCalendar` nunca foi
marcada como tabela de data (MOD-005), e é justamente por isso que o Power BI
gerou uma tabela de data automática para a própria `DimCalendar[Data]` — uma das 4
ocorrências de MOD-001. Essa cadeia é o núcleo da seção de estudo de caso da
monografia.

---

## 4. O que esta etapa decidiu, e o que segue em aberto

### 4.1 D-1: a contagem de regras deixou de ser meta e passou a ser resultado

O roadmap previa "20–25 regras determinísticas" na semana 4, e a atualização
anterior deste documento ainda reportava essa meta como pendência (8 de 20–25).
Essa pendência está **resolvida — por decisão, não por chegar ao número**:

| Grupo | Conteúdo | Situação |
|---|---|---|
| 1 | Regras estruturais (modelagem, performance estática) | **Completo — 8 regras** |
| 2 | Regras de DAX com padrão textual inequívoco | **Fechado nesta etapa — 1 regra (DAX-001)** |
| 3 | Regras de DAX dependentes de contexto | Fora do MVP (sem parser sintático, a heurística erra muito) |
| 4 | Regras de M | Segue no MVP, primeiro corte sob pressão de prazo (R-07) |

Em 06/10/2026 passou a valer uma segunda condição, anterior à detectabilidade —
âncora citável do Microsoft Learn, verificada antes do código — que eliminou 3 das
8 regras estruturais propostas e reescreveu a MOD-005 (ela lia uma propriedade que
o Power BI Desktop nunca grava no arquivo).

Nesta etapa (08/10/2026) o critério ganhou um **terceiro teste**, formulado a
partir da lição da MOD-005: suficiência de evidência, em três cláusulas — (a)
todas as formas da condição, (b) todos os sósias do sinal, (c) todos os sítios
onde o sinal pode morar. Afirmação por ausência exige as três completas
(`backlog.md`). Esse teste teve seu **primeiro caso de rejeição**: a **PERF-005**
("coluna sem uso") tinha âncora já transcrita e era a regra de maior rendimento
esperado da etapa — e ainda assim foi recusada, antes do código, porque a
documentação que a sustenta justifica uma coluna por servir ao **relatório ou** à
estrutura do modelo, e a camada de relatório (F19) a ferramenta não lê. Medido no
P8: `usos_de_coluna` achou 36 colunas sem uso estrutural; a regra reportaria
**33** (três saem por serem geradas por agrupamento/análise). Dessas 33, apenas
**5** são defensáveis (chaves substitutas órfãs, verdadeiro positivo); **3** são
colunas de calendário que a própria documentação recomenda manter (falso
positivo **confirmado**); e **25** são atributos reportáveis cujo uso a
ferramenta não pode verificar, porque depende da camada de relatório. **A
precisão não pode ser estabelecida com o que a ferramenta lê** — varia entre
~15% (5/33, se as 25 estiverem de fato em uso, o cenário mais provável) e ~91%
(30/33, no outro extremo) —, contra o gatilho de 0,7 do R-03. Essa indeterminação
é a mesma violação da cláusula (c) dita de outra forma: a regra não foi recusada
por ter precisão medida baixa, mas por sua precisão ser impossível de fixar
dentro do escopo do MVP.

A **DAX-001** (divisão com `/` onde o denominador não é constante) entrou com
âncora verificada no mesmo dia — e a verificação quase a derrubou pelo mesmo
motivo: o enunciado original marcaria como defeito exatamente o que a
documentação recomenda quando o denominador é constante. A regra que entrou no
código afirma apenas sobre denominador não constante. Seu rendimento no P8 é
**zero**, e o zero foi confirmado por duas medidas independentes — a regra e um
controle sobre toda divisão em escopo —, não apenas pela ausência de achado da
regra.

A **DAX-003** (`FILTER` sobre tabela inteira) ficou de fora desta etapa: zero
ocorrência nas 105 expressões em escopo do P8, sem evidência real para ancorar o
teste. Fica candidata registrada. A **DAX-002** (iteração desnecessária) segue sem
âncora verificada; a etapa classificou à mão as 6 ocorrências de `SUMX` do P8 e
nenhuma é iteração desnecessária — o que não decide a regra a favor nem contra,
só confirma que o P8 não a exerceria.

**O resultado, para a monografia:** mantendo a exigência de âncora e o terceiro
teste, e sem abrir o grupo 3, o que está fechado são **9 regras** (8 do grupo 1,
1 do grupo 2); o que falta decidir é, no máximo, mais 1 do grupo 2 (DAX-002, se
a âncora verificar) mais o que o grupo 4 (regras de M) render — e esse grupo
ainda não foi atacado, então o projeto não tem hoje base para apontar um total
otimista único, muito menos afirmar que ele chega a 20–25. A diferença não é um
déficit de esforço — é o critério funcionando: a monografia defende as **9
regras** entregues e usa as regras recusadas (PERF-005, e antes dela três regras
estruturais e a convenção de nomenclatura) como evidência do próprio método, não
uma contagem otimista que ninguém somou com confiança.

### 4.2 Dataset P1–P7 convertido e medido — o gatilho do R-12 não disparou

Os sete projetos públicos (P1–P7, licença MIT) foram convertidos para PBIP em
09/10/2026 e auditados pelas 9 regras, sem falha de regra em nenhum. O gatilho do
**R-12** — *menos de ~40 achados em P1–P7* — **não disparou**:

| | P1 | P2 | P3 | P4 | P5 | P6 | P7 | **Total** |
|---|---|---|---|---|---|---|---|---|
| Achados | 10 | 4 | 8 | 6 | 18 | 7 | 0 | **53** |

Por regra: PERF-001 19, PERF-003 16, MOD-003 7, DAX-001 6, MOD-006 3, MOD-001 1,
MOD-007 1. A DAX-001, que deu zero no P8, achou 6 no P5.

**A margem é fina, e depende de uma regra.** As 19 ocorrências da PERF-001 foram
revistas uma a uma e resistem à âncora: nenhuma coluna avalia medida ou usa
funcionalidade exclusiva de DAX, que é a exceção que a própria documentação
declara. A PERF-003 é diferente: a âncora diz que a soma imprecisa em ponto
flutuante é **rara** e depende da distribuição dos valores, que a ferramenta não
lê. **Sem a PERF-003, P1–P7 somam 37 — abaixo do gatilho.** O ground truth da
semana 8 dirá se a precisão dela sustenta a margem.

**Consequência:** o R-12 cai de probabilidade Alta para Média e segue aberto. O
P9 deixa de ser "quase certo"; a recomendação é não acioná-lo agora, mas decidir
com o orientador olhando as duas contas, não só o 53.

A medição revelou também o primeiro defeito do lexer que o P8 não mostrava —
decimal sem zero à esquerda (`*.3`, no P2) —, já corrigido com teste.

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

**14 riscos registrados.** Situação em 09/10/2026:

| Status | Riscos |
|---|---|
| **Resolvido** | R-02 (LLM na GPU de 6 GB), R-09 (poucos PBIP públicos) |
| **Mitigado** | R-06 (dados sensíveis), R-08 (dependências no Windows, parcial), R-11 (OneDrive), R-14 (disco C: cheio) |
| **Aberto** | R-01, R-03, R-04, R-05, R-07, R-10, R-12, R-13 |

### O que merece atenção agora

**R-12 — significância da avaliação** · P=**M**, I=**A** · ver seção 4.2.
Medido em 09/10/2026: 53 achados em P1–P7, acima do gatilho de ~40, e a
probabilidade caiu de Alta para Média. Segue aberto porque a margem depende da
PERF-003 — sem ela, 37.

**R-03 — falsos positivos em heurísticas de DAX** · P=Alta, I=M.
O risco se materializou no **grupo 2**, fechado nesta etapa, e ganhou uma
terceira mitigação por construção: `core/dax.py` é um lexer, não expressão
regular sobre texto bruto, com cobertura medida contra o P8 — 137 de 137
expressões tokenizadas sem token desconhecido, 105 de 105 em escopo sem lacuna.
O episódio da MOD-005, e depois o da PERF-005, mostram que a exigência de
âncora e o terceiro teste do critério de detectabilidade (seção 4.1) funcionam
mesmo sob incentivo para ignorá-los.

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
| 1 | **Decidir o P9 com o orientador** | O gatilho do R-12 não disparou (53 achados em P1–P7), mas sem a PERF-003 seriam 37. A decisão precisa das duas contas (seção 4.2) |
| 2 | Verificar empiricamente se o Power BI Desktop grava `roles[].tablePermissions[].filterExpression` no `model.bim` | Menos urgente do que antes: era a dependência da PERF-005, que foi recusada. Permanece pendência porque pode sustentar regra futura de RLS. Também vale para a DAX-001, que já consome o sítio `role` em produção hoje — mas sem o mesmo risco: ela afirma por **presença** do operador `/`, então sobre uma propriedade que o Desktop talvez nunca escreva ela simplesmente não encontra nada; o falso positivo destrutivo que motiva a pendência é risco de regra que afirma por **ausência**, como a PERF-005 teria sido |
| 3 | Iniciar a Fase 3: catálogo de fontes (`sources.yaml`) e coleta | Entregável da semana 6, que agora começa um roadmap-week depois do planejado (seção 2). As URLs canónicas das 9 regras já são, por construção, parte do catálogo que a RAG precisa conter |

---

## 9. Como verificar o que está aqui

```powershell
# clonar e preparar
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

pytest                            # 196 testes (os que leem o PBIP real são pulados sem data/)
python -m core.rules.catalogo     # as 9 regras com as URLs do Microsoft Learn
```

Os testes que leem o PBIP real são **pulados** automaticamente numa cópia limpa
do repositório, porque `data/` não é versionado — o PBIP contém o modelo de um
projeto real. São eles que travam as 15 ocorrências medidas, a cobertura do
lexer (137 de 137 expressões, zero desconhecida) e a cobertura da varredura de
DAX (105 de 105 em escopo, 0 lacunas).

**Repositório:** <https://github.com/FredLisboa77/PUC-RIO_TCC>
As 8 regras estruturais foram desenvolvidas na branch `fase2-motor-de-regras`,
já mergeada na `main` e preservada no remoto como registro do recorte daquela
etapa. O grupo 2 de DAX (lexer, varredura, resolução de uso e DAX-001) foi
desenvolvido na branch `fase2-regras-de-dax`, ainda não mergeada no momento
deste fechamento de documentos.
