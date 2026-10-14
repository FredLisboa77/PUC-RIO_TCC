# Relatório HTML/PDF e cache das respostas do LLM

- **Data:** 13/10/2026
- **Fase:** 4, semana 10 — segundo subprojeto da F4 (o primeiro foi a interface Streamlit,
  mergeada na `main` em `5fce01f`)
- **Status:** Aguardando revisão do Fred
- **Depende de:** `ResultadoAuditoria` (`core/auditoria.py`), `app/consulta.py`, o catálogo de
  regras (`core/rules/todas.py`) e `url_em_portugues` (`rag/catalogo.py`)
- **Branch:** `fase4-relatorio`, criada a partir da `main` (`5fce01f`)
- **Funcionalidades do planejamento:** F13 (relatório HTML), F14 (PDF a partir do mesmo HTML),
  F16 (cache dos resultados do LLM)

## 1. Objetivo e enquadramento

A ferramenta já audita pela CLI e pela interface e grava o resultado em JSON. Falta o documento
que sai dela: um relatório que se abre sem a ferramenta. Critério de aceite do roadmap
(semana 10): **HTML e PDF gerados**.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Quem lê o relatório | Os dois públicos com o mesmo documento: o dono do modelo, a quem o analista entrega, e a banca/monografia, como anexo. A seção técnica é opcional na geração |
| O que é o cache da F16 | Cache das **respostas do LLM** (não só abrir JSON salvo): auditoria repetida roda ao vivo em segundos e com textos idênticos; rotulado no resultado |
| Motor do PDF | Playwright controlando o **Edge já instalado** (`channel="msedge"`), sem baixar o Chromium do Playwright |
| Menores adiados da interface | Entram nesta etapa, numa tarefa de acabamento, cada um com teste |

## 2. Mudança de lugar: `app/consulta.py` → `core/apresentacao.py`

