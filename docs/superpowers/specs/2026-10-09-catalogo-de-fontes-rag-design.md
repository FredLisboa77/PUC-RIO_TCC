# Catálogo de fontes da RAG (`rag/sources.yaml`)

- **Data:** 09/10/2026
- **Fase:** 3 — semana 6 do roadmap
- **Status:** Em revisão
- **Pendência:** G-8 (`backlog.md`)
- **Decisões que este desenho executa:** ADR-004 (coleta pelas páginas públicas do Learn, catálogo gerado a partir do `toc.json`), ADR-002 (corpus e embeddings em inglês)

## 1. Objetivo e contexto

A Fase 3 constrói a base que fundamenta as explicações dos achados (ADR-003: toda explicação cita um trecho recuperado, e todo trecho carrega URL e data). O primeiro passo é o **catálogo**: a lista versionada das páginas que a base contém, com os metadados que a citação vai precisar. Coleta, chunking, embeddings e índice são etapas seguintes, fora deste documento.

O ADR-004 decidiu que o catálogo é **gerado** a partir dos `toc.json` do Microsoft Learn, não digitado. Este desenho define como.

### O que a medição de 09/10/2026 mudou no plano

| Fato medido | Consequência |
|---|---|
| `power-bi/guidance/toc.json` lista **160** links (o ADR-004 contou 142 em 22/09) | A seção muda; o catálogo precisa registrar **quando** foi lido, e o diff entre leituras precisa ser visível |
| Referência de DAX: **510** páginas; de M: **769** | O roadmap previa ~60–120 documentos. O escopo aprovado (seção 2) chega a **1.420** — mudança decidida pelo Fred, registrada no backlog |
| Duas âncoras das 9 regras ficam **fora** das três seções do ADR-004: `power-bi/connect-data/desktop-data-types` (PERF-003) e `power-bi/transform-model/desktop-date-tables` | Gerar só das três seções deixaria sem fonte duas regras em produção. As âncoras viram origem própria |
| Os `toc.json` em **pt-BR** das cinco seções envolvidas têm **exatamente os mesmos caminhos** que os em inglês | A versão em português de cada página pode ser apontada sem raspar HTML — mas é conferida, não suposta |
| Link relativo à raiz no `toc.json` (`/dax/best-practices/...`) **não traz o idioma** | Resolvido ingenuamente, vira `learn.microsoft.com/dax/...` e seria descartado; as 9 páginas de DAX que o guidance lista perderiam essa origem. A resolução prefixa o idioma (seção 2.2) |

## 2. O que entra no catálogo

### 2.1 Origens

Uma página entra se vier de pelo menos uma origem:

| Origem | Conteúdo | Páginas (09/10/2026) |
|---|---|---|
| `toc:power-bi/guidance` | Todo link do `toc.json` do guidance que seja artigo do Learn — inclusive os que apontam para outras seções (`/dax/best-practices/...`, `/fabric/cicd/...`), porque a Microsoft os pôs nessa navegação | 151 |
| `toc:dax` | **Toda** a referência de DAX, boas práticas incluídas | 508 |
| `toc:powerquery-m` | **Toda** a referência de Power Query M | 768 |
| `regra:<ID>` | A `url_canonica` de cada regra do registro | 9 âncoras, 8 URLs distintas |

**Total: 1.420 páginas** — 1.418 das três seções (9 delas em `toc:power-bi/guidance` e `toc:dax` ao mesmo tempo) mais as 2 âncoras de fora.

Uma âncora fora das três seções tem o título resolvido pelo retrato do `toc.json` da **sua** seção. Hoje são duas seções nessa condição: `power-bi/connect-data` e `power-bi/transform-model`. Elas são retratadas, mas **não são origem**: só a página da âncora entra, não a seção inteira.

### 2.2 Resolução de link

Cada `href` é resolvido para URL absoluta em `https://learn.microsoft.com/en-us/`:

| Forma do `href` | Exemplo | Resolução |
|---|---|---|
| Relativo | `star-schema` | relativo à pasta da seção: `.../en-us/power-bi/guidance/star-schema` |
| Relativo com `../` | `../transform-model/dataflows/...` | idem, com a subida de pasta aplicada |
| Relativo à raiz | `/dax/best-practices/dax-variables` | **prefixa o idioma**: `.../en-us/dax/best-practices/dax-variables` |
| Absoluto | `https://ideas.fabric.microsoft.com/` | mantido; excluído se o host não for `learn.microsoft.com` |

