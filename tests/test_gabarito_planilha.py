"""Planilha de anotação: cega, protegida, com lista suspensa."""

import pytest
from openpyxl import load_workbook

from gabarito.candidatos import COLUNAS_DE_FATOS, Candidato, ErroDeGabarito
from gabarito.planilha import LINHA_CABECALHO, PERGUNTAS, gerar_planilha


def _candidatos():
    return [
        Candidato(id_regra="MOD-002", projeto="P1", objeto="Vendas[Produto] → Produto[Produto]",
                  fatos={"direcao": "ambos_sentidos", "cardinalidades": "muitos:um", "ativo": "sim"}),
        Candidato(id_regra="PERF-001", projeto="P3", objeto="Pessoa[Salário]",
                  fatos={"expressao": "Pessoa[Base] * 1.1"}),
    ]


def _ids_da_aba(aba):
    return [aba.cell(row=r, column=1).value for r in range(LINHA_CABECALHO + 1, aba.max_row + 1)]


def test_uma_aba_por_regra_mais_instrucoes(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    livro = load_workbook(destino)
    assert livro.sheetnames == ["Instruções", *sorted(COLUNAS_DE_FATOS)]


def test_pergunta_no_topo_e_cabecalho_com_os_fatos(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    assert aba["A1"].value == PERGUNTAS["MOD-002"]
    assert aba["A2"].value.startswith("https://learn.microsoft.com/")
    cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
    assert cabecalho == ["id", "projeto", "objeto", "direcao", "cardinalidades", "ativo", "veredito", "justificativa", "referencia"]


def test_id_com_caracteres_especiais_volta_identico(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    livro = load_workbook(destino)
    assert _ids_da_aba(livro["MOD-002"]) == ["MOD-002|P1|Vendas[Produto] → Produto[Produto]"]
    assert _ids_da_aba(livro["PERF-001"]) == ["PERF-001|P3|Pessoa[Salário]"]


def test_veredito_tem_lista_suspensa(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    validacoes = aba.data_validations.dataValidation
    assert len(validacoes) == 1
    assert validacoes[0].formula1 == '"viola,não viola,indeterminado"'
    assert "G5" in str(validacoes[0].sqref)


def test_aba_protegida_com_so_as_colunas_de_anotacao_livres(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    assert aba.protection.sheet is True
    assert aba["A5"].protection.locked is True
    assert [aba.cell(row=5, column=c).protection.locked for c in (7, 8, 9)] == [False, False, False]


def test_planilha_e_cega(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    valores = [
        str(celula.value).strip().lower()
        for aba in load_workbook(destino).worksheets
        for linha in aba.iter_rows()
        for celula in linha
        if celula.value is not None
    ]
    textos = " ".join(valores)
    for proibido in ("severidade", "achado", "mensagem"):
        assert proibido not in textos, proibido
    assert not {"alta", "media", "média", "baixa"} & set(valores)


def test_recusa_sobrescrever(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    with pytest.raises(ErroDeGabarito, match="já existe"):
        gerar_planilha(_candidatos(), destino)