O relatório precisa das mesmas consultas da interface (avisos, linhas, resumo, painel "o que foi
examinado"), e `reports/` não deve depender de `app/`. O módulo vai para
`core/apresentacao.py` sem mudança de comportamento; `app/streamlit_app.py` e os testes passam a
importar de lá (`tests/test_app_consulta.py` → `tests/test_apresentacao.py`).

## 3. O relatório (`reports/`)

### 3.1 Conteúdo

HTML autocontido, em português do Brasil, com CSS embutido e nenhum recurso externo além dos
links para o Learn. Nesta ordem:

1. **Cabeçalho:** projeto, data, modo (selo "só regras" quando for o caso), modelo, tempo; uma
   frase sobre o que a ferramenta faz e o que **não** faz — não lê a camada de relatório
   (visuais) nem dados.
2. **O que foi examinado:** regras executadas de quantas, regras com falha e o erro, expressões
   DAX analisadas, lacunas, falha da varredura — antes dos achados.
3. **Resumo:** achados por severidade e por categoria; quantos têm aviso; quantas explicações
   vieram do cache (seção 4).
4. **Índice dos achados:** tabela (severidade, regra, objeto, tabela, aviso), cada linha com
   link interno para o detalhe.
5. **Detalhe por achado**, agrupado por regra, na ordem de `linhas()` (severidade, regra,
   objeto): título da regra, mensagem, evidência (trecho em bloco de código, valores lidos),
   avisos, explicação, recomendação (`recomendacao_final`), fontes citadas — título, seção,
   link do Learn com âncora, "ler em português" quando houver, e o **texto original** do trecho.
6. **Regras aplicadas:** as regras do catálogo com título, severidade, categoria e URL de
   fundamentação (com o link em português).
7. **Seção técnica (opcional, `tecnico=True`):** por achado, todos os trechos que o LLM leu (com
   a origem), tempo, tokens, reduções de contexto, modelo e se veio do cache.

Não entram: tradução automática (é só de exibição; o relatório cita o original), filtros e nada
interativo. CSS de impressão (`@media print`): cada achado evita quebra de página no meio
(`break-inside: avoid`); os links aparecem pelo texto, sem imprimir o endereço ao lado (o PDF
mantém os links clicáveis).

Resultado sem achados: o relatório sai com cabeçalho, painel e a frase "Nenhum achado".

**Escape:** todo texto vindo do modelo, do LLM ou do catálogo passa pelo autoescape do Jinja2.
Um nome de medida com `<script>` aparece como texto.

### 3.2 Geração

- `reports/html.py`: `gerar_html(resultado: ResultadoAuditoria, *, tecnico: bool = False,
  registro: Registro | None = None) -> str`. Jinja2 com `autoescape=True`, template
  `reports/templates/relatorio.html.j2`.
- `reports/pdf.py`: `gerar_pdf(html: str, destino: Path, *, timeout_s: float = 60) -> Path`.
  Playwright síncrono, `chromium.launch(channel="msedge")`, `page.set_content(html)`,
  `page.pdf(format="A4", print_background=True, margin=…, display_header_footer=True,
  footer_template=<"página X de Y">)`. Qualquer falha — pacote ausente, Edge ausente, tempo
  esgotado — levanta `ErroDePdf` com mensagem clara.
- **CLI:** `python -m reports <resultado.json> [--pdf] [--tecnico]` grava
  `<pasta do resultado>/<nome do resultado>.html` (e `.pdf`; com `--tecnico`, sufixo
  `-tecnico`). Falha no PDF: o HTML fica gravado, a mensagem sai em stderr e o código é 1.
- **Interface:** no cabeçalho do resultado, caixa "incluir seção técnica" e os botões
  "Baixar relatório HTML" e "Baixar relatório PDF" (`st.download_button`). O PDF é gerado
  quando o usuário pede (botão "Gerar PDF", que depois vira o download), não a cada
  reexecução do script. Falha no PDF vira mensagem ao lado do botão.

### 3.3 Mascaramento de M — declarado sem objeto

O planejamento previa mascarar strings de conexão e caminhos de consultas M antes do relatório.
Medido em 13/10/2026 nos resultados de P1–P8: nenhuma evidência carrega M, string de conexão ou
caminho local — as regras só leem tabelas, colunas, medidas e relacionamentos, e o grupo 4
(regras de M) saiu do MVP. O mascaramento volta como requisito se uma regra passar a ler M.

## 4. Cache das respostas do LLM (`core/analise/cache.py`)

- `ClienteComCache(llm: LLMClient, pasta: Path = PASTA_CACHE)` implementa `LLMClient`;
  `nome` é o do cliente envolvido. `PASTA_CACHE = outputs/cache-llm/` (já no `.gitignore`).
- **Chave:** sha256 do JSON canônico (`sort_keys`) de modelo, mensagens, esquema e opções de
  geração (`NUM_CTX`, temperatura 0, `SEED`). Qualquer mudança no prompt — regra, contexto
  recuperado, texto do prompt — muda a chave; não há invalidação manual.
- **Armazenamento:** um arquivo por chave, `<pasta>/<hash>.json`, com `texto`,
  `tokens_prompt`, `modelo` e `gravado_em`. Gravação atômica (arquivo temporário + `replace`).
- **Só sucesso entra:** `ErroDeLLM` (inclusive `ContextoExcedido`) passa adiante e nada é
  gravado.
- **Arquivo ilegível ou corrompido:** tratado como ausente — chama o LLM e regrava — com aviso
  no log. **Pasta sem permissão:** a resposta é usada, o cache só não grava, aviso no log.
- **`aquecer()` sempre vai ao cliente real.** Com o Ollama fora do ar, a auditoria completa
  aborta como hoje, mesmo com tudo em cache (ADR-003).
- **Rótulo:** `RespostaLLM` e `AchadoEnriquecido` ganham `do_cache: bool = False` (o padrão
  mantém os JSONs antigos válidos). Num achado do cache, `segundos` é o tempo desta chamada.
  `resumir()` da CLI imprime "Do cache: N" e calcula o tempo médio só sobre as chamadas reais.
  Interface e relatório mostram "N de M explicações vieram do cache de respostas".
- **Desligado por padrão.** CLI: `python -m core.auditoria <pasta> --cache`. Interface: caixa
  "reusar respostas guardadas do LLM (cache)" no modo completo. Com o cache ligado, a tradução
  de trechos também passa por ele.

## 5. Acabamento da interface (menores adiados em 13/10)

| Menor | Correção |
|---|---|
| JSON listado que some antes do clique em "Abrir" → traceback | `OSError` na leitura vira `ErroParaUsuario` |
| `salvar_envio` fora de `try`; pastas `envio-*` acumulam em %TEMP% | gravação do envio dentro do tratamento de erro; a pasta é apagada ao fim da execução |
| `ValidationError` de bug no pipeline aparece como "Não consegui ler o projeto" | capturado antes, como erro inesperado com o tipo |
| Tradução usa o modelo da barra lateral | usa `resultado.modelo_llm`; a barra lateral só quando o resultado não tem modelo |
| Duas auditorias do mesmo modo no mesmo minuto se sobrescrevem | carimbo com segundos: `AAAA-MM-DDTHHMMSS` |
| Objeto, falhas de regra e rótulos de link sem escape de markdown | `_md` nesses pontos |
| Resultado sem achados mostra "Nenhum achado com estes filtros." | "Nenhum achado." quando o resultado não tem achados |
| JSON com BOM recusado | leitura aceita BOM UTF-8 |
| Placeholders dos filtros em inglês ("Choose options") | `placeholder="todas"` |

## 6. Erros

| Situação | O que acontece |
|---|---|
| Playwright não instalado ou Edge ausente | `ErroDePdf` "PDF indisponível: …"; o HTML continua disponível |
| PDF demora mais que `timeout_s` | `ErroDePdf` com a mesma forma |
| Arquivo do cache ilegível | tratado como ausente, aviso no log |
| Pasta do cache sem escrita | resposta usada, nada gravado, aviso no log |
| JSON inválido na CLI do relatório | mensagem e código 1 (mesma leitura da interface) |

## 7. Testes

- **HTML** (resultados em memória): completo, só regras, sem fundamentação, com divergência,
  com lacuna e falha de regra, zero achados. Conferem: avisos presentes; escape de `<script>`
  em nome de objeto e em texto do LLM; seção técnica só com `tecnico=True`; links pt-BR; nenhum
  `src=`/`href=` externo além de `https://learn.microsoft.com`; contagem do cache.
- **PDF:** teste real com marcador `pdf`, pulado quando o Playwright ou o Edge não estão
  disponíveis, conferindo que o arquivo começa com `%PDF`; caminho de erro com Playwright
  simulado (pacote ausente, falha no `launch`).
- **CLI do relatório:** grava `.html`; com `--pdf` simulado grava `.pdf`; falha do PDF deixa o
  HTML e sai com 1.
- **Cache:** acerto e erro; chave muda com prompt e com modelo; falha não é guardada; arquivo
  corrompido; pasta sem escrita; `do_cache` até o achado; auditoria repetida com cache dá textos
  idênticos e zero chamadas ao LLM falso; JSON sem `do_cache` abre; `--cache` na CLI.
- **Interface** (`AppTest`): botões de download aparecem; o de HTML entrega o conteúdo; um teste
  por menor da seção 5.
- **Aceite manual, registrado no progress-log:** HTML e PDF do P8 (completo, com e sem seção
  técnica) e de um projeto de P1–P7 em só regras, abertos e conferidos; P8 auditado duas vezes
  com `--cache` — a segunda em segundos, com textos iguais.

## 8. Dependências

`jinja2` e `playwright`, versões fixadas no `requirements.txt` (seção "Fase 4 - relatório"). Sem
`playwright install`: o navegador é o Edge do sistema. Emenda na ADR-002 registrando o canal
`msedge` e o motivo (o Norton intercepta TLS; o Chromium do Playwright são ~150 MB).

## 9. Fora deste subprojeto

| Item | Destino |
|---|---|
| Mascaramento de M | Sem objeto hoje (seção 3.3) |
| Relatório em Word/Excel, envio por e-mail | Fora do MVP |
| Tradução dentro do relatório | Fora: o relatório cita o original |
| Plano B da banca com o Ollama fora do ar | Abrir JSON salvo (já existe); o cache não substitui o aquecimento |
