# ADR-003 — Orquestração sequencial e detecção híbrida

- **Status:** Proposta
- **Data:** 22/09/2026

## Decisão
1. A auditoria é uma função `run_audit()` que executa em ordem: ingestão → parsing → regras → recuperação → geração → validação da citação → relatório. Não há multiagente.
2. **As regras determinísticas são a única fonte de achados.** O LLM só explica e recomenda, e precisa citar um trecho recuperado. Se a citação não estiver entre os trechos recuperados, a resposta é descartada e o achado sai com a recomendação padrão da regra e a marca "sem fundamentação gerada".

## Justificativas
- Precisão e recall dos achados passam a ser determinísticos e reprodutíveis, o que dá validade acadêmica à avaliação.
- O pipeline é linear; um framework de agentes não traria ganho demonstrável.
- A validação da citação reduz alucinação de forma mensurável (taxa de citações válidas vira métrica).

## Revisão
Reavaliar só se a Fase 3 mostrar uma necessidade que o fluxo sequencial não atende. Caso contrário, multiagente continua em Trabalhos Futuros.
