# ADR-005 — Dataset de avaliação: amostras públicas da Microsoft

- **Status:** Aceita
- **Data:** 22/09/2026

## Contexto
A avaliação precisa de 5 a 8 projetos PBIP de domínios de negócio diferentes. Havia duas opções: usar PBIX próprios (já disponíveis) ou usar amostras públicas. O desenvolvedor optou pelas amostras públicas.

## Decisão
Usar os PBIX públicos do repositório **`microsoft/powerbi-desktop-samples`** (licença **MIT**, confirmada via API do GitHub em 22/09/2026), convertidos manualmente para PBIP em formato TMSL (`model.bim`).

### Dataset proposto — 7 projetos, 7 domínios
| PBIP_ID | Arquivo de origem | Pasta no repositório | Domínio |
|---|---|---|---|
| P1 | `AdventureWorks Sales.pbix` | `2026 Power BI Samples Revamp` | Vendas B2B / varejo |
| P2 | `Corporate Spend.pbix` | `2026 Power BI Samples Revamp` | Financeiro / despesas corporativas |
| P3 | `Employee Hiring and History.pbix` | `2026 Power BI Samples Revamp` | Recursos humanos |
| P4 | `Competitive Marketing Analysis.pbix` | `2026 Power BI Samples Revamp` | Marketing |
| P5 | `Store Sales.pbix` | `2026 Power BI Samples Revamp` | Varejo / loja física |
| P6 | `Supply Chain Sample.pbix` | `Sample Reports` | Cadeia de suprimentos |
| P7 | `Revenue Opportunities.pbix` | `Sample Reports` | Pipeline comercial / CRM |

P1 a P5 vêm da revisão de 2026 e P6 a P7 de amostras mais antigas. Essa mistura é proposital: modelos de épocas diferentes tendem a ter qualidade diferente, o que evita um dataset uniformemente bom ou uniformemente ruim.

## Justificativas
1. **Licença MIT**: permite uso, cópia e redistribuição com atribuição. Elimina o risco R-06 de dados sensíveis (não há string de conexão corporativa nem caminho local de cliente).
2. **Reprodutibilidade acadêmica**: a banca e qualquer leitor podem baixar exatamente os mesmos arquivos e repetir a avaliação. Um dataset privado tornaria os números não verificáveis.
3. **Variedade de domínios** confirmada por inspeção do repositório, não presumida.
4. Serve ao mesmo tempo como dataset de avaliação e como base da demonstração pública de 15 minutos.

## Consequências
- (+) A avaliação passa a ser reprodutível por terceiros — ganho direto de validade acadêmica.
- (+) O `data/` pode, em princípio, ser versionado; mesmo assim permanece no `.gitignore`, porque os PBIX pesam de 0,7 a 9,5 MB cada e o `eval/dataset.md` registra a origem exata, o que basta para reproduzir.
- (−) Amostras da Microsoft podem ter menos problemas graves que um modelo corporativo real, o que pode reduzir o número de achados. **Mitigação:** se na semana 4 o total de achados do dataset ficar baixo demais para uma avaliação significativa, acrescentar 1 ou 2 PBIX próprios do desenvolvedor como P8/P9, com os caminhos e as conexões mascarados.
- (−) O ground truth precisa ser construído do zero sobre modelos que o desenvolvedor não escreveu, o que exige mais tempo de leitura na semana 8.

## Não decidido aqui
A conversão PBIX → PBIP continua manual e fora do escopo do software (Arquivo > Salvar como > Projeto do Power BI, com o preview de TMDL **desligado**).
