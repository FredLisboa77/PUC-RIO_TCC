# Coleta e extração da base RAG

- **Data:** 09/10/2026
- **Fase:** 3 — semana 6 do roadmap
- **Status:** Rascunho — seções aprovadas uma a uma com o Fred
- **Depende de:** `rag/sources.yaml` (G-8, spec `2026-10-09-catalogo-de-fontes-rag-design.md`)
- **Decisões que este desenho executa:** ADR-004 (coleta pelas páginas públicas do Learn; HTML bruto guardado para reprocessar), R-13 (extrator quebra com mudança de layout)

## 1. Objetivo e contexto

Baixar as **1.420 páginas** do catálogo com `indexar: true` e transformar cada uma em
texto estruturado por seção, pronto para o chunking da etapa seguinte. As 6 leituras
do SQLBI (`indexar: false`) nunca são baixadas.

**Restrições que já valem:** termos de uso do Learn (uso pessoal e não comercial;
cópia local em `rag/store/`, fora do Git); pausa entre requisições e coleta retomável
(spec do catálogo, 5.1); HTML bruto guardado para reprocessar sem baixar de novo
(ADR-004, R-13); título real e data de acesso de cada página registrados para a
citação.

### O que a amostra de 09/10/2026 mostrou

| Fato medido | Consequência |
|---|---|
| 6 páginas sorteadas do catálogo: HTTP 200, 46–81 KB, 0,56–0,75 s cada | ~80 MB e ~40 min para as 1.420, com pausa de 1 s |
| Cada página traz `updated_at`, `ms.date`, `document_id` e `git_commit_id` em `<meta>` | A citação pode dizer de quando é o texto; uma recoleta futura sabe o que mudou |
| Todo título de seção tem `id` (`<h2 id="...">`) | A citação pode apontar a seção exata (`#ancora`), não só a página |
| Disco D: com 1.499 GB livres; RAM com 2,5 GB livres de 15,9 GB | Disco sem restrição; memória não pesa na coleta, mas pesa nas etapas de embeddings e LLM |

### Decisões do Fred nesta etapa

- **Dois passos separados** — `rag.coleta` (rede, HTML bruto) e `rag.extracao` (offline,
  HTML → texto estruturado). Ajustar o extrator custa reprocessar, não rebaixar.
  Recusados: um passo só guardando só o texto (descarta o bruto, contraria ADR-004) e
  um passo só guardando os dois (junta rede e interpretação; erro de extração derruba a
  coleta).
- **Extração com BeautifulSoup** (`beautifulsoup4`, parser `html.parser` da biblioteca
  padrão, sem lxml). Recusados: só biblioteca padrão (extração estruturada longa e
  frágil) e trafilatura (muitas dependências, pouco controle sobre seções e âncoras).

## 2. A coleta — `python -m rag.coleta`

**Entrada:** as entradas do `rag/sources.yaml` com `indexar: true`, em ordem de `id`.

**Saída, toda em `rag/store/` (fora do Git):**

- **HTML bruto** em `rag/store/raw/paginas/`, um arquivo por página, caminho derivado
  do id: `learn:dax/calculate-function-dax` → `learn/dax/calculate-function-dax.html`.
  Gravação atômica (`.tmp` + `replace`).
- **Registro da coleta** em `rag/store/coleta.jsonl`: uma linha por tentativa,
  acrescentada logo depois de gravar a página — `id`, `url`, situação (`ok` | `erro`,
  com o motivo), tamanho, `sha256` do arquivo, data e hora do acesso (UTC) e os
  metadados de versão da página (`updated_at`, `ms_date`, `git_commit_id`,
  `document_id`).

**Retomada:** ao começar, lê o registro e pula toda página cuja última linha é `ok` e
cujo arquivo existe com o mesmo `sha256`. Uma interrupção (queda de rede, Ctrl+C,
desligar a máquina) custa no máximo a página em andamento. Páginas com erro são
tentadas de novo na execução seguinte.

**Etiqueta e proteção:**

- Pausa de **1 s** entre requisições, configurável (`--pausa`).
- Mesmo `User-Agent` e mesmo buscador do G-8 (`rag.tocs.buscar_padrao`), que **recusa
  redirecionamento**: página que mudou de endereço é erro, porque o catálogo envelheceu.
- Erro comum de uma página (404, por exemplo) é registrado e a coleta segue.
- **429 ou 503** — o servidor pedindo para parar — **interrompem na hora**. Também
  interrompem **5 falhas seguidas** (sem internet, por exemplo), para não martelar o site.
- `--limite N` coleta só as N primeiras páginas, para ensaio.

**Resumo ao final:** coletadas nesta execução, já existentes, com erro (listadas uma a
uma) e o total `ok` sobre o total do catálogo.

## 3. A extração — `python -m rag.extracao`

**Entrada:** o HTML bruto de cada página cuja última linha no registro da coleta é
`ok`. Offline.

**Estrutura medida em 09/10/2026** (`guidance/star-schema` e `dax/calculate-function-dax`):
o conteúdo está num único `<main id="main">`; os títulos vão de H1 a H4, todos com
`id`; páginas de referência de DAX trazem `<pre>` (5 na de CALCULATE) e `<table>` (5);
o fim de página traz blocos de navegação — "Related content" (`h2#related-content`),
"Feedback" (`h2#ms--feedback`) e "Additional resources".

**Saída:** um JSON por página em `rag/store/textos/`, no mesmo caminho relativo do HTML:

- **Identificação:** `id` e `url` do catálogo; **título real** (o texto do H1); metadados
  de versão vindos do registro da coleta (`updated_at`, `ms_date`, data de acesso).
- **Seções:** uma por título H1–H4, cada uma com:
  - `ancora` (`syntax`, `remarks`...), para a citação apontar a seção exata;
  - `nivel` (1–4) e `caminho` (ex.: `Syntax › Parameters`), para o trecho não perder
    contexto;
  - `blocos` em ordem, cada um com `tipo`: `paragrafo`, `lista`, `tabela` (linhas em
    texto, com o cabeçalho), `codigo` (verbatim, com a `linguagem` — DAX, M), `nota`
    (os avisos *Note*, *Tip*, *Important* do Learn, com o rótulo).
  - O conteúdo entre o H1 e o primeiro H2 forma a seção de nível 1.

**Fica de fora, por lista explícita, com contagem no resumo:** navegação lateral e
"In this article"; as seções `related-content`, `next-steps`, `ms--feedback` e
"Additional resources" (só listas de links); imagens; o endereço dos links (o texto
do link fica).

**Verificações que falham alto:** página sem H1 ou sem nenhum bloco de texto é **erro
nomeado** no resumo. H1 diferente do título do catálogo **não** é erro — o do catálogo
é o título de navegação —, mas é registrado.

**Versão do extrator:** cada JSON leva `versao_extrator`. Mudou o extrator, roda-se a
extração de novo sobre o HTML guardado, em segundos.

**Direitos nos testes:** nenhum HTML do Learn entra no Git (termos de uso, spec do
catálogo 5.2). Testes de unidade usam HTML sintético escrito à mão imitando a
estrutura medida acima; um teste sobre os dados reais roda só quando `rag/store/`
existe, como os testes do PBIP real.
