"""Toda citação tem entrada no .bib e toda entrada é citada."""

from academico.citacoes import chaves_do_bib, citacoes, verificar

BIB = """
@article{sadowski2018,
  author = {Sadowski, Caitlin},
  year = {2018},
}
@online{learn-pbip, title = {PBIP}}
"""


def test_chaves_do_bib():
    assert chaves_do_bib(BIB) == {"sadowski2018", "learn-pbip"}


def test_citacoes_ignora_rotulos_de_tabela_e_secao():
    texto = """
    == Método <sec-metodo>
    Ver @sec-metodo e @tab-regras, segundo @sadowski2018 e #cite(<learn-pbip>, form: "prose").
    Contato: fred@exemplo.com. Escapado: \\@naocita.
    """
    tabela = "#figure(table())<tab-regras>"
    assert citacoes([texto, tabela]) == {"sadowski2018", "learn-pbip"}


def test_verificar_aponta_os_dois_sentidos(tmp_path):
    (tmp_path / "capitulos").mkdir()
    (tmp_path / "capitulos" / "c.typ").write_text("Segundo @sadowski2018 e @fantasma.", encoding="utf-8")
    (tmp_path / "referencias.bib").write_text(BIB, encoding="utf-8")
    v = verificar(tmp_path)
    assert v.sem_entrada == ["fantasma"]
    assert v.nao_citadas == ["learn-pbip"]


def test_verificar_sem_bib_e_sem_citacao_e_vazio(tmp_path):
    (tmp_path / "main.typ").write_text("Sem citações.", encoding="utf-8")
    assert verificar(tmp_path) == ([], [])


def test_monografia_sem_citacao_orfa():
    v = verificar()
    assert v.sem_entrada == [], f"citações sem entrada no .bib: {v.sem_entrada}"
    assert v.nao_citadas == [], f"entradas do .bib nunca citadas: {v.nao_citadas}"
