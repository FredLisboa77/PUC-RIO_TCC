"""Relatório HTML: conteúdo, avisos, escape, seção técnica e autocontenção."""

import re

from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.auditoria import ResultadoAuditoria
from core.rules.base import RegraMeta
from core.rules.expressoes import LacunaDax
from core.rules.registry import Registro
from core.rules.runner import FalhaDeRegra, ResultadoRegras
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto
from reports.html import gerar_html

URL_REGRA = "https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time"


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(RegraMeta(
        id="MOD-001", titulo="Tempo automático de data/hora está ligado", categoria="modelagem",
        severidade="alta", url_canonica=URL_REGRA, termos_consulta=("t",), recomendacao_padrao=RECOMENDACAO_PADRAO,
    ), lambda m: [])
    return registro


def _gerado(objeto="LocalDateTable_1", **extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(objeto=objeto), contexto=contexto(2),
        geracao=Geracao(explicacao="A tabela automática aumenta o modelo.",
                        recomendacao="Desative a opção.", citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m", segundos=8.1, tokens_prompt=1200,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _resultado(achados, regras=None, **extra) -> ResultadoAuditoria:
    campos = dict(
        projeto="P8_contoso-vendas", modelo_llm="qwen", gerado_em="2026-10-13T19:45:31",
        regras=regras or ResultadoRegras(regras_executadas=1, expressoes_analisadas=105),
        achados=achados, segundos_total=155.1,
    )
    campos.update(extra)
    return ResultadoAuditoria(**campos)


def test_cabecalho_painel_resumo_e_achado():
    html = gerar_html(_resultado([_gerado()]), registro=_registro())
    assert "P8_contoso-vendas" in html
    assert "1 de 1 regras executadas" in html
    assert "105 de 105 expressões DAX analisadas" in html
    assert "não lê a camada de relatório" in html
    assert "A tabela automática aumenta o modelo." in html
    assert "Desative a opção." in html
    assert "Disable the auto date/time option." in html  # texto original do trecho citado
    assert 'href="#achado-1"' in html and 'id="achado-1"' in html


def test_avisos_aparecem():
    html = gerar_html(_resultado([
        _gerado(cita_ancora=False),
        AchadoEnriquecido(achado=achado(objeto="T2"), contexto=contexto(1), situacao="sem_fundamentacao",
                          motivo_descarte="json_invalido", modelo="m"),
    ]), registro=_registro())
    assert "Não cita a seção âncora da regra" in html
    assert "Sem fundamentação — recomendação padrão da regra" in html
    assert RECOMENDACAO_PADRAO in html


def test_so_regras_tem_selo_e_recomendacao_padrao():
    resultado = _resultado([AchadoEnriquecido.so_regras(achado())], modo="so_regras", modelo_llm=None)
    html = gerar_html(resultado, registro=_registro())
    assert "só regras" in html
    assert RECOMENDACAO_PADRAO in html
    assert "Fontes citadas" not in html


def test_falha_de_regra_lacuna_e_zero_achados():
    regras = ResultadoRegras(
        regras_executadas=0, regras_com_falha=[FalhaDeRegra(id_regra="MOD-001", erro="KeyError: 'x'")],
        expressoes_analisadas=9,
        lacunas_de_expressao=[LacunaDax(sitio="medida", objeto="[Total]", tabela="Vendas", posicao=12,
                                        trecho="SUM(", motivo="parêntese sem par")],
    )
    html = gerar_html(_resultado([], regras), registro=_registro())
    assert "MOD-001: KeyError" in html
    assert "[Total] (medida, posição 12): parêntese sem par" in html
    assert "Nenhum achado" in html


def test_escapa_html_vindo_do_modelo_e_do_llm():
    """Review Focus 4."""
    malicioso = _gerado(
        objeto="<script>alert(1)</script>",
        geracao=Geracao(explicacao='<img src=x onerror="alert(2)">', recomendacao="r", citacoes=[1]),
    )
    html = gerar_html(_resultado([malicioso]), registro=_registro())
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)" in html
    assert "<img src=x" not in html


def test_secao_tecnica_so_quando_pedida():
    resultado = _resultado([_gerado(do_cache=True)])
    sem = gerar_html(resultado, registro=_registro())
    com = gerar_html(resultado, tecnico=True, registro=_registro())
    assert "Seção técnica" not in sem and "Seção técnica" in com
    assert "1200" in com  # tokens
    assert "1 explicação(ões) vieram do cache" in sem


def test_links_em_portugues_e_nada_externo_alem_do_learn():
    html = gerar_html(_resultado([_gerado()]), registro=_registro())
    assert "https://learn.microsoft.com/pt-br/power-bi/guidance/auto-date-time" in html
    externos = re.findall(r'(?:src|href)="(?!#)([^"]+)"', html)
    assert externos and all(u.startswith("https://learn.microsoft.com/") for u in externos)