A comparação entre URLs — inclusive com a `url_canonica` das regras — é feita sobre a forma normalizada: esquema e host em minúsculas, sem `?query`, sem `#fragmento`, sem barra final.

### 2.3 Exclusões

Não são erro; são contadas por motivo no resumo da geração.

| Motivo | Exemplos (09/10/2026) |
|---|---|
| Host fora do `learn.microsoft.com` | fórum, `ideas.fabric`, `feedback.azure`, status do Azure — 6 |
| Página de entrada de seção ou área que não é documentação | `./`, `/contribute/`, `/answers/`, `/training/fabric/` — 6 |

O critério para o segundo motivo é a URL resolvida terminar em `/`, com uma lista explícita de prefixos não documentais (`/contribute/`, `/answers/`, `/training/`) como segunda barreira.

### 2.4 Idioma

- O texto que será **indexado** é o en-US, e a `url` de cada entrada é a `/en-us/`. O ADR-002 não muda: corpus e embeddings (`bge-small-en-v1.5`) seguem em inglês.
- Cada entrada tem `url_pt_br`, preenchida **somente** quando o mesmo caminho existe no retrato pt-BR da seção que forneceu a entrada. Se a Microsoft tirar uma página do pt-BR, o campo fica vazio em vez de apontar para um link quebrado.
- O relatório final usará `url_pt_br` para levar o leitor à versão em português da página citada.

Por que não indexar o pt-BR, como foi cogitado: o `bge-small-en-v1.5` é monolíngue; o pt-BR do Learn é em grande parte tradução automática; e as âncoras das 9 regras foram verificadas e transcritas do texto em inglês. Indexar pt-BR exigiria revisar o ADR-002 e trocar para um embedding multilíngue de ~2 GB. Decisão do Fred em 09/10/2026: inglês indexado, link pt-BR para o leitor.

## 3. Componentes e fluxo

```
learn.microsoft.com/{en-us,pt-br}/<seção>/toc.json
        │  python -m rag.catalogo atualizar      (único passo com rede)
        ├──► rag/store/raw/tocs/<idioma>/<seção>.json   bruto, fora do Git
        ▼
rag/tocs/<idioma>/<seção>.json                   listagem normalizada, versionada
        │  python -m rag.catalogo gerar           (offline, determinístico)
        │  + âncoras de core.rules.todas.REGISTRO
        │  + rag/observacoes.yaml                 (notas à mão)
        ▼
rag/sources.yaml                                  versionado; nunca editado à mão
        │  (próxima etapa: coleta → rag/store/, fora do Git)
```

### 3.1 `rag/tocs.py` — retratos (I/O)

- Constante `SECOES`, explícita: `power-bi/guidance`, `dax`, `powerquery-m` como **origens**; `power-bi/connect-data`, `power-bi/transform-model` como **resolução de âncora**. Idiomas: `en-us`, `pt-br`. Dez retratos.
- `baixar_retratos(buscar, hoje, pasta_versionada, pasta_bruta)`:
  - `buscar(url) -> bytes` é injetado. O padrão usa `urllib.request` da biblioteca padrão, com `User-Agent` que identifica o projeto e o repositório (`powerbi-ai-auditor (+https://github.com/FredLisboa77/PUC-RIO_TCC)`) e `timeout` de 30 s. Sem e-mail no cabeçalho.
  - Baixa **os dez** antes de gravar qualquer um. Qualquer falha — HTTP diferente de 200, JSON inválido, ausência de `items` — aborta sem tocar nos retratos existentes.
  - Grava o bruto em `rag/store/raw/tocs/` (fora do Git, para auditoria e reprocessamento) e a **listagem normalizada** em `rag/tocs/`:

```json
{
  "secao": "power-bi/guidance",
  "idioma": "en-us",
  "url": "https://learn.microsoft.com/en-us/power-bi/guidance/toc.json",
  "baixado_em": "2026-10-09",
  "itens": [
    {"href": "star-schema", "titulo": "Understand star schema and the importance for Power BI"}
  ]
}
```

  `itens` é a árvore achatada em ordem de aparição, só com os itens que têm `href`. A listagem é JSON com chaves em ordem fixa e indentação fixa, para que o `git diff` entre dois retratos mostre exatamente o que a Microsoft mudou.

### 3.2 `rag/catalogo.py` — montagem (função pura)

