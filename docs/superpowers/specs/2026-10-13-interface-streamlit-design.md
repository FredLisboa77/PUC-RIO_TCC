# Interface Streamlit da auditoria

- **Data:** 13/10/2026
- **Fase:** 4, semana 9 — primeiro dos dois subprojetos da F4 (o segundo é o relatório
  HTML/PDF e o cache da demo, semana 10)
- **Status:** Aguardando revisão do Fred
- **Depende de:** `run_audit()` (`core/auditoria.py`), o contrato `AchadoEnriquecido`
  (`core/analise/base.py`) e o índice da RAG (`rag/indice.py`)
- **Branch:** `fase4-interface`, criada a partir da `main` (`40ca0ae`)
- **Funcionalidades do planejamento:** F01 (upload e pasta local), F02 (mensagens claras de
  estrutura), F12 (resultados, filtros, detalhe com evidência)

## 1. Objetivo e enquadramento

A ferramenta hoje só tem a CLI (`python -m core.auditoria`), que imprime um resumo e grava
um JSON. A F4 dá a ela uma interface. O uso principal, decidido pelo Fred, é o de uma
**ferramenta para um analista de BI usar de fato**: ele envia o próprio projeto, acompanha o
progresso e explora os achados. A demonstração para a banca é um caso particular, coberto
pela entrada "abrir resultado salvo", que tem o mesmo peso da nova auditoria.

Critério de aceite do roadmap (semana 9): **app ponta a ponta em 1 PBIP**.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Uso principal | Ferramenta para analista; abrir resultado salvo é entrada de primeira classe |
| Sinais de confiança (`cita_ancora`, fidelidade, sem fundamentação) | Aviso visível no achado quando há problema; trechos lidos, tempo e tokens num expansor de detalhes técnicos |
| Auditoria sem LLM | Modo **só regras**, escolhido explicitamente pelo usuário e rotulado como tal. Falha do Ollama numa auditoria completa continua abortando (ADR-003) |
| Execução longa | Síncrona no próprio script, com barra de progresso por achado e controles desabilitados (abordagem 1). Thread em segundo plano e subprocesso descartados |
| Trechos citados em inglês | Link "ler em português" (`url_pt_br`) mais botão "traduzir trecho" sob demanda pelo mesmo Ollama, com a tradução ao lado do original |

## 2. Mudanças no pipeline (`core/`)

### 2.1 Modo só regras no contrato

- `ResultadoAuditoria` ganha `modo: Literal["completo", "so_regras"] = "completo"`;
  `modelo_llm` passa a `str | None`.
- `Situacao` ganha `"so_regras"`. Nessa situação `contexto` é vazio e `geracao`,
  `motivo_descarte`, `cita_ancora`, `fidelidade`, `segundos` e `tokens_prompt` são `None`.
  O validador `_situacao_coerente` passa a cobrir os três estados: `gerado` exige os quatro
  campos de geração; `sem_fundamentacao` exige só o motivo; `so_regras` exige os quatro
  `None` e contexto vazio.
- `AchadoEnriquecido.modelo` passa a `str | None` (`None` só em `so_regras`).
- `recomendacao_final()` não muda: sem geração, devolve a recomendação padrão do catálogo.
- **Compatibilidade obrigatória:** um JSON gravado antes desta mudança (formato de
  11/10/2026, sem `modo`) continua sendo lido por `ResultadoAuditoria.model_validate_json`,
  como resultado `completo`. Um teste trava isso com uma fixture no formato antigo em
  `tests/fixtures/`, não com o arquivo de `outputs/`.

### 2.2 `run_audit()`

```python
def run_audit(
    pasta_pbip, *, llm: LLMClient | None, base: BaseRag | None,
    registro=None, gabaritos=None,
    ao_progredir: Callable[[int, int, Achado], None] | None = None,
) -> ResultadoAuditoria
```

- `llm is None` **e** `base is None` → modo só regras: não carrega gabaritos, não chama
  `verificar_ancoras`, não aquece o LLM. Cada achado vira `AchadoEnriquecido` com
  `situacao="so_regras"`. Roda em segundos.
- Só um dos dois `None` → `ValueError`: modo ambíguo é erro de programação, não escolha.
- Modo completo: comportamento atual inalterado, inclusive o aborto com `ErroDeAuditoria`
  quando o LLM não responde no aquecimento.
