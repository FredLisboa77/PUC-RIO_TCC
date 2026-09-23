# Dataset de avaliação

**Status:** P8 convertido (23/09/2026). P1–P7 ainda não baixados nem convertidos.
**Decisão de origem:** [ADR-005](../docs/adr/ADR-005-dataset-de-avaliacao.md).

## Origem

**P1–P7** vêm de **[microsoft/powerbi-desktop-samples](https://github.com/microsoft/powerbi-desktop-samples)**, licença **MIT** (confirmada via API do GitHub em 22/09/2026).

Usar amostras públicas em vez de projetos corporativos é uma decisão metodológica: a banca e qualquer leitor podem baixar exatamente os mesmos arquivos e repetir a avaliação.

**P8** é a exceção deliberada: um projeto construído pelo autor sobre o banco de exemplo público **ContosoRetailDW**. Entrou no dataset porque modelos de amostra da Microsoft tendem a ser limpos demais (risco R-12), enquanto P8 já apresenta problemas reais de modelagem na primeira leitura. Não é reprodutível por terceiros, e por isso **nunca sustenta sozinho uma conclusão** — toda métrica reportada deve aparecer também na forma "apenas P1–P7".

## Os 8 projetos

| PBIP_ID | Arquivo de origem | Pasta no repositório | Domínio |
|---|---|---|---|
| P1 | `AdventureWorks Sales.pbix` | `2026 Power BI Samples Revamp` | Vendas B2B / varejo |
| P2 | `Corporate Spend.pbix` | `2026 Power BI Samples Revamp` | Financeiro / despesas corporativas |
| P3 | `Employee Hiring and History.pbix` | `2026 Power BI Samples Revamp` | Recursos humanos |
| P4 | `Competitive Marketing Analysis.pbix` | `2026 Power BI Samples Revamp` | Marketing |
| P5 | `Store Sales.pbix` | `2026 Power BI Samples Revamp` | Varejo / loja física |
| P6 | `Supply Chain Sample.pbix` | `Sample Reports` | Cadeia de suprimentos |
| P7 | `Revenue Opportunities.pbix` | `Sample Reports` | Pipeline comercial / CRM |
| P8 | `CONTOSO - Painel de Análise de Vendas Online.pbix` | — (autoria própria, base ContosoRetailDW) | Varejo online |

P1–P5 vêm da revisão de 2026 e P6–P7 de amostras mais antigas. A mistura é proposital: modelos de épocas diferentes tendem a ter qualidade diferente, o que evita um dataset uniformemente bom ou uniformemente ruim.

### P8 — ficha e verificação de privacidade

Convertido em 23/09/2026 e guardado em `data/pbip/P8_contoso-vendas/` (fora do Git). `definition.pbism` `version` **4.2**; `compatibilityLevel` **1600**.

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

O slot P8 já foi usado (ver acima), antecipando a contingência do risco R-12. Se na semana 4 o total de achados no dataset inteiro ainda ficar abaixo de ~40, acrescentar **1 PBIX próprio como P9**, repetindo a mesma verificação de privacidade aplicada ao P8 antes de qualquer commit.
