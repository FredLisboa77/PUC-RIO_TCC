# ADR-001 — Formato do modelo semântico: model.bim (TMSL)

- **Status:** Aceita (gate da Fase 1 aprovado em 22/09/2026)
- **Data:** 22/09/2026

## Contexto
O MVP suporta um único formato de modelo semântico dentro do PBIP: TMDL (pasta `definition/`) ou TMSL (`model.bim`). O parser precisa ser confiável e caber em ~2 semanas de trabalho de um desenvolvedor iniciante em Python/IA.

## Decisão
Usar **model.bim (TMSL/JSON)**. Todos os PBIP do dataset serão salvos com o recurso de preview "Store semantic model using TMDL format" **desligado**.

## Justificativas
1. Leitura com `json.load()` da biblioteca padrão, sem dependências.
2. Segundo o Microsoft Learn (página atualizada em 30/05/2026), salvar PBIP em TMDL **ainda está em preview**, e a conversão para TMDL é **irreversível**.
3. Não há parser TMDL oficial em Python. O parser da Microsoft (`microsoft/tmdl-parser`) atende à extensão do VS Code; a alternativa no PyPI é pequena e não testada.
4. Escrever um parser TMDL robusto (indentação, expressões multilinha) consumiria de 2 a 3 semanas do orçamento de 180 h.

## Consequências
- (+) Menor risco técnico na Fase 2.
- (−) Diffs e leitura humana piores; o JSON guarda DAX e M às vezes como string e às vezes como lista de linhas → o parser deve normalizar os dois casos.
- (−) Se a Microsoft tornar o TMDL padrão durante o projeto, será preciso manter o preview desligado (risco R-01).
- O parser fica atrás da interface `load_model(path)`, deixando o TMDL como Trabalho Futuro sem reescrever as regras.

## Validação documental (22/09/2026) — VALIDADO
Conferido contra [Microsoft Learn — Power BI Desktop project semantic model folder](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset), página atualizada em 30/05/2026:

- `definition.pbism` versão **1.0** → definição deve estar em TMSL (`model.bim`); versão **4.0 ou superior** → TMSL **ou** TMDL. Confirmado, é tabela literal da página.
- `model.bim` só existe quando o projeto é salvo em TMSL; a pasta `definition\` só existe quando é salvo em TMDL. Confirmado.
- Salvar em TMDL continua em **preview**: "Saving as a Power BI Project using TMDL is currently in preview". Confirmado.
- Conversão irreversível: "Once you upgrade to TMDL, you can't revert back to TMSL". Confirmado.
- `.pbi\cache.abf` contém dados do modelo e é ignorado pelo Git por padrão. Confirmado.
- **Fato adicional para o capítulo de Limitações:** o recurso *Power BI Desktop projects* inteiro ainda está em preview, não apenas o TMDL.

## Validação prática pendente
Salvar 1 PBIP real, confirmar a presença de `model.bim` e a `version` do `definition.pbism`, e registrar a saída de `tree /F /A` no progress-log.
