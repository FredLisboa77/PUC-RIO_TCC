"""A planilha de anotação do gabarito (`.xlsx`) e o CSV oficial.

A planilha é cega: lista todos os candidatos com os mesmos fatos neutros, sem
dizer quais a ferramenta marcou. Fica protegida, com só as colunas de anotação
livres, para que um fato ou um ID não seja editado por engano.
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.worksheet.datavalidation import DataValidation

import core.rules.todas  # noqa: F401 — registra as regras
from core.rules.registry import REGISTRO
from gabarito.candidatos import COLUNAS_DE_FATOS, Candidato, ErroDeGabarito

VEREDITOS = ("viola", "não viola", "indeterminado")
COLUNAS_EDITAVEIS = ("veredito", "justificativa", "referencia")
LINHA_CABECALHO = 4

PERGUNTAS = {
    "MOD-001": "Esta tabela foi gerada pelo Tempo automático de data/hora?",
    "MOD-002": "Este relacionamento filtra nos dois sentidos sem que o cenário exija isso, segundo a orientação de relacionamentos bidirecionais?",
    "MOD-003": "Esta tabela deveria se relacionar com o resto do modelo, segundo o star schema? (Tabela de medidas ou de parâmetros isolada de propósito: não viola.)",
    "MOD-005": "Esta tabela funciona como dimensão de data e não está marcada como tabela de data?",
    "MOD-006": "Esta tabela é o elo intermediário de uma dimensão em floco de neve que deveria ser desnormalizada?",
    "MOD-007": "Este relacionamento é um-para-um entre tabelas que descrevem a mesma entidade?",
    "PERF-001": "Esta coluna calculada poderia ser criada no Power Query ou na origem, como a orientação de redução de dados recomenda?",
    "PERF-003": "Esta coluna de ponto flutuante é somada de forma que a imprecisão do tipo possa afetar o resultado?",
    "DAX-001": "Alguma divisão desta expressão tem denominador que pode ser zero ou BLANK, caso em que a documentação recomenda DIVIDE?",
}

INSTRUCOES = [
    "Gabarito das regras em P1–P7 — protocolo de anotação",
    "",
    "1. Julgue cada linha pela pergunta no topo da aba e pela página do Learn indicada, não por preferência pessoal.",
    "2. veredito: 'viola', 'não viola' ou 'indeterminado' (use a lista suspensa).",
    "3. 'indeterminado' só quando o modelo não traz a informação necessária (ex.: a distribuição dos valores de uma coluna).",
    "4. Justificativa obrigatória em 'viola' e 'indeterminado'.",
    "5. Referência: a URL de qualquer fonte usada além da página indicada no topo da aba.",
    "6. A planilha não mostra o que a ferramenta decidiu, de propósito: o julgamento é cego.",
    "7. Para conferir o andamento: python -m gabarito importar --parcial",
]


def _aba_de_regra(livro: Workbook, id_regra: str, candidatos: list[Candidato]) -> None:
    aba = livro.create_sheet(id_regra)
    aba["A1"] = PERGUNTAS[id_regra]
    aba["A1"].font = Font(bold=True)
    aba["A2"] = REGISTRO.meta(id_regra).url_canonica
    cabecalho = ["id", "projeto", "objeto", *COLUNAS_DE_FATOS[id_regra], *COLUNAS_EDITAVEIS]
    for coluna, nome in enumerate(cabecalho, start=1):
        celula = aba.cell(row=LINHA_CABECALHO, column=coluna, value=nome)
        celula.font = Font(bold=True)

    primeira_editavel = len(cabecalho) - len(COLUNAS_EDITAVEIS) + 1
    linhas = sorted(candidatos, key=lambda c: (c.projeto, c.objeto))
    for i, c in enumerate(linhas, start=LINHA_CABECALHO + 1):
        valores = [c.id, c.projeto, c.objeto, *(c.fatos[f] for f in COLUNAS_DE_FATOS[id_regra])]
        for coluna, valor in enumerate(valores, start=1):
            aba.cell(row=i, column=coluna, value=valor).alignment = Alignment(wrap_text=True, vertical="top")
        for coluna in range(primeira_editavel, len(cabecalho) + 1):
            aba.cell(row=i, column=coluna).protection = Protection(locked=False)

    if linhas:
        letra = aba.cell(row=LINHA_CABECALHO, column=primeira_editavel).column_letter
        validacao = DataValidation(type="list", formula1=f'"{",".join(VEREDITOS)}"', allow_blank=True)
        validacao.add(f"{letra}{LINHA_CABECALHO + 1}:{letra}{LINHA_CABECALHO + len(linhas)}")
        aba.add_data_validation(validacao)
    aba.freeze_panes = aba.cell(row=LINHA_CABECALHO + 1, column=4)
    aba.protection.sheet = True


def gerar_planilha(candidatos: list[Candidato], destino: Path) -> None:
    if destino.exists():
        raise ErroDeGabarito(f"{destino} já existe e pode ter vereditos — apague ou renomeie antes de gerar outra")
    livro = Workbook()
    instrucoes = livro.active
    instrucoes.title = "Instruções"
    for i, linha in enumerate(INSTRUCOES, start=1):
        instrucoes.cell(row=i, column=1, value=linha)
    for id_regra in sorted(COLUNAS_DE_FATOS):
        _aba_de_regra(livro, id_regra, [c for c in candidatos if c.id_regra == id_regra])
    destino.parent.mkdir(parents=True, exist_ok=True)
    livro.save(destino)
