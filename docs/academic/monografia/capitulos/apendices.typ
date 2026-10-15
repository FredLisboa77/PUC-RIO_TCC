#import "../abnt.typ": fonte

#set heading(
  numbering: (..n) => {
    let p = n.pos()
    if p.len() == 1 { "APÊNDICE " + numbering("A", p.first()) + " –" } else { numbering("A.1", ..p) }
  },
  supplement: [Apêndice],
)
#counter(heading).update(0)

= Catálogo das regras <apendice-a>

A tabela abaixo lista as nove regras da ferramenta, com a categoria, a severidade e o endereço da página do Microsoft Learn que ancora cada uma. A descrição de cada regra está na seção 3.4.

#include "../gerado/catalogo.typ"

= Rubrica da avaliação das explicações <apendice-b>

A rubrica foi aplicada a cada uma das 61 explicações geradas em P1 a P7, numa planilha que mostrava, para cada achado, a regra, o objeto, a mensagem da regra, a explicação, a recomendação, os trechos citados e, como referência, a passagem âncora da regra. A planilha não mostrava nenhum sinal automático da ferramenta: se a explicação citava a âncora, se a conferência automática acusara divergência, se a resposta viera do cache, nem os tempos de geração.

Cada explicação recebeu um veredito em cada um de três itens, com as opções "sim", "não" ou "indeterminado". A justificativa era obrigatória em todo "não". As definições, reproduzidas na aba de instruções da planilha, foram:

- *Pertinente*: pelo menos um trecho citado é de fato a passagem da documentação que sustenta o achado. Não basta o trecho existir entre os trechos fornecidos ao modelo.
- *Fiel*: o que a explicação afirma é sustentado pelos trechos citados ou pelos fatos do achado, sem nada inventado, seja número, nome ou comportamento.
- *Recomendação correta*: a recomendação resolve o problema neste modelo, sem erro técnico.

A partir dos três itens, uma explicação é *utilizável como está* quando recebe "sim" nos três. Um "não" em qualquer item torna a explicação não utilizável, mesmo que outro item seja indeterminado. Para cada item, a proporção principal é a fração de "sim" entre os casos decididos; o piso conta os indeterminados como "não" e o teto, como "sim". Na anotação realizada não houve casos indeterminados.

= Como reproduzir os resultados <apendice-c>

O código está no repositório público do trabalho (https://github.com/FredLisboa77/PUC-RIO_TCC). Os comandos abaixo são executados na raiz do repositório, com o ambiente virtual do Python 3.11 ativo.

== Ambiente

```
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct-q4_K_M
```

== Projetos avaliados

Os projetos P1 a P7 são amostras do repositório `microsoft/powerbi-desktop-samples`, sob licença MIT. Cada arquivo PBIX é aberto no Power BI Desktop, com o recurso de pré-visualização de armazenamento em TMDL desligado, e salvo como projeto do Power BI (`.pbip`) na pasta `data/pbip/`. A lista exata dos arquivos está em `eval/dataset.md`.

== Base de documentação e recuperação

```
python -m rag.catalogo        # catálogo de fontes
python -m rag.coleta          # coleta (cópia local)
python -m rag.extracao        # texto por seção
python -m rag.avaliacao gerar # consultas e gabaritos
python -m rag.medicao         # 24 combinações
python -m rag.indice construir
python -m rag.complementares medir
```

== Regras

```
python -m gabarito gerar      # planilha cega do gabarito
python -m gabarito importar   # grava o gabarito
python -m gabarito medir      # precisão e revocação por regra
```

O gabarito anotado já está versionado em `eval/ground_truth.csv`; para refazer só a medição, basta o último comando, executado na marca de versão `regras-gt` do repositório.

== Geração e consolidação

```
python -m avaliacao_geracao auditar     # auditoria de P1-P7 com cache
python -m avaliacao_geracao medir       # rubrica: taxas, Wilson e kappa
python -m avaliacao_geracao consolidar  # junta todos os resultados
```

Os vereditos da rubrica estão versionados em `eval/rubrica_geracao.csv`. Como o modelo de linguagem não é determinístico, uma nova rodada sem o cache original produz textos diferentes dos avaliados, e a rubrica precisaria ser aplicada de novo.

== Monografia

```
python -m academico tabelas   # tabelas a partir de eval/results/
python -m academico pdf       # compila este documento
```

Todas as tabelas de resultado deste documento são geradas pelo primeiro comando a partir do arquivo `eval/results/consolidado-2026-10-14.json`, e a suíte de testes do repositório falha se alguma delas divergir do arquivo de resultados.
