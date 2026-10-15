# Monografia e README de entrega

- **Data:** 15/10/2026
- **Fase:** 5, semana 12 — segundo subprojeto da F5 (o primeiro, avaliação da geração, foi
  mergeado na `main` em `c4b4dc8`; o terceiro é a demonstração, semana 13)
- **Status:** Aguardando revisão do Fred
- **Depende de:** `eval/results/consolidado-2026-10-14.json` (fonte única das tabelas de
  resultado), `eval/results/regras-2026-10-12.json`, ADRs 001–005, `docs/project/progress-log.md`,
  `riscos.md`, `backlog.md`, `fase1-viabilidade-e-planejamento.md`
- **Branch:** `fase5-monografia`, criada a partir da `main` (`19944d5`)

## 1. Objetivo e enquadramento

Escrever a monografia do TCC e adequar o `README.md` do repositório ao modelo de entrega exigido
pelo curso. Os dois são entregáveis.

### Decisões do Fred nesta etapa

| Questão | Decisão |
|---|---|
| Formato | Livre, nas normas ABNT, entregue em PDF |
| Extensão | 30 a 50 páginas textuais (sem pré e pós-textuais); alvo de ~42 |
| Autoria | Claude rascunha cada capítulo; o Fred revisa e aprova capítulo a capítulo |
| Composição | **Typst**, instalado pelo pip (pacote `typst`), sem LaTeX nem Word |
| README | Reescrito no modelo da PUC-Rio (anexado pelo Fred em 15/10/2026), requisito de entrega |
| Estrutura e tese | Aprovadas como na seção 2 |

### Dados de identificação

| Campo | Valor |
|---|---|
| Título | Auditoria de projetos Power BI |
| Autor (capa e folha de rosto) | Carlos Frederico Coelho Lisboa |
| Orientadora | Evelyn C. S. Batista (sem link de GitHub) |
| Curso | Pós-Graduação *Inteligência Artificial Generativa & Large Language Models* (GenAI e LLM MASTER), PUC-Rio; disciplina "Projetos de Sistemas Inteligentes de Apoio à Decisão" |
| Matrícula | 251.100.867 |
| Repositório | https://github.com/FredLisboa77/PUC-RIO_TCC |

## 2. Argumento e estrutura

**Tese.** É possível auditar um projeto PBIP com regras determinísticas ancoradas na
documentação oficial e usar um LLM local só para *explicar* os achados, não para detectá-los. O
texto defende o rigor do método, não a cobertura: a contagem de regras é resultado do critério
de detectabilidade (a rejeição da PERF-005 é evidência do critério funcionando); a recuperação
entrega evidência pertinente em todos os achados; o gargalo medido é a geração do modelo de 7B;
e a conferência automática de fidelidade é declarada insuficiente.

| Cap. | Título e conteúdo | Pág. (alvo) | Fontes principais |
|---|---|---|---|
| — | Pré-textuais ABNT: capa, folha de rosto, resumo, abstract, listas de figuras e tabelas, lista de siglas, sumário | — | — |
| 1 | **Introdução** — contexto, problema, objetivo, contribuições, organização do texto | 4 | fase1, status |
| 2 | **Fundamentação e trabalhos relacionados** — PBIP/TMSL; boas práticas de modelagem (Microsoft Learn, Kimball); análise estática e o custo dos falsos positivos (Sadowski et al., 2018); RAG; LLM local e fidelidade; ferramentas existentes | 8 | backlog, specs da RAG, pesquisa verificada |
| 3 | **Método e arquitetura** — critério de detectabilidade (três testes); as 9 regras e suas âncoras; pipeline sequencial com detecção híbrida; base RAG e recuperação; geração com citação obrigatória; dataset (P1–P7, P8 como estudo de caso) | 11 | ADRs 001–005, specs |
| 4 | **Avaliação** — 4.1 regras (precisão 0,88 na tag `regras-gt`, Wilson por regra, análise de erros da MOD-003 e da PERF-001); 4.2 recuperação (24 combinações, seção + BM25); 4.3 geração (rubrica humana, kappa da conferência automática, padrões dos "não"); 4.4 estudo de caso P8 e desempenho | 12 | consolidado, regras-2026-10-12, progress-log |
| 5 | **Discussão e ameaças à validade** — um anotador; n pequeno por regra; efeito teto da recuperação; não determinismo do Ollama; escopo fora do MVP (TMDL, camada de relatório, PBIX, regras de M) | 5 | riscos, progress-log, fase1 |
| 6 | **Conclusão e trabalhos futuros** | 2 | — |
| Apênd. | A — catálogo das regras; B — rubrica da geração; C — como reproduzir os resultados | — | `core.rules.catalogo`, spec da avaliação |

## 3. Artefatos e organização

