# Backlog e Controle de Escopo

Última atualização: 08/10/2026 (fechamento da Fase 2: D-1 — contagem de regras passa a resultado —, âncora da DAX-001 transcrita, DAX-002 e DAX-003 registradas como candidatas, F25 em Trabalhos Futuros).

## MVP aprovado
F01–F16, conforme a matriz em `fase1-viabilidade-e-planejamento.md`.

## Critério de seleção de regras — decidido em 29/09/2026

A meta era **20 a 25 regras** (revisado por D-1 em 08/10/2026, abaixo — a contagem final deixou de ser meta), mas a escolha de *quais* regras implementar deixa de ser por cota fixa por categoria e passa a seguir a **detectabilidade**: entram primeiro as regras cujo problema pode ser identificado de forma confiável a partir do `model.bim`, porque são as que produzem auditoria de valor real e menos falsos positivos.

Ordem de prioridade que isso implica:

1. **Regras estruturais** (modelagem e performance estática) — leem propriedades explícitas do JSON: relacionamentos bidirecionais, tabelas de data automáticas, colunas calculadas, tipos de dados, colunas sem uso, cardinalidade inferida. A detecção é praticamente determinística e o falso positivo é raro.
2. **Regras de DAX com padrão textual inequívoco** — divisão com `/` em vez de `DIVIDE`, `FILTER` sobre tabela inteira, iteração desnecessária. O padrão é reconhecível por expressão regular sem interpretar semântica.
3. **Regras de DAX dependentes de contexto** — transição de contexto, `CALCULATE` aninhado, escopo de variáveis. Entram apenas se sobrar orçamento, porque sem um parser sintático a heurística erra com frequência.
4. **Regras de M** — mantidas no MVP, mas são as primeiras a ser cortadas sob pressão de prazo (R-07).

Consequência prática: se a contagem final ficar perto de 20 em vez de 25, a diferença sai do grupo 3, não do grupo 1. Uma regra com precisão baixa é pior que uma regra ausente, porque mina a confiança no relatório inteiro.

## Âncora verificada antes do código — decidido em 06/10/2026

Acrescenta-se ao critério acima uma segunda condição, anterior à detectabilidade: **uma regra só entra se existir passagem citável do Microsoft Learn que a sustente**, lida e transcrita antes de qualquer código. Sem isso a regra não pode cumprir a ADR-003, que obriga o LLM a fundamentar cada achado num trecho recuperado.

A regra nasceu do custo evitado: ao desenhar as oito regras estruturais, conferir as âncoras consumiu a leitura de cinco páginas e **eliminou três das nove regras propostas** — uma delas porque a página que a sustentaria recomendava justamente o que a regra marcaria como defeito. Verificar depois teria custado o código das três.

Decorre daí um subproduto: as URLs canónicas das regras são, por construção, as páginas que o `rag/sources.yaml` precisa conter (G-8, semana 5). O catálogo de regras alimenta o catálogo de fontes.

## Terceiro teste do critério de detectabilidade — primeiro caso de rejeição, decidido em 08/10/2026

A etapa de 08/10/2026 formulou um terceiro teste para o critério de detectabilidade (spec `docs/superpowers/specs/2026-10-08-regras-de-dax-e-varredura-textual-design.md`, seção 3): suficiência da evidência, em três cláusulas — (a) todas as formas da condição, (b) todos os sósias do sinal, (c) todos os sítios onde o sinal pode morar. Afirmação por ausência exige as três completas.

A MOD-005 (06/10) foi o caso que motivou o teste: passava nos dois critérios anteriores e ainda assim marcaria uma dimensão corretamente configurada como defeito. Ali o teste **corrigiu** a regra — ela sobreviveu, reescrita.

A PERF-005 é o segundo caso em que o terceiro teste muda o resultado, e o primeiro em que o resultado é **rejeição**, não correção. Era a regra de maior rendimento esperado da etapa, com âncora já transcrita dois dias antes (ver abaixo); a cláusula (c) a derrubou mesmo com esse incentivo para ignorá-la — o critério se provou sobre o caso em que custava mais caro aplicá-lo.

## D-1 — a contagem de 20–25 regras deixa de ser meta e passa a ser resultado, decidido em 08/10/2026

A meta de "20 a 25 regras determinísticas" vem do planejamento da Fase 1 (`fase1-viabilidade-e-planejamento.md`, entregável do F2) e, até 29/09/2026, de uma cota fixa por categoria — 8 DAX, 4 M, 6 modelagem, 5 performance, que somava 23. Essa cota foi substituída pelo critério de detectabilidade no próprio 29/09, e as duas exigências que entraram depois — âncora citável verificada antes do código (06/10) e o terceiro teste de suficiência de evidência (acima, 08/10) — cortaram mais do que a cota teria cortado: a verificação de âncora de 06/10 trocou três candidatas estruturais sem passagem citável por duas novas que a tinham (MOD-006, MOD-007), chegando às **8** regras estruturais que valem hoje; do grupo 2, só a DAX-001 entrou — a PERF-005 foi recusada antes do código e a DAX-002 segue sem âncora verificada.

