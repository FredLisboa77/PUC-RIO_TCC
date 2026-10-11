# Geração com o LLM e citação obrigatória

- **Data:** 11/10/2026
- **Fase:** 3, semana 7 do roadmap (F11)
- **Status:** Aguardando revisão do Fred
- **Depende de:** o índice da vencedora (`rag/store/indice/`, spec `2026-10-11-medicao-da-recuperacao-design.md`), o gabarito das âncoras (`eval/recuperacao/consultas.yaml`), as regras (`core/rules/`) e o Ollama com `qwen2.5:7b-instruct-q4_K_M`
- **Decisões que este desenho executa:** ADR-003 (regras são a única fonte de achados; citação obrigatória; descarte com recomendação padrão), ADR-002 (modelo local, `num_ctx=4096`, saída em português; emendas de 09/10 — âncora sempre no contexto — e de 11/10 — busca BM25 sobre o corpus completo)

## 1. Objetivo e contexto

Transformar cada achado das regras num **achado enriquecido**: explicação e recomendação
redigidas pelo LLM a partir de trechos recuperados, com citação validada por código. A
entrega da semana é rodar a auditoria inteira sobre um PBIP real (o P8, estudo de caso
da ADR-005) e gravar os achados enriquecidos em JSON.

O LLM **não decide** se o achado existe (ADR-003). Ele só explica e recomenda, e precisa
citar um trecho do contexto. Se a resposta não passa na validação, é descartada e o
achado sai com a `recomendacao_padrao` da regra e a marca "sem fundamentação gerada".

O resultado precisa permitir que a Fase 5 meça três coisas sem refazer a geração:

1. **citação válida** — o número citado existe no contexto;
2. **citação pertinente** — a seção âncora da regra está entre as citadas (gabarito
   objetivo, emenda de 09/10 da ADR-002);
3. **fidelidade à evidência** — números e nomes da resposta aparecem no achado ou nos
   trechos (critério nascido no spike de 29/09: o 3B escreveu "duas tabelas" quando a
   evidência dizia quatro).

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Granularidade da citação | **Pelo número do trecho** (`[1]`, `[2]`…). O código traduz para página + seção. URL inteira (spike) ou URL com âncora foram descartadas: a primeira só mede pertinência por página; a segunda obriga um 7B a copiar strings longas |
| Formato da resposta | **JSON com esquema imposto pelo Ollama** (`format` = JSON Schema) |
| Quantas citações | **1 a 3** números; válida se todos existem; pertinente se a âncora está entre eles |
| Falha na validação | **Descarta direto**, sem nova tentativa, **registrando o motivo** em cada achado. Nova tentativa só entra depois, como mudança medida, se a taxa real vier baixa |
| Fidelidade | **Verifica e registra, não descarta.** A heurística ainda não está calibrada para ser portão |
| Escopo | Geração **e** `run_audit()` mínimo com comando de linha. Fora: interface, relatório HTML/PDF, cache F16, medição sobre P1–P7 |
| Organização | Pacote `core/analise/` com unidades pequenas (o desenho da Fase 1 previa um `core/analysis.py` único; a troca é organização interna e não pede ADR) |

## 2. Fluxo

Sequencial e sem estado, por achado:

```
Achado + RegraMeta
  → consulta = montar_consulta(meta, achado)          rag/consulta.py (já existe)
  → contexto = [âncora] + complementares do BM25      core/analise/contexto.py
  → mensagens → LLMClient.gerar(mensagens, esquema)   core/analise/prompt.py, llm.py
  → validar → aceita | descarta com motivo            core/analise/validacao.py
  → se aceita: verificar fidelidade                   core/analise/fidelidade.py
  → AchadoEnriquecido                                 core/analise/enriquecimento.py
```

E da auditoria inteira (`core/auditoria.py`):

```
pasta PBIP → abrir_pbip → ler_modelo → avaliar_regras
           → verificação de partida (toda regra com gabarito e âncora no índice)
           → enriquecer cada achado → ResultadoAuditoria → outputs/<projeto>-<data>.json
```

