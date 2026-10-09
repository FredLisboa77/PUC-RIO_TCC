# Dataset de avaliação

**Status:** P8 convertido (23/09/2026), agora como estudo de caso fora das métricas. **P1–P7 baixados em 09/10/2026** (passo 1 do procedimento abaixo) e **ainda não convertidos** — os passos 2–5 exigem a GUI do Power BI Desktop.
**Decisão de origem:** [ADR-005](../docs/adr/ADR-005-dataset-de-avaliacao.md).

## Origem

**P1–P7** vêm de **[microsoft/powerbi-desktop-samples](https://github.com/microsoft/powerbi-desktop-samples)**, licença **MIT** (confirmada via API do GitHub em 22/09/2026).

Usar amostras públicas em vez de projetos corporativos é uma decisão metodológica: a banca e qualquer leitor podem baixar exatamente os mesmos arquivos e repetir a avaliação.

**P8 não faz parte do dataset de métricas.** Por decisão de 29/09/2026 (ADR-005, segunda emenda), ele é tratado como **estudo de caso qualitativo** em seção própria — ver abaixo. Nenhuma métrica de precisão, recall, Precision@K ou MRR o inclui, o que dispensa a ressalva "apenas P1–P7" que antes teria de acompanhar todo número.

## Os 7 projetos do dataset

| PBIP_ID | Arquivo de origem | Pasta no repositório | Domínio |
|---|---|---|---|
| P1 | `AdventureWorks Sales.pbix` | `2026 Power BI Samples Revamp` | Vendas B2B / varejo |
| P2 | `Corporate Spend.pbix` | `2026 Power BI Samples Revamp` | Financeiro / despesas corporativas |
| P3 | `Employee Hiring and History.pbix` | `2026 Power BI Samples Revamp` | Recursos humanos |
| P4 | `Competitive Marketing Analysis.pbix` | `2026 Power BI Samples Revamp` | Marketing |
| P5 | `Store Sales.pbix` | `2026 Power BI Samples Revamp` | Varejo / loja física |
| P6 | `Supply Chain Sample.pbix` | `Sample Reports` | Cadeia de suprimentos |
| P7 | `Revenue Opportunities.pbix` | `Sample Reports` | Pipeline comercial / CRM |

P1–P5 vêm da revisão de 2026 e P6–P7 de amostras mais antigas. A mistura é proposital: modelos de épocas diferentes tendem a ter qualidade diferente, o que evita um dataset uniformemente bom ou uniformemente ruim.

## P8 — estudo de caso (fora das métricas)

Projeto construído pelo autor sobre o banco de exemplo público **ContosoRetailDW**, no domínio de varejo online. Convertido em 23/09/2026 e guardado em `data/pbip/P8_contoso-vendas/` (fora do Git). `definition.pbism` `version` **4.2**; `compatibilityLevel` **1600**.

**Papel no trabalho:** demonstrar a ferramenta em profundidade sobre um modelo real, em vez de somar um ponto às métricas. O achado central já identificado na primeira leitura é o **tempo automático ligado**: quatro tabelas de data geradas pelo Power BI (um `DateTableTemplate_*` e três `LocalDateTable_*`) convivendo com uma `DimCalendar` própria — uma delas gerada sobre a própria coluna de data da `DimCalendar`. O estudo de caso acompanha esse achado de ponta a ponta — detecção pela regra, trecho recuperado, explicação gerada, fonte citada e impacto no modelo.

O `.pbix` de origem **não** está em `data/pbix/`: com 174 MB e o disco C: sem espaço (ver R-14), ele permanece apenas na pasta original do autor. A ferramenta lê o PBIP, não o PBIX, então isso não afeta a avaliação.

| Objeto | Qtd |
|---|---|
| Tabelas | 19 |
| Medidas | 93 |
| Colunas | 106 (35 calculadas) |
| Relacionamentos | 11 |

**Mascaramento exigido pelo R-12 — verificado, nada a mascarar:**

- Única fonte externa: `Sql.Databases("localhost\")` → banco `ContosoRetailDW`. Sem host real, sem credenciais, sem caminho de arquivo.
- Varredura do PBIP inteiro por nome de usuário, `C:\Users`, `OneDrive`, e-mails e menções à instituição: **nenhuma ocorrência**.
- As colunas de pessoas (`DimCustomer`, `DimEmployee`) contêm dados sintéticos do Contoso, não pessoas reais.

Reverificar essa varredura se o PBIP for regerado.

## Procedimento de conversão (manual, fora do escopo do software)

Para cada PBIX, na semana 4:

1. Baixar o `.pbix` do repositório da Microsoft e salvar em `data/pbix/`.
2. Abrir no **Power BI Desktop**.
3. Confirmar que o preview **"Store semantic model using TMDL format" está DESLIGADO** em *Arquivo > Opções e configurações > Opções > Recursos de visualização*. Isso é obrigatório: a conversão para TMDL é irreversível (ADR-001).
4. *Arquivo > Salvar como > Projeto do Power BI (.pbip)*, salvando em `data/pbip/P<n>_<nome>/`.
5. Conferir que a pasta `<nome>.SemanticModel/` contém **`model.bim`** e **não** contém a pasta `definition/`.
6. Registrar no `progress-log.md`: PBIP_ID, nome do arquivo, `version` lida no `definition.pbism`, e o número de tabelas e medidas.

### Download de P1–P7 — feito em 09/10/2026

Os sete `.pbix` foram baixados de `raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main`
para `data/pbix/`, nomeados `P<n>_<arquivo original>.pbix`. Todos conferidos: assinatura ZIP
(`50 4b 03 04`) e tamanho idêntico ao que a API do GitHub informa para o commit de `main`.

| PBIP_ID | Caminho no repositório | Tamanho |
|---|---|---|
| P1 | `2026 Power BI Samples Revamp/AdventureWorks Sales.pbix` | 8,4 MB |
| P2 | `2026 Power BI Samples Revamp/Corporate Spend.pbix` | 0,7 MB |
| P3 | `2026 Power BI Samples Revamp/Employee Hiring and History.pbix` | 8,5 MB |
| P4 | `2026 Power BI Samples Revamp/Competitive Marketing Analysis.pbix` | 6,6 MB |
| P5 | `2026 Power BI Samples Revamp/Store Sales.pbix` | 9,7 MB |
| P6 | `Sample Reports/Supply Chain Sample.pbix` | 1,2 MB |
| P7 | `Sample Reports/Revenue Opportunities.pbix` | 7,5 MB |

**Armadilha de nome, registrada para reprodutibilidade:** **seis dos sete** nomes aparecem
em mais de uma pasta do repositório, com conteúdos diferentes — só `Supply Chain Sample.pbix`
é único. `Revenue Opportunities.pbix` é o caso extremo, em quatro pastas: 7.465.671 bytes em
`Sample Reports` contra 245.930 em `2026 Power BI Samples Revamp` e 247.054 em
`new-power-bi-service-samples` e `powerbi-service-samples` — 30 vezes menor. A coluna "Caminho no repositório" acima, não o nome do
arquivo, é o que identifica cada projeto. A tabela dos 7 projetos já fixava a pasta de cada
um, e foi ela que decidiu qual baixar.

**Por que os passos 2–5 não podem ser automatizados.** Verificado nos arquivos baixados: o
modelo semântico de um `.pbix` vive numa única entrada `DataModel` do ZIP — um ABF comprimido,
não um `model.bim`. Nenhuma leitura do `.pbix` produz o PBIP; só o Desktop o escreve. (A camada
de relatório, ao contrário, está em claro: P1–P5 já trazem `Report/definition/pages/`, o
formato PBIR novo, e P6–P7 o `Report/Layout` antigo.)

Power BI Desktop confirmado instalado nesta máquina: versão da Store **2.158.1304.0**. O ajuste
do passo 3 (preview de TMDL desligado) **não é verificável por fora** — não aparece no hive de
registro virtualizado do app da Store —, então a conferência visual do passo 3 é obrigatória, e
não uma formalidade: a conversão para TMDL é irreversível (ADR-001).

### Conversão de P1–P7 — feita em 09/10/2026

Convertidos pelo autor no Desktop 2.158 e guardados em `data/pbip/P<n>_<nome>/`. Conferido nos
sete: `model.bim` presente, pasta `definition/` ausente. Ao salvar, o Desktop gravou os sete
relatórios em PBIR — inclusive P6–P7, que no `.pbix` estavam no `Report/Layout` antigo.

| PBIP_ID | `version` | `compatibilityLevel` | Tabelas | Medidas |
|---|---|---|---|---|
| P1 | 4.2 | 1606 | 10 | 20 |
| P2 | 4.2 | 1606 | 10 | 19 |
| P3 | 4.2 | 1606 | 9 | 25 |
| P4 | 4.2 | 1606 | 9 | 22 |
| P5 | 4.2 | 1606 | 7 | 32 |
| P6 | 4.2 | 1606 | 7 | 4 |
| P7 | 4.2 | 1606 | 7 | 4 |

`data/` está no `.gitignore`. Os arquivos não são versionados — este documento é o que torna o dataset reprodutível.

## Ground truth

Construído manualmente na **semana 8**, antes de ver os resultados finais da ferramenta (risco R-04).

Formato de `eval/ground_truth.csv`:

```
PBIP_ID | DOMINIO | PROBLEMA | CATEGORIA | SEVERIDADE | JUSTIFICATIVA | REFERENCIA
```

Regras de construção:

- **Não fabricar problemas.** Só entra no ground truth o que existe de fato no modelo.
- Cada linha precisa de uma `REFERENCIA` — a URL da página que sustenta que aquilo é um problema.
- `CATEGORIA` ∈ {DAX, M, MODELAGEM, PERFORMANCE}.
- `SEVERIDADE` ∈ {ALTA, MEDIA, BAIXA}.

## Contingência

Com o P8 fora das métricas, o **risco R-12 volta a Aberto**: o dataset depende de amostras da Microsoft que podem ter poucos problemas. Se na semana 4 o total de achados em P1–P7 ficar abaixo de ~40, acrescentar **1 PBIX próprio como P9**, repetindo a verificação de privacidade aplicada ao P8 antes de qualquer commit. Diferente do P8, o P9 entraria no dataset de métricas, e aí a ressalva "apenas P1–P7" voltaria a ser necessária — razão para só recorrer a ele se o gatilho de fato disparar.