**A aritmética, por componente, sem somar um total que o projeto ainda não pode calcular:** mantendo as duas exigências, e sem abrir o grupo 3 (DAX dependente de contexto, onde a heurística erra sem parser sintático) nem afrouxar a exigência de âncora — o que já está fechado é **8** regras no grupo 1 e **1** no grupo 2 (DAX-001); o que falta decidir é, no máximo, mais **1** no grupo 2 (DAX-002, se a âncora verificar — a DAX-003 já saiu, adiada por zero ocorrência no P8), mais o que o **grupo 4** (regras de M) render — e esse grupo ainda não foi atacado, então não há hoje base para apontar quantas regras ele soma, nem portanto um total único para o conjunto. Fosse o grupo 4 generoso, o cenário otimista poderia se aproximar de 20; não sendo, fica bem abaixo. É precisamente por não poder somar esse total com confiança que a contagem final deixa de ser uma meta numérica a perseguir. Chegar a 20–25 com certeza exigiria uma das duas alternativas que o projeto já recusou, em 29/09 e 06/10: aceitar o grupo 3, ou relaxar a exigência de âncora.

**Decisão:** a contagem final deixa de ser **meta** e passa a ser **resultado** do método. A monografia defende o conjunto menor — hoje 9 regras — e usa as regras descartadas (candidatas abaixo e o log de alertas) como evidência do próprio método, não como déficit a desculpar. Uma regra ausente por falta de âncora ou de evidência suficiente é um resultado do critério funcionando, não uma lacuna de esforço.

## Âncora da DAX-001 — verificada e transcrita em 08/10/2026 (Tarefa 8)

**URL canônica:** <https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator> — *DIVIDE function vs divide operator (/) in DAX*, página de boas práticas do Microsoft Learn, `ms.date` 25/08/2021, revisada em 13/01/2026. **Acesso em 08/10/2026.** A URL de `power-bi/guidance/` que a sondagem inicial usara não é a canônica — a página canonicaliza para `/dax/best-practices/`.

Passagens transcritas:

> "It's recommended that you use the DIVIDE function whenever the denominator is an expression that could return zero or BLANK."

> "In the case that the denominator is a constant value, we recommend that you use the divide operator. In this case, the division is guaranteed to succeed, and your expression will perform better because it will avoid unnecessary testing."

**A verificação mudou a regra, e por pouco não a derrubou.** O enunciado original — "divisão com `/` em vez de `DIVIDE`" — marcaria como defeito o que a própria página **recomenda** quando o denominador é constante: o mesmo erro que derrubou a PERF-004 em 06/10, reaberto por outra porta. A regra que entrou no código afirma apenas sobre denominador **não constante**, condição que as duas passagens acima sustentam juntas.

## Revisão contra a literatura — melhorias registradas em 09/10/2026

Revisão do projeto inteiro contra a literatura de análise estática, avaliação, RAG e
engenharia de software. Os três pontos de risco já têm resposta registrada:
contaminação do ground truth (`eval/dataset.md`, R-04), recuperação ancorada e conjunto
de avaliação da recuperação (ADR-002, emenda de 09/10). As melhorias de custo baixo
ficam aqui, para entrar quando a etapa correspondente chegar:

| Melhoria | Quando | Base |
|---|---|---|
| Integração contínua: `pytest` a cada push e em todo PR, mais um linter (`ruff`) | Antes de integrar o PR #1, ou logo depois | Prática padrão; hoje o repositório não tem CI |
| Precisão por regra com intervalo de confiança de Wilson, e por categoria, em vez de um número único | Fase 5 (semana 11) | Wilson (1927); n = 7 projetos |
| Fidelidade das explicações: numa amostra, conferir se a citação sustenta o que o texto afirma, além de existir entre os trechos | Fase 5, na rubrica | Gao et al. (2023), ALCE; Es et al. (2023), RAGAS |
| Situar o gatilho de precisão do R-03 (0,7) diante da referência industrial de menos de 10% de falsos positivos efetivos | Monografia, capítulo de avaliação | Sadowski et al. (2018), CACM |
| Completar `eval/dataset.md` como *datasheet*: motivação, composição, processo de coleta, licenças, usos não recomendados | Semana 8, junto com o ground truth | Gebru et al. (2021), *Datasheets for Datasets* |
| Testes gerados por propriedades no lexer de DAX e na resolução de URL | Quando um dos dois for mexido de novo | MacIver et al. (2019), Hypothesis |
| Recoleta com cache HTTP (`ETag`/`If-None-Match`), baixando só o que mudou | Trabalho futuro da coleta | RFC 9111 |

