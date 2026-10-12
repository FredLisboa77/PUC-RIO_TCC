"""Fidelidade à evidência: números e nomes da resposta precisam ter origem."""

from pathlib import Path

from core.analise.base import Geracao
from core.analise.fidelidade import verificar_fidelidade
from fabricas_analise import achado, contexto, trecho_de_contexto


def _divergencias(explicacao, recomendacao="Desative a opção.", *, a=None, ctx=None):
    geracao = Geracao(explicacao=explicacao, recomendacao=recomendacao, citacoes=[1])
    return verificar_fidelidade(geracao, a or achado(), ctx or contexto(1)).divergencias


def test_numero_por_extenso_errado_e_divergencia():
    # O caso do spike de 29/09: a evidência dizia 4 tabelas, o 3B escreveu "duas".
    assert _divergencias("O modelo tem duas tabelas de data automáticas.") == [
        "número 2 ausente do achado e dos trechos"
    ]


def test_numero_certo_nao_diverge():
    assert _divergencias("O modelo tem quatro tabelas automáticas.") == []
    assert _divergencias("O modelo tem 4 tabelas automáticas.") == []


def test_numero_presente_so_no_trecho_e_aceito():
    ctx = [trecho_de_contexto(1, "Each hidden table adds 7 columns.")]
    assert _divergencias("Cada tabela oculta tem 7 colunas.", ctx=ctx) == []


def test_numero_por_extenso_em_ingles_no_trecho_e_aceito():
    ctx = [trecho_de_contexto(1, "It creates three hidden tables.")]
    assert _divergencias("Cria três tabelas ocultas.", ctx=ctx) == []


def test_decimal_com_virgula_casa_com_ponto():
    a = achado(mensagem="A coluna ocupa 12.5 MB.")
    assert _divergencias("A coluna ocupa 12,5 MB.", a=a) == []


def test_um_e_uma_nao_sao_numeros():
    assert _divergencias("Uma tabela de datas resolve um problema.") == []


def test_numero_dentro_de_nome_nao_e_extraido():
    a = achado(objeto="LocalDateTable_1", mensagem="A tabela 'LocalDateTable_1' é automática.")
    assert _divergencias("A tabela LocalDateTable_1 é automática.", a=a) == []


def test_nome_com_maiusculas_trocadas_e_aceito():
    a = achado(objeto="Vendas[Total]", tipo_objeto="medida", mensagem="A medida Vendas[Total] divide com /.")
    assert _divergencias("A medida vendas[TOTAL] usa o operador /.", a=a) == []


def test_nome_inventado_e_divergencia():
    assert _divergencias("Corrija a medida [Margem].") == ["nome [Margem] ausente do achado e dos trechos"]


def test_nome_entre_aspas_presente_no_achado_e_aceito():
    a = achado(objeto="DateTableTemplate_0eab", mensagem="A tabela oculta 'DateTableTemplate_0eab' foi gerada.")
    assert _divergencias("A tabela ‘DateTableTemplate_0eab’ é automática.", a=a) == []


def test_detalhe_nao_serializavel_nao_quebra():
    a = achado(detalhe={"caminho": Path("x/y"), "conjunto": {3}})
    assert _divergencias("Há 3 itens.", a=a) == []


def test_divergencias_nao_se_repetem():
    assert _divergencias("Duas tabelas e duas colunas.") == ["número 2 ausente do achado e dos trechos"]
