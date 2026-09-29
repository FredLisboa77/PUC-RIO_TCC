# Backlog e Controle de Escopo

Última atualização: 29/09/2026 (critério de seleção de regras; P8 como estudo de caso).

## MVP aprovado
F01–F16, conforme a matriz em `fase1-viabilidade-e-planejamento.md`.

## Critério de seleção de regras — decidido em 29/09/2026

A meta continua sendo **20 a 25 regras**, mas a escolha de *quais* regras implementar deixa de ser por cota fixa por categoria e passa a seguir a **detectabilidade**: entram primeiro as regras cujo problema pode ser identificado de forma confiável a partir do `model.bim`, porque são as que produzem auditoria de valor real e menos falsos positivos.

Ordem de prioridade que isso implica:

1. **Regras estruturais** (modelagem e performance estática) — leem propriedades explícitas do JSON: relacionamentos bidirecionais, tabelas de data automáticas, colunas calculadas, tipos de dados, colunas sem uso, cardinalidade inferida. A detecção é praticamente determinística e o falso positivo é raro.
2. **Regras de DAX com padrão textual inequívoco** — divisão com `/` em vez de `DIVIDE`, `FILTER` sobre tabela inteira, iteração desnecessária. O padrão é reconhecível por expressão regular sem interpretar semântica.
3. **Regras de DAX dependentes de contexto** — transição de contexto, `CALCULATE` aninhado, escopo de variáveis. Entram apenas se sobrar orçamento, porque sem um parser sintático a heurística erra com frequência.
4. **Regras de M** — mantidas no MVP, mas são as primeiras a ser cortadas sob pressão de prazo (R-07).

Consequência prática: se a contagem final ficar perto de 20 em vez de 25, a diferença sai do grupo 3, não do grupo 1. Uma regra com precisão baixa é pior que uma regra ausente, porque mina a confiança no relatório inteiro.

## Trabalhos Futuros
| ID | Item | Motivo da exclusão |
|---|---|---|
| F17 | Suporte a TMDL | Sem parser Python oficial; formato ainda em preview (ADR-001) |
| F18 | Parser DAX completo (AST) | Complexidade alta para o prazo de 180 h |
| F19 | Camada de relatório (PBIR, visuais, páginas) | Fora do escopo do MVP |
| F20 | Reranking e busca híbrida BM25 | Fora do escopo do MVP |
| F21 | Correção automática / geração de PBIP corrigido | Fora do escopo do MVP |
| F22 | Framework multiagente | ADR-003 |
| F23 | Métricas em runtime (VertiPaq, DAX Studio, XMLA) | Fora do escopo do MVP |
| F24 | Entrada em PBIX e conversão automática | Fora do escopo do MVP |

## Log de alertas de escopo
| Data | Sugestão | Decisão |
|---|---|---|
| 22/09/2026 | Executar o BPA do Tabular Editor via CLI em vez de reescrever as regras | **Recusado.** Adiciona dependência .NET e o repositório de regras não tem licença (R-10). Regras próprias em Python, ancoradas no Learn |
| 22/09/2026 | Trocar `bge-small-en` por um modelo multilíngue para lidar com saída em português | **Recusado.** Consulta em inglês + saída em português resolve sem trocar para um modelo de ~2 GB (ADR-002, C-6) |
| 29/09/2026 | Manter o P8 dentro do dataset de métricas | **Recusado.** Vira estudo de caso qualitativo: as métricas ficam 100% reprodutíveis e o P8 rende mais em profundidade que como oitavo ponto amostral (ADR-005, 2ª emenda) |
| 29/09/2026 | Fixar cota de regras por categoria (8 DAX, 4 M, 6 modelagem, 5 performance) | **Substituído** pelo critério de detectabilidade acima. A cota otimizava contagem; o critério otimiza qualidade do achado |

## Pendências abertas do gate da Fase 1
| ID | Pendência | Responsável | Prazo |
|---|---|---|---|
| G-2 | ~~Salvar 1 PBIP real em TMSL e registrar `tree /F /A` no progress-log~~ | Fred | **Concluído em 23/09/2026** |
| G-8 | Gerar `rag/sources.yaml` a partir dos `toc.json` | Semana 5 | Semana 5 |
| — | ~~Instalar Ollama e rodar o spike de LLM~~ | Fred | **Concluído em 29/09/2026** — 7B aprovado, ADR-006 descartada |
| — | Baixar os 7 PBIX do dataset e converter para PBIP | Fred | Semana 4 |
| — | Detalhar as limitações declaradas (heurísticas vs. parser DAX; performance estática vs. medida) no capítulo de metodologia | Fred | Semana 12 |
| — | Escrever o estudo de caso do P8 | Fred | Semana 12 |