- `ler_retratos(pasta) -> Retratos` — lê `rag/tocs/`; falha se faltar algum dos dez, nomeando o arquivo e indicando `atualizar`.
- `montar_catalogo(retratos, ancoras, observacoes) -> list[Fonte]` — sem rede e sem ler o registro de regras sozinha. `ancoras` é `{id_regra: url}`; `observacoes` é `{id: texto}`. Saída ordenada por `id`. Recebe tudo por parâmetro, para que `rag/` não dependa de `core/` e os testes usem dados pequenos.
- `escrever_yaml(fontes, caminho)` — `yaml.safe_dump` com ordem de campos fixa, `sort_keys=False`, `allow_unicode=True` e `width` grande o bastante para não quebrar linha. Gerar duas vezes dá bytes idênticos.
- `Fonte` é um modelo Pydantic, como o resto do projeto.

### 3.3 Comando

- `python -m rag.catalogo gerar` (padrão, offline) e `python -m rag.catalogo atualizar` (baixa os retratos e então gera).
- É a camada de comando que importa `core.rules.todas.REGISTRO` e extrai as âncoras.
- Ao fim, imprime: total de páginas, contagem por origem, exclusões por motivo, quantas têm `url_pt_br`, e cada âncora com a entrada que a satisfez.

### 3.4 Seção nova

Quando uma regra futura tiver âncora fora das cinco seções, `gerar` falha nomeando a URL. A correção é uma linha em `SECOES` e um `atualizar`. Explícito, sem adivinhar em qual `toc.json` procurar.

## 4. Formato de cada entrada

```yaml
- id: learn:dax/best-practices/dax-divide-function-operator
  url: https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator
  url_pt_br: https://learn.microsoft.com/pt-br/dax/best-practices/dax-divide-function-operator
  titulo: DIVIDE function vs divide operator (/)
  organizacao: Microsoft
  data_acesso: '2026-10-09'
  licenca: Termos de uso do Microsoft Learn — uso pessoal e não comercial; cópia local não redistribuída (https://learn.microsoft.com/en-us/legal/termsofuse)
  origem: [regra:DAX-001, toc:dax, toc:power-bi/guidance]
  observacao: null
```

| Campo | Regra |
|---|---|
| `id` | `learn:` + caminho depois de `/en-us/`. O prefixo reserva espaço para fontes curadas futuras (`sqlbi:`, `daxguide:`) |
| `url` | URL canônica en-US, normalizada (seção 2.2) |
| `url_pt_br` | seção 2.4; `null` quando o caminho não está no retrato pt-BR |
| `titulo` | Título de navegação do `toc.json`, preferindo o retrato da **própria seção** da página; depois, a ordem fixa `guidance`, `dax`, `powerquery-m`, seções de âncora. Medido em 09/10: as 9 páginas presentes em dois tocs têm o mesmo título nos dois |
| `organizacao` | `Microsoft` |
| `data_acesso` | Data do retrato que forneceu o título. É a data de **catalogação**; a data de acesso ao **conteúdo**, que vai na citação, é registrada pela coleta |
| `licenca` | Texto fixo da tabela acima (ver seção 5.2) |
| `origem` | Lista ordenada, sem repetição |
| `observacao` | Vem de `rag/observacoes.yaml`; `null` quando não há nota |

**Limitação declarada do `titulo`:** alguns títulos de navegação são genéricos (`Introduction` aparece 3 vezes). A coleta registrará o título real da página (H1) no manifesto do `rag/store/`, e é esse que a citação final usa.

## 5. Verificação de boas práticas (09/10/2026)

### 5.1 Etiqueta de coleta

- **`robots.txt` relido hoje** (`learn.microsoft.com`, `User-agent: *`): bloqueia `/*/answers/...`, `/*/opbuildpdf/`, `/*/search/?*terms` e dois endpoints de `/api/`. Nada bloqueia `toc.json` nem as seções do catálogo. Igual ao verificado em 22/09 (ADR-004).
- **Volume:** esta etapa faz 10 requisições. A coleta (etapa seguinte, ~1.420 páginas) precisará de pausa entre requisições e de ser retomável — fica registrado aqui como requisito herdado.
- **Identificação:** `User-Agent` com nome e repositório do projeto; `timeout` explícito; nenhuma repetição automática — falha é falha, e o comando é rodado de novo.

### 5.2 Termos de uso — e a correção que eles impuseram

Os Termos de Uso do Learn (lidos hoje, versão de 12/05/2025) dizem que os serviços são *"for your personal and non-commercial use"* e que não se pode *"copy, distribute, transmit, publicly display ... reproduce, publish"* o que se obtém deles sem consentimento, salvo para uso próprio, pessoal e não comercial. Para documentos, a permissão exige que *"use ... is for informational and non-commercial or personal use only and will not be copied or posted on any network computer"*.