## 3. Contratos (`core/analise/base.py`)

**`TrechoDeContexto`**

| Campo | Conteúdo |
|---|---|
| `numero` | 1, 2, … — o número que o LLM cita |
| `id_pagina`, `url`, `titulo`, `ancora`, `caminho` | de onde veio, copiados do `TrechoIndexado` |
| `texto` | o texto entregue ao modelo |
| `origem` | `"ancora"` (sempre o número 1) ou `"busca"` |

**`Geracao`** — `explicacao: str`, `recomendacao: str`, `citacoes: list[int]`.

**`AchadoEnriquecido`**

| Campo | Conteúdo |
|---|---|
| `achado` | o `Achado` original, intacto |
| `contexto` | `list[TrechoDeContexto]`, inteiro — a Fase 5 e a banca veem o que o modelo tinha |
| `geracao` | `Geracao`, ou `None` se descartada |
| `situacao` | `"gerado"` ou `"sem_fundamentacao"` |
| `motivo_descarte` | `"json_invalido"`, `"campo_vazio"`, `"citacoes_fora_do_limite"`, `"citacao_inexistente"`, `"erro_llm"` ou `None` |
| `cita_ancora` | `bool` — o trecho 1 está entre as citadas; `None` se descartada |
| `fidelidade` | `divergencias: list[str]` (vazia = sem divergência); `None` se descartada |
| `modelo` | nome do modelo do LLM |
| `segundos` | tempo da chamada, sem a carga do modelo |

Método `recomendacao_final(meta: RegraMeta) -> str` (método e não propriedade, porque o
achado guarda só o `id_regra` e o catálogo é a fonte da recomendação padrão): a recomendação do LLM se `situacao == "gerado"`,
senão `meta.recomendacao_padrao`. O relatório nunca precisa saber de onde veio a
recomendação; só exibe a marca "sem fundamentação gerada" quando for o caso.

Invariantes, checados por validador Pydantic: `situacao == "gerado"` ⇔ `geracao` não
nula ⇔ `motivo_descarte` nulo ⇔ `cita_ancora` e `fidelidade` não nulos.

## 4. Contexto (`core/analise/contexto.py`)

- **[1] é sempre o trecho âncora**: o trecho do índice com o `id_pagina` e a `ancora` do
  gabarito da regra (`eval/recuperacao/consultas.yaml`, seção `gabaritos`). Se a seção
  foi partida em vários trechos, entra a parte que contém a frase-marca (comparação com
  `rag.texto.normalizar`, como a régua). A âncora vem do gabarito, que já é verificado
  contra a base por teste; o `RegraMeta` não ganha campo novo, para não duplicar a
  informação.
- **Complementares**: `buscar(consulta, k=10)`; descartados os trechos idênticos ao
  âncora (mesmo `id`), entram **até 4**, em ordem de posição, enquanto o total de
  palavras do contexto não passar de **1.800** (~2.500 tokens). Sobram ~1.600 tokens dos
  4096 para instrução, evidência e resposta. A âncora entra sempre, mesmo que sozinha
  passe do orçamento. Um complementar que estouraria o orçamento é pulado, e o próximo é
  tentado.
- **Falta de âncora** (regra sem gabarito, ou seção ausente do índice, ou nenhuma parte
  com a frase-marca): `ErroDeContexto`. O `run_audit()` verifica todas as regras do
  registro **na partida** e aborta antes de chamar o LLM — nunca um contexto sem âncora
  em silêncio.

### Ajuste em `rag/indice.py`

O `Buscador` de hoje devolve `Trecho` (só `texto`, `id_pagina`, `ancora`) — falta URL e
título para o contexto — e `carregar_buscador()` carrega o `bge-small` e o Chroma mesmo
quando a busca é BM25. Nova classe **`BaseRag`**:

