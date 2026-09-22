# powerbi-ai-auditor

Ferramenta de IA para auditoria automatizada de projetos Power BI no formato **PBIP** (Power BI Project).

Trabalho de Conclusão de Curso — PUC-Rio.

## O que faz

Recebe um projeto PBIP (como `.zip` ou pasta local), lê o modelo semântico, detecta problemas de boas práticas em DAX, M, modelagem e performance estática, e gera para cada achado uma explicação e uma recomendação fundamentadas em documentação pública recuperada por RAG, com citação obrigatória da fonte.

O resultado aparece numa interface local e pode ser exportado em HTML e PDF.

## Estado atual

| Fase | Período | Status |
|---|---|---|
| **Fase 1 — Viabilidade e planejamento** | Semanas 1–2 | **Gate aprovado em 22/09/2026** |
| Fase 2 — Leitura do PBIP e regras | Semanas 3–4 | Não iniciada |
| Fase 3 — RAG e análise com LLM | Semanas 5–8 | Não iniciada |
| Fase 4 — Interface e relatório | Semanas 9–10 | Não iniciada |
| Fase 5 — Avaliação, documentação e banca | Semanas 11–13 | Não iniciada |

Nenhum código de produto foi escrito ainda. O planejamento completo está em [`docs/project/fase1-viabilidade-e-planejamento.md`](docs/project/fase1-viabilidade-e-planejamento.md).

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
```

## Nota sobre dados

`data/`, `outputs/`, `rag/store/` e `.env` estão no `.gitignore`. Arquivos `.pbix`, `.abf` e `.pbi/localSettings.json` nunca são versionados — podem conter dados, strings de conexão e caminhos locais.
