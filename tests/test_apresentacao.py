"""Consultas puras de apresentação (interface e relatório): avisos, tabela, filtros, resumo e painel."""

from core import apresentacao as consulta
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.apresentacao import Filtro
from core.auditoria import ResultadoAuditoria
from core.rules.base import RegraMeta
from core.rules.expressoes import LacunaDax
from core.rules.registry import Registro
from core.rules.runner import FalhaDeRegra, ResultadoRegras
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto


def _meta(id_regra: str, severidade: str, categoria: str) -> RegraMeta:
    return RegraMeta(
        id=id_regra, titulo=f"Título {id_regra}", categoria=categoria, severidade=severidade,
        url_canonica="https://learn.microsoft.com/x", termos_consulta=("t",),
        recomendacao_padrao=RECOMENDACAO_PADRAO,
    )


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(_meta("MOD-001", "media", "modelagem"), lambda m: [])
    registro.registrar(_meta("DAX-001", "alta", "dax"), lambda m: [])
    registro.registrar(_meta("PERF-001", "baixa", "performance"), lambda m: [])
    return registro


def _gerado(a, **extra) -> AchadoEnriquecido:
    campos = dict(
        achado=a, contexto=contexto(2),
        geracao=Geracao(explicacao="e", recomendacao="Use DIVIDE no lugar do operador.", citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m", segundos=1.0,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _descartado(a, motivo="json_invalido") -> AchadoEnriquecido:
    return AchadoEnriquecido(achado=a, contexto=contexto(1), situacao="sem_fundamentacao",
                             motivo_descarte=motivo, modelo="m")


def _resultado(achados, regras=None) -> ResultadoAuditoria:
    return ResultadoAuditoria(
        projeto="P", modelo_llm="m", gerado_em="2026-10-13T15:30:00",
        regras=regras or ResultadoRegras(regras_executadas=3, expressoes_analisadas=10),
        achados=achados, segundos_total=1.0,
    )


# --- avisos ---

def test_gerado_limpo_nao_tem_aviso():
    assert consulta.avisos(_gerado(achado())) == []


def test_cada_gatilho_gera_seu_aviso():
    def titulos(item):
        return [a.titulo for a in consulta.avisos(item)]

    divergente = _gerado(achado(), fidelidade=Fidelidade(divergencias=["42", "Vendas"]))
    assert titulos(_descartado(achado())) == ["Sem fundamentação — recomendação padrão da regra"]
    assert "não devolveu JSON válido" in consulta.avisos(_descartado(achado()))[0].explicacao
    assert titulos(divergente) == ["Divergência de fidelidade"]
    assert "42, Vendas" in consulta.avisos(divergente)[0].explicacao
    assert titulos(_gerado(achado(), cita_ancora=False)) == ["Não cita a seção âncora da regra"]
    assert titulos(_gerado(achado(), reducoes_de_contexto=2)) == ["Contexto reduzido para caber"]
    assert titulos(AchadoEnriquecido.so_regras(achado())) == ["Só regras — sem explicação do LLM"]


def test_todo_motivo_de_descarte_tem_frase():
    for motivo in ["json_invalido", "campo_vazio", "citacoes_fora_do_limite", "citacao_inexistente",
                   "erro_llm", "contexto_excedido"]:
        assert consulta.avisos(_descartado(achado(), motivo))[0].explicacao


# --- linhas, filtros, resumo ---

def _tres():
    return _resultado([
        _gerado(achado("MOD-001", objeto="B")),
        _gerado(achado("DAX-001", objeto="Medida", tipo_objeto="medida"), cita_ancora=False),
        _gerado(achado("MOD-001", objeto="A")),
    ])


def test_linhas_ordenadas_por_severidade_regra_e_objeto_com_indice_original():
    ls = consulta.linhas(_tres(), _registro())
    assert [(l.regra, l.objeto, l.indice) for l in ls] == [("DAX-001", "Medida", 1), ("MOD-001", "A", 2), ("MOD-001", "B", 0)]
    assert (ls[0].severidade, ls[0].categoria, ls[0].titulo, ls[0].aviso) == ("alta", "dax", "Título DAX-001", True)


def test_linha_sem_tabela_usa_o_travessao():
    a = achado()
    a.evidencia.tabela = None
    assert consulta.linhas(_resultado([_gerado(a)]), _registro())[0].tabela == consulta.SEM_TABELA


def test_filtro_vazio_nao_restringe_e_filtros_se_combinam():
    ls = consulta.linhas(_tres(), _registro())
    assert consulta.filtrar(ls, Filtro()) == ls
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(regras=frozenset({"MOD-001"})))] == ["A", "B"]
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(so_com_aviso=True))] == ["Medida"]
    assert consulta.filtrar(ls, Filtro(severidades=frozenset({"alta"}), categorias=frozenset({"modelagem"}))) == []
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(tabelas=frozenset({"A"})))] == ["A"]


def test_opcoes_de_filtro_em_ordem_de_severidade():
    opcoes = consulta.opcoes_de_filtro(consulta.linhas(_tres(), _registro()))
    assert opcoes["severidades"] == ["alta", "media"]
    assert opcoes["regras"] == ["DAX-001", "MOD-001"]
    assert opcoes["categorias"] == ["dax", "modelagem"]


def test_resumo_conta_severidade_categoria_e_aviso():
    r = consulta.resumir(consulta.linhas(_tres(), _registro()))
    assert (r.total, r.com_aviso) == (3, 1)
    assert r.por_severidade == {"alta": 1, "media": 2, "baixa": 0}
    assert r.por_categoria == {"dax": 1, "modelagem": 2}


# --- painel "o que foi examinado" ---

def test_examinado_sem_problema():
    e = consulta.examinado(_resultado([]))
    assert (e.regras, e.expressoes, e.falhas, e.lacunas) == (
        "3 de 3 regras executadas", "10 de 10 expressões DAX analisadas", [], [])


def test_examinado_com_falha_de_regra_e_lacuna():
    regras = ResultadoRegras(
        regras_executadas=2, regras_com_falha=[FalhaDeRegra(id_regra="MOD-003", erro="KeyError: 'x'")],
        expressoes_analisadas=9,
        lacunas_de_expressao=[LacunaDax(sitio="medida", objeto="[Total]", tabela="Vendas", posicao=12,
                                        trecho="SUM(", motivo="parêntese sem par")],
    )
    e = consulta.examinado(_resultado([], regras))
    assert e.regras == "2 de 3 regras executadas"
    assert e.falhas == ["MOD-003: KeyError: 'x'"]
    assert e.expressoes == "9 de 10 expressões DAX analisadas"
    assert e.lacunas == ["[Total] (medida, posição 12): parêntese sem par"]


def test_examinado_com_varredura_falha_e_sem_dax():
    falhou = consulta.examinado(_resultado([], ResultadoRegras(regras_executadas=3, falha_na_varredura="boom")))
    assert falhou.expressoes == "A varredura de DAX falhou (boom): as regras de texto não rodaram."
    sem_dax = consulta.examinado(_resultado([], ResultadoRegras(regras_executadas=3)))
    assert sem_dax.expressoes == "Nenhuma expressão DAX em escopo."


# --- escolha do achado do detalhe (Review Focus 3) ---

def test_escolher_cai_no_primeiro_quando_a_selecao_nao_cabe():
    ls = consulta.linhas(_tres(), _registro())
    assert consulta.escolher(ls, [2]) == ls[2]
    assert consulta.escolher(ls, []) == ls[0]
    assert consulta.escolher(ls[:2], [5]) == ls[0]
    assert consulta.escolher([], [0]) is None
