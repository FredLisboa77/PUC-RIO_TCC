# ADR-004 — Coleta da base RAG: páginas públicas do Learn, não repositório GitHub

- **Status:** Aceita
- **Data:** 22/09/2026

## Contexto
O plano original da Fase 1 previa baixar o markdown da documentação da Microsoft a partir do repositório `MicrosoftDocs/powerbi-docs` no GitHub, sob licença CC BY 4.0. A verificação mostrou que esse caminho não existe.

## Verificações feitas (22/09/2026)
1. `GET api.github.com/repos/MicrosoftDocs/powerbi-docs` → **404 Not Found**. O repositório público não existe.
2. Busca na organização `MicrosoftDocs`: os únicos repositórios públicos relacionados são `MicrosoftDocs/powerbi-docs-powershell` (CC BY 4.0) e `MicrosoftDocs/fabric-docs` (CC BY 4.0). Nenhum dos dois contém a orientação de modelagem e DAX que as regras precisam citar.
3. A página do Learn aponta o código-fonte para `MicrosoftDocs/powerbi-docs-pr`, que é **privado**.
4. `learn.microsoft.com/robots.txt` (User-agent `*`): não bloqueia `/power-bi/*`. Bloqueia apenas `/*/answers/...`, `/*/search/?*terms`, `/*/opbuildpdf/` e alguns endpoints `/api/`. O site publica sitemap oficial em `https://learn.microsoft.com/_sitemaps/sitemapindex.xml`.
5. `https://learn.microsoft.com/en-us/power-bi/guidance/toc.json` retorna HTTP 200 e lista **142 artigos** de orientação, entre eles: `star-schema`, `import-modeling-data-reduction`, `model-date-tables`, `relationships-one-to-one`, `relationships-many-to-many`, `relationships-active-inactive`, `relationships-bidirectional-filtering`, `directquery-model-guidance`, `composite-model-guidance`, `report-separate-from-model`.
6. `www.sqlbi.com/robots.txt` e `dax.guide/robots.txt` (User-agent `*`): bloqueiam apenas `/wp-admin/`, `/u/`, `/cert/`, `/learn/`, `/account/`, `/cart/`, `/checkout/`. Páginas de artigo estão liberadas.
7. `github.com/TabularEditor/BestPracticeRules`: campo `license` da API = **null**, sem arquivo LICENSE.

## Decisão
1. **Coletar as páginas públicas do `learn.microsoft.com` em HTML**, convertendo para texto, em vez de clonar repositório de markdown.
2. **Gerar o `rag/sources.yaml` a partir do `toc.json`** de cada seção (`/power-bi/guidance`, referência de DAX, referência de Power Query M), e não a partir de uma lista digitada à mão. Cada entrada guarda `id`, `url`, `titulo`, `organizacao`, `data_acesso`, `licenca`, `observacao`.
3. **SQLBI e DAX Guide entram como lista curta e curada** (10 a 15 artigos escolhidos um a um), nunca por varredura automática.
4. **Regras do Best Practice Analyzer do Tabular Editor entram apenas como referência conceitual.** Não copiar os arquivos `BPARules-*.json` para o repositório, nem reproduzir o texto das regras literalmente. Cada regra do projeto é redigida com palavras próprias e ancorada numa página do Microsoft Learn, que é de onde a fundamentação citada deve vir de qualquer forma (ADR-003).
5. **A cópia local fica em `rag/store/`, fora do Git.** O repositório versiona o catálogo de fontes e o código de coleta, nunca o conteúdo baixado.

## Consequências
- (+) A contagem do corpus deixa de ser estimativa: 142 artigos de guidance já verificados, mais as referências de DAX e M.
- (+) Coleta reprodutível: o `toc.json` é um contrato estável e versionável.
- (+) Risco jurídico reduzido a zero no que se redistribui, porque nada de conteúdo de terceiros é publicado no repositório.
- (−) Converter HTML para texto é mais trabalhoso e mais frágil que ler markdown; a limpeza (navegação, rodapé, blocos de código) precisa de teste.
- (−) Se a Microsoft mudar o layout do Learn, o extrator quebra. Mitigação: guardar o HTML bruto em `rag/store/raw/` para reprocessar sem baixar de novo.

## Registro para o relatório acadêmico
Este ADR é a evidência de que as fontes foram verificadas quanto a licença e a permissão de coleta antes do uso, e não presumidas.