```
docs/academic/monografia/
  main.typ            pré-textuais + inclusão dos capítulos
  abnt.typ            estilo: A4, margens 3 cm (sup./esq.) e 2 cm (inf./dir.), 12 pt,
                      espaçamento 1,5, numeração contada da folha de rosto e impressa
                      a partir da Introdução, no canto superior direito
  capitulos/          01-introducao.typ … 06-conclusao.typ, apendices.typ
  referencias.bib     uma entrada por fonte conferida
  abnt.csl            estilo de citação autor-data ABNT, versionado
  gerado/             tabelas .typ produzidas por script — não editar à mão
docs/academic/monografia.pdf   PDF final versionado (alvo do link do README)
academico/            pacote Python
  python -m academico tabelas   lê os JSON de eval/results e escreve gerado/*.typ
  python -m academico pdf       compila main.typ em monografia.pdf
```

**Fonte única dos números.** Toda tabela de resultado sai de `python -m academico tabelas`.
Número no texto corrido é conferido contra o JSON antes do commit e cita o arquivo de origem
quando não vier de tabela.

**Testes** (no molde do teste do `sources.yaml`):
- os arquivos de `gerado/` são idênticos ao que o gerador produz a partir dos JSON;
- toda citação `@chave` dos capítulos existe em `referencias.bib`, e toda entrada do `.bib` é
  citada;
- `main.typ` compila sem erro (teste marcado como lento, se passar de alguns segundos).

## 4. README no modelo da PUC-Rio

Segue o modelo à risca, com os comentários de orientação removidos:

1. Título; aluno (link para o GitHub do Fred); orientadora (sem link); linha de co-orientação
   removida.
2. Frase do curso com o link do modelo.
3. Link para o código (o próprio repositório) e para a monografia (`docs/academic/monografia.pdf`).
   "Trabalhos relacionados" só se houver itens verificados no capítulo 2; caso contrário, removido.
4. Resumo e Abstract — os mesmos textos da monografia.
5. 1. Introdução · 2. Modelagem · 3. Resultados · 4. Conclusões — condensação dos capítulos
   (três a seis parágrafos cada); "Modelagem" corresponde ao capítulo 3; "Resultados" traz as
   três tabelas principais (regras, recuperação, geração), também geradas pelo script.
6. 5. Referências — as citadas no README, no formato ABNT.
7. 6. Instalação · 7. Como executar — o essencial do README atual.
8. Rodapé: matrícula, PUC-Rio, curso.

O conteúdo técnico do README atual que não couber em Instalação/Como executar (certificado do
Norton, `pip.ini`, `HF_HUB_OFFLINE`, comandos da avaliação, estrutura de pastas) vai para
`docs/project/ambiente.md`, linkado a partir do README. Nada é apagado.

O README é escrito **por último**, depois dos capítulos aprovados.

## 5. Processo e qualidade

**Ordem:** (1) infraestrutura — Typst, estilo ABNT, gerador de tabelas, testes; (2) capítulo 3;
(3) capítulo 4; (4) capítulo 2; (5) capítulo 5; (6) capítulo 1; (7) capítulo 6 e apêndices;
(8) resumo e abstract; (9) README e `ambiente.md`; (10) revisão de consistência de ponta a ponta
(números, nomes de regra, termos) e merge.

**Ciclo por capítulo:** rascunho → commit e push na `fase5-monografia` → PDF parcial compilado
entregue ao Fred → correções → o capítulo só conta como aprovado quando o Fred disser.

**Referências:** cada entrada do `.bib` é aberta e conferida na fonte (autor, ano, título,
local). Trabalho relacionado que não puder ser verificado não entra, e o Fred é avisado.

**Limitações declaradas:** as decisões já registradas no progress-log vão íntegras ao texto,
como a Fase 1 prometeu: um anotador só, P9 não acionado, BM25 mantido, MVP sem regras de M,
PERF-001 sem complementar pertinente, verificação de `filterExpression` de RLS pendente no
Desktop.

## 6. Fora do escopo

- Slides e roteiro da demonstração (subprojeto 3, semana 13).
- Código novo na ferramenta de auditoria.
- Reabrir decisões tomadas: segundo anotador, P9, escolha do BM25, regras de M.

## 7. Riscos

| Risco | Mitigação |
|---|---|
| O pacote `typst` do pip não instalar sob o Norton ou não trazer o compilador | Verificar na primeira tarefa; alternativa: binário oficial do Typst baixado com o bundle de certificados já usado no Hugging Face |
| CSL ABNT não suportada integralmente pelo Typst | Testar citação e lista de referências na primeira tarefa; alternativa: estilo de bibliografia embutido mais próximo, com ajuste manual documentado |
| Extensão estourar 50 páginas | Orçamento por capítulo da seção 2; contagem de páginas a cada PDF parcial |
| Referência de trabalho relacionado inverificável | Não entra; o capítulo 2 se apoia no que for conferido |