## Candidatas a regra — registradas, não implementadas

| Candidata | Âncora | Situação |
|---|---|---|
| **Relacionamento entre tipos diferentes** (ex-MOD-004) | Nenhuma encontrada em `desktop-create-and-manage-relationships` nem em `desktop-data-types` | Bloqueada por duas perguntas: existe passagem citável? E o Desktop permite criar esse relacionamento, ou valida os tipos e torna a condição inexistente em modelo real? |
| **Tabela calculada em DAX** (ex-PERF-004) | Contra-indicada: `guidance/auto-date-time` recomenda `CALENDAR`/`CALENDARAUTO` | Descartada, não adiada. Só voltaria numa forma estreita que exclua tabelas de data, e aí não sobra achado em P8 |
| **Chave substituta órfã sem uso** (forma estreita da PERF-005, recusada em 08/10) | A mesma `guidance/import-modeling-data-reduction` — a reverificar: a passagem transcrita justifica a coluna por servir ao **relatório ou** à estrutura, e uma forma estreita que só afirme sobre o segundo propósito precisa de passagem própria, ainda não encontrada | Bloqueada por duas perguntas: existe passagem citável para a forma estreita? E existe predicado **estrutural** que separe chave substituta de atributo comum sem recorrer a convenção de nome (`Key`/`ID`), que o projeto recusou em 06/10 por falta de âncora (R-10)? Sem as duas, a regra não entra |
| **DAX-002 — Iteração desnecessária** | A verificar — sem passagem citável, a regra não entra, pela mesma exigência de 06/10 | Não implementada nesta etapa, por decisão informada e não por falta de verificação: das 6 ocorrências de `SUMX` em escopo no P8, **zero** são iteração desnecessária — todas multiplicam duas colunas linha a linha (uma soma um termo antes de multiplicar), nenhuma substituível por `SUM` sobre uma coluna só (medido em 08/10/2026, Tarefa 9). O número não decide a favor nem contra a regra; diz apenas que o P8 não a exerceria. Fica como candidata, aguardando âncora |
| **DAX-003 — `FILTER` sobre tabela inteira** | Ainda a verificar | **Adiada** (D-8, spec de 08/10/2026). Zero ocorrência de `FILTER` nas 105 expressões em escopo do P8 — sem teste de regressão real contra arquivo e sem evidência para a monografia. Permanece candidata registrada, a decidir quando P1–P7 existirem |
| **Conversão de texto em número sem cultura** (grupo 4, M; registrada em 09/10/2026) | A verificar — procurar no Learn a passagem sobre o argumento `culture` de `Number.FromText`/`Table.TransformColumnTypes` e sobre a "localidade para importação" | Não é questão de sintaxe: o DAX e o M são gravados em notação invariável (medido em 09/10/2026 com um modelo pt-BR). O risco é em tempo de execução — o mesmo texto `"10,5"` vira número diferente conforme a cultura de quem atualiza. Antes da âncora, falta a pergunta de detectabilidade: a conversão sem cultura é visível no texto M, mas se o dado de origem é textual ou já numérico depende da fonte, que a ferramenta não lê |

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
| F25 | Recusar-se a declarar o grupo de DAX completo enquanto houver lacuna aberta (`lacunas_de_expressao`) | D-7 (spec de 08/10/2026): projeto acadêmico, avisar a lacuna no resultado já basta. Interromper a auditoria por lacuna exigiria lógica de bloqueio fora do MVP, e nenhum corpus do dataset hoje exerce lacuna real para desenhar o refinamento contra arquivo observado |