Consequências para o desenho:

1. **A cópia local do conteúdo** (`rag/store/`, fora do Git) é uso pessoal, não comercial e acadêmico, sem redistribuição — compatível, como o ADR-004 já previa.
2. **Correção em relação ao desenho conversado:** a primeira versão versionava o `toc.json` **bruto**. Isso publicaria num repositório público uma cópia literal de um arquivo da Microsoft. O desenho final versiona apenas a **listagem normalizada** (caminho e título), que é a mesma informação bibliográfica que o próprio `sources.yaml` já contém; o bruto fica em `rag/store/raw/tocs/`, fora do Git.
3. **`licenca` não diz CC BY 4.0.** Essa licença vale para os repositórios públicos `MicrosoftDocs/*`, e o ADR-004 mostrou que o do Power BI é privado. O campo descreve o que foi verificado: os termos de uso, e a condição sob a qual o projeto os cumpre.

### 5.3 Engenharia

| Prática | Como o desenho atende |
|---|---|
| Núcleo puro, I/O nas bordas | `montar_catalogo` não faz rede nem lê arquivo; `buscar` é injetado |
| Reprodutibilidade | Retratos datados e versionados; geração determinística; teste de arquivo gerado atualizado (seção 6, item 4) |
| Escrita atômica | Os dez retratos só substituem os antigos se todos vierem certos |
| Arquivo gerado não editado à mão | `sources.yaml` só sai do gerador; notas humanas em `observacoes.yaml` |
| Falha alta | Âncora ausente, retrato ausente ou nota órfã interrompem a geração |
| Dependência mínima e fixada | Rede com `urllib` (biblioteca padrão). **PyYAML** entra no `requirements.txt` com versão fixa, usado só via `safe_load`/`safe_dump` |
| Metadados de citação por documento | URL canônica, título, organização, datas e licença por entrada — o que o ADR-003 exige da citação |

## 6. Erros e testes

### 6.1 Erros

| Situação | Comportamento |
|---|---|
| `atualizar`: um `toc.json` com HTTP ≠ 200, JSON inválido ou sem `items` | Aborta sem tocar nos retratos existentes |
| `gerar`: falta retrato | Falha nomeando o arquivo e indicando `atualizar` |
| Retrato com estrutura inesperada | Falha nomeando o arquivo |
| Âncora de regra não encontrada em nenhum retrato | Falha listando as âncoras e as regras que as usam |
| Nota em `observacoes.yaml` para `id` fora do catálogo | Falha — a nota não pode sumir em silêncio quando a Microsoft remove ou renomeia uma página |
| Link excluído | Não é erro; contado no resumo por motivo |

### 6.2 Testes (pytest, sem rede)

1. **Unidade, com retratos pequenos feitos à mão:** os quatro tipos de `href` (seção 2.2), inclusive o relativo à raiz recebendo o idioma; cada motivo de exclusão; página com duas origens vira uma entrada com as duas; precedência de título; `url_pt_br` presente só quando o caminho está no retrato pt-BR; âncora resolvida por seção que não é origem; âncora ausente e nota órfã levantam erro; mesma entrada em outra ordem dá a mesma saída.
2. **Determinismo:** gerar duas vezes produz bytes idênticos.
3. **Retratos:** `buscar` falso; uma falha no meio preserva os retratos antigos; o bruto vai para a pasta fora do Git e a listagem normalizada para `rag/tocs/`.
4. **Sobre os dados reais versionados** (sempre rodam, porque `rag/tocs/` está no Git): as 9 âncoras presentes; contagem entre 1.300 e 1.600; e o **`sources.yaml` do repositório idêntico ao que o gerador produz agora** — pega edição à mão e catálogo desatualizado em relação aos retratos.

## 7. Fora de escopo

- Coleta das páginas, chunking, embeddings, índice e recuperação.
- SQLBI e DAX Guide — etapa própria, depois de fechar o R-05. O prefixo de `id` já reserva o espaço.
- Qualquer mudança no ADR-002.

## 8. Registros a fazer junto com a implementação

- `backlog.md`: G-8 concluído; mudança de escopo do corpus de ~60–120 para ~1.420 páginas, decidida pelo Fred em 09/10/2026, com o motivo (referências completas de DAX e M na base).
- `.gitignore`: nada a mudar — `rag/store/` já está ignorado, e `rag/tocs/` deve ser versionado.
- `progress-log.md`: entrada da etapa, com as contagens medidas.
