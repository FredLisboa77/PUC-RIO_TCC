# Backlog e Controle de Escopo

Última atualização: 22/09/2026 (gate da Fase 1 aprovado).

## MVP aprovado
F01–F16, conforme a matriz em `fase1-viabilidade-e-planejamento.md`.

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

## Pendências abertas do gate da Fase 1
| ID | Pendência | Responsável | Prazo |
|---|---|---|---|
| G-2 | Salvar 1 PBIP real em TMSL e registrar `tree /F /A` no progress-log | Fred | Semana 1 |
| G-8 | Gerar `rag/sources.yaml` a partir dos `toc.json` | Semana 5 | Semana 5 |
| — | Instalar Ollama e rodar o spike de LLM | Fred | Semana 2 |
| — | Baixar os 7 PBIX do dataset e converter para PBIP | Fred | Semana 4 |