- `ao_progredir(feito, total, achado)` é chamado depois de cada achado tratado, nos dois
  modos. A CLI não o passa.

### 2.3 CLI e gravação

- `python -m core.auditoria <pasta> --so-regras` roda o modo só regras (sem carregar a base).
  `resumir()` passa a indicar o modo e, em só regras, não imprime as linhas de geração.
- `gravar()` passa a nomear o arquivo `<projeto>-<AAAA-MM-DDTHHMM>.json`, com sufixo
  `-so-regras` no modo só regras. Hoje uma segunda auditoria no mesmo dia sobrescreve a
  primeira, o que apaga o histórico de quem audita, corrige e audita de novo.

### 2.4 Link em português

`rag/catalogo.py` (ou um módulo vizinho) ganha `url_em_portugues(url: str) -> str | None`,
que resolve o `url_pt_br` de uma URL do Learn pelo `rag/sources.yaml`, ignorando o fragmento
(`#ancora`) e normalizando a barra final. Lê o catálogo uma vez (cache em memória). URL fora
do catálogo devolve `None`. O texto indexado continua em inglês; a ADR-002 não muda.

### 2.5 Tradução sob demanda

`core/analise/traducao.py`:

```python
def traduzir_trecho(texto: str, llm: LLMClient) -> str
```

Pede ao LLM, em JSON com esquema de um campo (`{"traducao": str}`), a tradução para
português do Brasil, preservando nomes de funções DAX/M, de propriedades e de opções do
Power BI. Resposta que não é JSON válido ou com campo vazio levanta `ErroDeTraducao`. A
tradução é **só de exibição**: a validação da citação já foi feita sobre o original, e nada
traduzido é gravado no resultado.

## 3. A interface (`app/`)

Roda com `streamlit run app/streamlit_app.py`. Textos em português do Brasil.

### 3.1 Barra lateral: duas entradas com o mesmo peso

**Nova auditoria**
- Envio de `.zip` (`st.file_uploader`) ou caminho de pasta local (`st.text_input`). O
  `.zip` enviado é gravado numa pasta temporária com o **nome original**, para
  `nome_do_projeto()` continuar dando o nome do projeto.
- Modo: "completo (com explicação do LLM)" ou "só regras".
- Modelo do Ollama (texto, padrão `MODELO_PADRAO`), só no modo completo.
- Botão "auditar". Durante a execução, um `st.status` mostra a etapa (leitura → regras →
  explicações) e um `st.progress` mostra "achado 7 de 15". Os controles ficam desabilitados
  até o fim (qualquer interação reexecutaria o script e interromperia a auditoria).
- Ao terminar, o resultado vai para o `st.session_state` e é gravado em `outputs/` com
  `gravar()`, como na CLI.

**Abrir resultado salvo**
- Lista dos JSONs de `outputs/`, do mais recente para o mais antigo, com projeto, data e modo.
- Envio de um JSON de outro lugar.

### 3.2 Área principal

1. **Cabeçalho:** projeto, modo (selo "só regras" quando for o caso), modelo, data e tempo
   total.
2. **O que foi examinado** — sempre visível, no alto, junto da contagem (como pede a
   docstring de `ResultadoRegras`): regras executadas de quantas, regras com falha e o erro
   de cada uma, expressões DAX analisadas, lacunas de expressão e falha da varredura, quando
   houver.
3. **Resumo:** achados por severidade e por categoria; quantos têm aviso.
4. **Filtros:** severidade, categoria, regra, tabela, "só achados com aviso".
5. **Tabela de achados:** `st.dataframe` com seleção de uma linha, ordenada por severidade
   (`ORDEM_SEVERIDADE`) e depois por regra e objeto. Colunas: severidade, regra, objeto,
   tabela, aviso.
6. **Detalhe do achado selecionado:**
   - título da regra, severidade, categoria, objeto, mensagem, trecho da evidência em bloco
     de código, valores lidos (`evidencia.detalhe`);
   - **avisos**, cada um com uma frase dizendo o que significa (tabela 3.3);
   - explicação e recomendação (`recomendacao_final`);
   - citações `[n]`: título, seção, link do Learn, "ler em português" (quando
     `url_em_portugues` resolver) e botão "traduzir trecho". A tradução aparece ao lado do
     original com o rótulo "tradução automática — o texto citado é o original" e fica no
     `session_state` para não ser refeita. O botão fica desabilitado em resultado só regras;
   - âncora da regra (`url_canonica`) com o link em português;
   - expansor **detalhes técnicos**: todos os trechos que o LLM leu (com a origem `ancora` ou
     `busca`), tempo, tokens, reduções de contexto e modelo.