- `BaseRag.carregar(pasta_indice=..., pasta_chroma=..., embedder=None)`: lê
  `config.json` e `trechos.jsonl`; o embedder e a coleção Chroma só são carregados se a
  busca da configuração não for `"bm25"`.
- `buscar(consulta, k) -> list[TrechoIndexado]`.
- `trecho_ancora(id_pagina, ancora, frase_marca) -> TrechoIndexado`, ou `ErroDeIndice`.

`carregar_buscador()` passa a ser um invólucro (`[t.para_regua() for t in base.buscar(...)]`);
o teste que reproduz a macro acerto@5 continua passando sem mudança.

## 5. Prompt (`core/analise/prompt.py`)

Duas mensagens para `/api/chat`:

- **Sistema**: auditor de modelos Power BI; o problema já foi detectado por uma regra
  determinística e o modelo **não** decide se ele existe; usar **só** os trechos
  fornecidos; citar de 1 a 3 números de trecho que sustentam a explicação; responder em
  português do Brasil; explicação e recomendação curtas e acionáveis (até ~120 palavras
  no total, como no spike).
- **Usuário**: título e categoria da regra; objeto (tipo e nome); `mensagem` do achado;
  `trecho` de DAX/M, cortado em 1.500 caracteres com a marca `[…]`; `detalhe` em JSON;
  e os trechos numerados, cada um como `[n] Título › caminho` seguido do texto. Os
  trechos ficam em inglês (o corpus é inglês, ADR-002 C-6).

## 6. Cliente do LLM (`core/analise/llm.py`)

- Protocolo `LLMClient`: `nome: str`; `gerar(mensagens, esquema) -> RespostaLLM` com
  `texto: str` e `segundos: float`. Levanta `ErroDeLLM` em falha de rede, HTTP ou timeout.
- `ClienteOllama(modelo, url="http://127.0.0.1:11434")`, via `urllib` (como o spike, sem
  dependência nova): `POST /api/chat` com `stream: false`, `format` = esquema,
  `options`: `num_ctx=4096`, **`temperature=0`, `seed=42`** — a rodada fica
  reproduzível, o que a avaliação acadêmica pede (o spike usou 0,2). Timeout de 120 s.
- `aquecer()`: uma chamada curta por execução, fora da medição de tempo (ressalva de
  método do spike: a carga do modelo para a VRAM não é custo por achado).
- Esquema: objeto com `explicacao` (string), `recomendacao` (string) e `citacoes`
  (array de inteiros, `minItems` 1, `maxItems` 3), todos obrigatórios.

## 7. Validação (`core/analise/validacao.py`)

A primeira falha decide o motivo:

1. texto não é JSON, ou falta campo, ou tipo errado → `json_invalido`
2. `explicacao` ou `recomendacao` vazia após `strip` → `campo_vazio`
3. `citacoes` com 0 ou mais de 3 itens, ou com repetição → `citacoes_fora_do_limite`
4. algum número fora de `1..len(contexto)` → `citacao_inexistente`

`ErroDeLLM` na chamada → `erro_llm`. Passou nas quatro: `situacao = "gerado"`,
`cita_ancora = 1 in citacoes`. A validação não confia no esquema do Ollama: os limites
de itens podem não ser respeitados pela decodificação restrita, então o código confere
de novo.

## 8. Fidelidade (`core/analise/fidelidade.py`)

Sobre `explicacao` + `recomendacao`, extrai:

- **números em algarismos** (`4`, `35`, `12,5`, `12.5`);
- **números por extenso de dois a dez** (`dois`/`duas`, `três`, …, `dez`), convertidos
  em algarismo — `um`/`uma` ficam de fora porque são artigos;
- **nomes de objeto**: padrões `Tabela[Coluna]`, `[Medida]` e texto entre aspas simples,
  duplas ou crases.

Cada item precisa aparecer no **achado** (`mensagem`, `evidencia.objeto`,
`evidencia.tabela`, `evidencia.trecho`, `evidencia.detalhe` serializado em JSON) ou em
**algum trecho do contexto**. Números comparam como número (`12,5` = `12.5`); nomes
comparam sem diferenciar maiúsculas. O que não aparece vira uma entrada em
`divergencias`, por exemplo `"número 2 ausente do achado e dos trechos"`.

