# powerbi-ai-auditor

Ferramenta de IA para auditoria automatizada de projetos Power BI no formato **PBIP** (Power BI Project).

Trabalho de Conclusão de Curso — PUC-Rio.

## O que faz

Recebe um projeto PBIP (como `.zip` ou pasta local), lê o modelo semântico, detecta problemas de boas práticas em DAX, M, modelagem e performance estática, e gera para cada achado uma explicação e uma recomendação fundamentadas em documentação pública recuperada por RAG, com citação obrigatória da fonte.

O resultado aparece numa interface local e pode ser exportado em HTML e PDF.

## Estado atual

| Fase | Período | Status |
|---|---|---|
| Fase 1 — Viabilidade e planejamento | Semanas 1–2 | **Concluída em 29/09/2026** — gate aprovado e spike de LLM validado |
| Fase 2 — Leitura do PBIP e regras | Semanas 3–4 | **Concluída em 08/10/2026** — ingestão, parser e motor de regras com 8 regras estruturais, com 2 pendências da semana 4 |
| **Fase 3 — RAG e análise com LLM** | Semanas 5–8 | **A iniciar** |
| Fase 4 — Interface e relatório | Semanas 9–10 | Não iniciada |
| Fase 5 — Avaliação, documentação e banca | Semanas 11–13 | Não iniciada |

O **resumo de andamento** — o que está pronto, o que ficou pendente e por quê — está em [`docs/project/status.md`](docs/project/status.md). O planejamento completo está em [`docs/project/fase1-viabilidade-e-planejamento.md`](docs/project/fase1-viabilidade-e-planejamento.md), e o histórico detalhado do trabalho em [`docs/project/progress-log.md`](docs/project/progress-log.md).

Já implementado: ingestão de PBIP (pasta ou `.zip`) com validação de estrutura, parser do `model.bim` para um modelo interno normalizado, e o motor de regras determinísticas com as 8 primeiras regras estruturais — 15 achados no PBIP real usado como estudo de caso. 101 testes passando.

Cada regra declara a página do Microsoft Learn que a sustenta, e `python -m core.rules.catalogo` imprime o catálogo. Regra sem essa âncora não entra no registro: a verificação das fontes antes de escrever código eliminou três das oito regras originalmente propostas, uma delas porque a página que a sustentaria recomendava justamente o que a regra marcaria como defeito.

## Decisões de arquitetura

| ADR | Assunto |
|---|---|
| [ADR-001](docs/adr/ADR-001-formato-model-bim.md) | Formato do modelo semântico: `model.bim` (TMSL), não TMDL |
| [ADR-002](docs/adr/ADR-002-stack-tecnologica.md) | Stack tecnológica, com o ambiente real medido |
| [ADR-003](docs/adr/ADR-003-orquestracao-sequencial-e-deteccao-hibrida.md) | Orquestração sequencial; as regras são a única fonte de achados |
| [ADR-004](docs/adr/ADR-004-coleta-da-base-rag.md) | Coleta da base RAG pelas páginas públicas do Microsoft Learn |
| [ADR-005](docs/adr/ADR-005-dataset-de-avaliacao.md) | Dataset de avaliação: amostras públicas da Microsoft (MIT) |

## Escopo

**Entra no MVP:** entrada em PBIP (TMSL), análise do modelo semântico, regras determinísticas, RAG sobre documentação pública versionada, geração de explicações com citação obrigatória, interface local, relatório HTML e PDF, avaliação quantitativa.

**Fora do MVP** (ver [`docs/project/backlog.md`](docs/project/backlog.md)): entrada em PBIX, suporte a TMDL, camada de relatório (`.Report`/PBIR), correção automática, multiagente, métricas em tempo de execução, reranking, autenticação e deploy.

## Stack

Python 3.11 · Streamlit · Pydantic · ChromaDB · sentence-transformers (`bge-small-en-v1.5`) · Ollama · Jinja2 + Playwright · pytest.

## Estrutura

```
app/       interface Streamlit
core/      leitura do PBIP, parsing, regras, análise
rag/       coleta, chunking, indexação, recuperação
reports/   templates HTML e exportação para PDF
tests/     testes e fixtures PBIP mínimos
eval/      ground truth, scripts e resultados da avaliação
docs/      academic/ (relatório), adr/ (decisões), project/ (log, backlog, riscos)
data/      projetos PBIP reais — ignorado no Git
outputs/   relatórios gerados — ignorado no Git
```

## Ambiente

Windows 11, Python 3.11.9. O ambiente virtual fica em `.venv/` na raiz do projeto.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Certificado do PyPI nesta máquina

O Norton intercepta TLS aqui: o certificado do PyPI chega emitido pela raiz "Norton Web/Mail Shield". O Windows confia nessa raiz, mas o `pip` usa o bundle do `certifi`, que não a contém — daí o erro `CERTIFICATE_VERIFY_FAILED`. A solução é apontar o `pip` para a mesma raiz que o sistema já confia, **sem** desabilitar a verificação:

```powershell
pip install -r requirements.txt --cert C:\ProgramData\Norton\Antivirus\wscert.pem
```

Para não repetir isso a cada comando, o arquivo `.venv/pip.ini` guarda essa configuração. Como o `.venv` não é versionado, ele precisa ser refeito se o ambiente for recriado.

### Modelo de linguagem

Ollama, com `qwen2.5:7b-instruct-q4_K_M` como modelo principal e `qwen2.5:3b` como contingência — escolhidos no spike de 29/09/2026 (resultado na [ADR-002](docs/adr/ADR-002-stack-tecnologica.md)).

```powershell
winget install --id Ollama.Ollama
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull qwen2.5:3b
```

**Antes do primeiro `pull`**, defina `OLLAMA_MODELS` apontando para um disco com espaço. Por padrão o Ollama grava em `C:\Users\<voce>\.ollama`, e os dois modelos somam 6,2 GB. Nesta máquina a variável aponta para `D:\dev\ollama-models` (risco R-14).

Para repetir o spike:

```powershell
python eval/spike_llm.py qwen2.5:3b qwen2.5:7b-instruct-q4_K_M
```

## Testes

```powershell
pytest
```

Os testes montam PBIP sintéticos em pasta temporária. Os nove testes que leem o PBIP real são **pulados** automaticamente quando `data/` não existe, que é o caso de qualquer cópia limpa do repositório — e com eles vai embora a rede de regressão das exclusões de escopo, que é o que trava as 15 ocorrências medidas.

## Nota sobre dados

`data/`, `outputs/`, `rag/store/` e `.env` estão no `.gitignore`. Arquivos `.pbix`, `.abf` e `.pbi/localSettings.json` nunca são versionados — podem conter dados, strings de conexão e caminhos locais.