### 3.3 Avisos

| Aviso | Gatilho |
|---|---|
| Sem fundamentação — recomendação padrão da regra | `situacao == "sem_fundamentacao"`, com o motivo em linguagem comum |
| Divergência de fidelidade | `fidelidade.divergencias` não vazia, com os termos |
| Não cita a seção âncora da regra | `cita_ancora is False` |
| Contexto reduzido para caber | `reducoes_de_contexto > 0` |
| Só regras — sem explicação do LLM | `situacao == "so_regras"` |

### 3.4 Divisão do código

- `app/consulta.py` — puro, sem Streamlit: avisos de um achado, linhas da tabela, filtros,
  resumos por severidade e categoria, painel "o que foi examinado", listagem e leitura dos
  resultados salvos.
- `app/streamlit_app.py` — só a renderização e o estado da sessão; chama `run_audit`,
  `gravar`, `traduzir_trecho` e as funções de `consulta`.

## 4. Erros

Toda falha vira mensagem na tela, nunca traceback.

| Situação | O que a interface faz |
|---|---|
| Entrada que não é PBIP (`ErroEstruturaPbip`) ou `model.bim` corrompido (`ValueError`) | Mensagem com o motivo; nada é gravado |
| Ollama fora do ar no aquecimento (`ErroDeAuditoria`) | Mensagem sugerindo o modo só regras ou iniciar o Ollama; nada é gravado (ADR-003) |
| Índice ausente ou âncora sem trecho (`ErroDeIndice`, `ErroDeContexto`, `OSError`) | Mensagem com o comando que constrói o índice; o modo só regras segue disponível |
| JSON inválido ou de outro formato ao abrir | Mensagem; o resultado aberto antes continua na tela |
| Falha ao gravar em `outputs/` | O resultado é exibido mesmo assim, com aviso |
| Tradução falha (`ErroDeLLM`, `ErroDeTraducao`) | Mensagem local no trecho; o resto do detalhe segue |

## 5. Testes

- **Pipeline** (`tests/test_auditoria.py`): só regras não toca base nem LLM; o validador
  cobre os três estados; `ValueError` com um só `None`; `ao_progredir` chamado N vezes com o
  total certo nos dois modos; `--so-regras` na CLI; nome do arquivo com hora e sufixo;
  compatibilidade com o JSON no formato de 11/10.
- **Link em português:** URL com e sem fragmento e barra final; URL fora do catálogo.
- **Tradução:** LLM falso — sucesso, JSON inválido, campo vazio.
- **`app/consulta.py`:** cada aviso com e sem gatilho; filtros combinados; ordenação;
  resumos; painel com falha de regra e com lacuna; listagem de `outputs/` ordenada e
  tolerante a JSON inválido. Objetos montados em memória (`tests/fabricas_analise.py`).
- **Interface** (`streamlit.testing.v1.AppTest`, LLM falso, PBIP sintético de `escrever_pbip` em `tests/conftest.py`): abrir resultado
  salvo mostra painel e tabela; só regras roda ponta a ponta; erro de PBIP vira mensagem.
- **Aceite manual, registrado no progress-log:** auditoria completa do P8 pela interface com
  o `qwen2.5:7b` (tempo e número de achados); auditoria só regras de P1–P7 conferindo os 53
  achados.

## 6. Dependência

`streamlit`, com versão fixada no `requirements.txt` (seção "Fase 4 - interface"). Jinja2 e
Playwright ficam para o subprojeto da semana 10.

## 7. Fora deste subprojeto

| Item | Destino |
|---|---|
| Relatório HTML/PDF e cache da demo (F13, F14, F16) | Subprojeto da semana 10 |
| Cancelamento da auditoria em andamento (thread em segundo plano) | Trabalho futuro |
| Texto oficial em pt-BR dos trechos (coleta das páginas pt-BR e alinhamento de seções) | Trabalho futuro — as âncoras mudam com o idioma, o alinhamento é frágil |
| Comparar duas auditorias do mesmo projeto | Trabalho futuro |