**Limitação declarada**: heurística de superfície. Não pega erro de sentido com números
certos e pode acusar um número derivado corretamente (8 − 4 = 4). Por isso registra e
não descarta; a Fase 5 lê as divergências.

## 9. Orquestração e comando (`core/auditoria.py`)

- `run_audit(pasta_pbip, *, llm: LLMClient, base: BaseRag, registro=REGISTRO, gabaritos=...) -> ResultadoAuditoria`.
- `ResultadoAuditoria`: `projeto` (nome da pasta), `modelo_llm`, `gerado_em` (ISO),
  `regras` (`ResultadoRegras` sem os achados — falhas, lacunas de DAX e cobertura
  continuam visíveis), `achados: list[AchadoEnriquecido]` e `segundos_total`.
- Comando: `python -m core.auditoria <pasta-pbip> [--modelo qwen2.5:7b-instruct-q4_K_M]`.
  Grava `outputs/<projeto>-<AAAA-MM-DD>.json` e imprime um resumo em ASCII (o console
  do Windows já quebrou o resumo do índice): N achados; gerados; sem fundamentação por
  motivo; quantos citam a âncora; quantos têm divergência de fidelidade; tempo médio por
  achado.

### Erros

| Situação | Comportamento |
|---|---|
| Ollama não responde no aquecimento | Aborta com mensagem clara, código 1 — em vez de 100 achados todos com `erro_llm` |
| Índice ausente, regra sem gabarito ou âncora ausente | Aborta na partida, antes de chamar o LLM |
| `ErroDeLLM` num achado | `erro_llm` naquele achado; a execução segue |
| PBIP inválido | `ErroEstruturaPbip` de `core.ingest`, mensagem e código 1 |

## 10. Testes

TDD, sem rede nem índice real na suíte padrão:

- `FakeLLM` com respostas roteirizadas e uma `BaseRag` montada a partir de trechos
  sintéticos.
- **Validação**: um teste por motivo de descarte, mais o caso aceito com e sem âncora.
- **Fidelidade**: "duas" contra uma evidência que diz 4 (o caso do spike); número
  presente só num trecho, aceito; `12,5` contra `12.5`; nome com maiúsculas trocadas;
  "uma tabela" não gera divergência.
- **Contexto**: âncora em [1]; sem duplicata; corte pelo orçamento com pulo para o
  próximo; parte certa de uma seção partida; `ErroDeContexto` sem gabarito.
- **`BaseRag`**: BM25 não carrega embedder (embedder falso que falha se chamado);
  `carregar_buscador` segue reproduzindo o resultado antigo.
- **`ClienteOllama`**: `urlopen` substituído; confere o corpo (`format`, `num_ctx`,
  `temperature`, `seed`, `stream`) e o `ErroDeLLM` em timeout.
- **`AchadoEnriquecido`**: invariantes; `recomendacao_final` nos dois casos.
- **`run_audit`** de ponta a ponta com o falso sobre um PBIP de teste; aborto de
  partida; aborto no aquecimento.
- Um teste real contra o Ollama, com marcador `ollama`, pulado quando ele não responde.

## 11. Entrega e registro

Rodar `python -m core.auditoria data/pbip/P8_contoso-vendas` com o 7B e registrar no
progress-log: número de achados, taxa de citação válida, taxa de citação da âncora,
achados com divergência de fidelidade, tempo médio e pior por achado. Ler à mão uma
amostra das respostas — o spike mostrou que os critérios automáticos não pegam tudo.

## 12. Fora do escopo

Interface (F12), relatório HTML/PDF (F13, F14), cache do LLM (F16), medição sobre
P1–P7 (Fase 5), nova tentativa após descarte, troca para a busca híbrida (só se os
trechos complementares se mostrarem fracos, emenda de 11/10 da ADR-002).