## Log de alertas de escopo
| Data | Sugestão | Decisão |
|---|---|---|
| 22/09/2026 | Executar o BPA do Tabular Editor via CLI em vez de reescrever as regras | **Recusado.** Adiciona dependência .NET e o repositório de regras não tem licença (R-10). Regras próprias em Python, ancoradas no Learn |
| 22/09/2026 | Trocar `bge-small-en` por um modelo multilíngue para lidar com saída em português | **Recusado.** Consulta em inglês + saída em português resolve sem trocar para um modelo de ~2 GB (ADR-002, C-6) |
| 29/09/2026 | Manter o P8 dentro do dataset de métricas | **Recusado.** Vira estudo de caso qualitativo: as métricas ficam 100% reprodutíveis e o P8 rende mais em profundidade que como oitavo ponto amostral (ADR-005, 2ª emenda) |
| 29/09/2026 | Fixar cota de regras por categoria (8 DAX, 4 M, 6 modelagem, 5 performance) | **Substituído** pelo critério de detectabilidade acima. A cota otimizava contagem; o critério otimiza qualidade do achado |
| 06/10/2026 | Manter a regra de coluna-chave agregável, com heurística de sufixo `Key`/`ID` | **Recusada.** Sem passagem citável no Learn; a frase próxima é contextual a outro exemplo; a origem é o BPA, recusado por licença (R-10). A variante estrutural dá zero em P8. Os objetos voltam como candidata "coluna sem uso" |
| 06/10/2026 | Manter a regra de tabela calculada em DAX | **Recusada.** A página que a sustentaria recomenda tabelas de data em `CALENDAR`/`CALENDARAUTO`. Em P8, 100% dos seus achados seriam refutados pela fonte citada |
| 06/10/2026 | Manter a regra de relacionamento entre tipos diferentes | **Adiada.** Sem âncora, e com dúvida sobre o produto permitir criar a condição. Fica como candidata com duas perguntas a resolver |
| 06/10/2026 | Reduzir a severidade de PERF-004 em vez de descartá-la | **Recusada.** Severidade baixa não resolve achado que a fonte contradiz: o problema não é importância, é fundamento |
| 08/10/2026 | Implementar a candidata "coluna sem uso" como PERF-005 | **Recusada.** A âncora justifica a coluna por servir ao relatório **ou** à estrutura do modelo, e a camada de relatório é o F19, que a ferramenta não lê — então a regra afirma ausência sobre domínio que não observa, violando a cláusula (c) do terceiro teste. Medido no P8: 33 achados (36 sem uso estrutural, menos 3 geradas por agrupamento/análise), dos quais 5 são defensáveis, 3 são colunas de calendário que a documentação recomenda (falso positivo confirmado) e 25 são atributos reportáveis cujo uso depende da camada de relatório, que a ferramenta não lê. **Precisão indeterminável** dentro do MVP — entre ~15% (5/33, se os 25 estiverem em uso) e ~91% (30/33, no outro extremo) —, contra o gatilho de 0,7 do R-03. A resolução de uso (`core/rules/referencias.py`) **fica** como evidência reproduzível da medição e para uso de regra futura |
| 09/10/2026 | Acionar o slot P9 (PBIX próprio) por precaução, dado que sem a PERF-003 P1–P7 somariam 37 | **Recusado** pelo Fred. O gatilho foi definido sobre contagem (ADR-005) e a contagem medida é **53**; o dataset de métricas fica P1–P7. A dependência da PERF-003 fica declarada, e o ground truth da semana 8 julga a precisão dela |
| 09/10/2026 | Ampliar o corpus da RAG de ~60–120 documentos para as referências completas de DAX e de M | **Aceito** pelo Fred. O catálogo passa a 1.420 páginas do Learn (guidance inteiro, 508 de DAX, 768 de M, mais as âncoras das regras). O texto indexado segue em inglês (ADR-002 inalterado); cada entrada leva `url_pt_br`, conferida no retrato pt-BR, para o leitor do relatório |
| 09/10/2026 | Indexar todos os artigos públicos do SQLBI | **Recusado** em favor de leitura complementar só com link. O site é de todos os direitos reservados, os termos não concedem uso dos artigos, e a Lei 9.610/98 (art. 46) cobre citação de passagens e cópia de pequenos trechos, não o armazenamento de artigos inteiros. Seis artigos curados entram com `indexar: false` (spec, seção 5.3) |

## Pendências abertas do gate da Fase 1
| ID | Pendência | Responsável | Prazo |
|---|---|---|---|
| G-2 | ~~Salvar 1 PBIP real em TMSL e registrar `tree /F /A` no progress-log~~ | Fred | **Concluído em 23/09/2026** |
| G-8 | ~~Gerar `rag/sources.yaml` a partir dos `toc.json`~~ | Semana 5 | **Concluído em 09/10/2026** — 1.420 páginas do Learn indexáveis e 6 leituras do SQLBI só como referência (spec `2026-10-09-catalogo-de-fontes-rag-design.md`) |
| — | ~~Instalar Ollama e rodar o spike de LLM~~ | Fred | **Concluído em 29/09/2026** — 7B aprovado, ADR-006 descartada |
| — | ~~Baixar os 7 PBIX do dataset e converter para PBIP~~ | Fred | **Concluído em 09/10/2026** — 53 achados em P1–P7 |
| — | Detalhar as limitações declaradas (heurísticas vs. parser DAX; performance estática vs. medida) no capítulo de metodologia | Fred | Semana 12 |
| — | Escrever o estudo de caso do P8 | Fred | Semana 12 |
