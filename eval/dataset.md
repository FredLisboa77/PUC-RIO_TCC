# Dataset de avaliação

**Status:** PLANEJADO — os arquivos ainda não foram baixados nem convertidos.
**Decisão de origem:** [ADR-005](../docs/adr/ADR-005-dataset-de-avaliacao.md).

## Origem

Todos os PBIX vêm de **[microsoft/powerbi-desktop-samples](https://github.com/microsoft/powerbi-desktop-samples)**, licença **MIT** (confirmada via API do GitHub em 22/09/2026).

Usar amostras públicas em vez de projetos corporativos é uma decisão metodológica: a banca e qualquer leitor podem baixar exatamente os mesmos arquivos e repetir a avaliação.

## Os 7 projetos

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

Se na semana 4 o total de achados no dataset inteiro ficar abaixo de ~40, as amostras da Microsoft são limpas demais para uma avaliação significativa. Nesse caso, acrescentar 1 ou 2 PBIX próprios como P8/P9, com caminhos e strings de conexão mascarados antes de qualquer commit (risco R-12).
