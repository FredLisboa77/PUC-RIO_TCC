"""Execução das regras.

Duas garantias que o resto do projeto depende: a ordem da saída é
determinística, porque a Fase 5 compara listas; e uma regra que explode não
derruba a auditoria, mas também não desaparece em silêncio.
"""

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.registry import Registro, regra
from core.rules.runner import avaliar

CAMPOS = {
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil.",
}


def _achado(id_regra: str, objeto: str) -> Achado:
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(tipo_objeto="tabela", objeto=objeto),
        mensagem=f"problema em {objeto}",
    )


def test_ordena_por_severidade_depois_id_depois_objeto():
    registro = Registro()

    @regra(id="MOD-902", severidade="baixa", registro=registro, **CAMPOS)
    def baixa(modelo):
        return [_achado("MOD-902", "Zebra"), _achado("MOD-902", "Alfa")]

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def alta(modelo):
        return [_achado("MOD-901", "Beta")]

    @regra(id="PERF-901", severidade="alta", registro=registro, **CAMPOS)
    def outra_alta(modelo):
        return [_achado("PERF-901", "Alfa")]

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert [(a.id_regra, a.evidencia.objeto) for a in resultado.achados] == [
        ("MOD-901", "Beta"),
        ("PERF-901", "Alfa"),
        ("MOD-902", "Alfa"),
        ("MOD-902", "Zebra"),
    ]
    assert resultado.regras_executadas == 3
    assert resultado.total_de_regras == 3


def test_isola_a_regra_que_levanta_excecao():
    registro = Registro()

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def explode(modelo):
        raise KeyError("propriedade inesperada")

    @regra(id="MOD-902", severidade="alta", registro=registro, **CAMPOS)
    def funciona(modelo):
        return [_achado("MOD-902", "DimProduct")]

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert [a.id_regra for a in resultado.achados] == ["MOD-902"]
    assert [f.id_regra for f in resultado.regras_com_falha] == ["MOD-901"]
    assert "KeyError" in resultado.regras_com_falha[0].erro
    assert resultado.regras_executadas == 1
    assert resultado.total_de_regras == 2


def test_isola_tambem_a_regra_geradora_que_explode_no_meio():
    """`yield` antes da exceção: o erro só aparece ao consumir o gerador."""
    registro = Registro()

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def explode_no_meio(modelo):
        yield _achado("MOD-901", "DimProduct")
        raise ValueError("estado inesperado")

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert resultado.achados == []
    assert [f.id_regra for f in resultado.regras_com_falha] == ["MOD-901"]


def test_registro_vazio_devolve_resultado_vazio():
    resultado = avaliar(ModeloSemantico(), registro=Registro())

    assert resultado.achados == []
    assert resultado.regras_com_falha == []
    assert resultado.total_de_regras == 0


# --- correções da revisão final ---


def test_isola_regra_que_rotula_achado_com_id_de_outra_regra():
    """A busca da severidade acontecia fora do isolamento.

    Um `id_regra` digitado errado no corpo da regra (MOD-9O1 com a letra O, por
    exemplo) levantava `KeyError` dentro do `sort` de `avaliar`, depois de todas
    as regras já terem rodado: em vez de uma regra isolada, a auditoria inteira
    morria com traceback.
    """
    registro = Registro()

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def rotula_errado(modelo):
        return [_achado("MOD-9O1", "DimProduct")]

    @regra(id="MOD-902", severidade="alta", registro=registro, **CAMPOS)
    def funciona(modelo):
        return [_achado("MOD-902", "DimStore")]

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert [a.id_regra for a in resultado.achados] == ["MOD-902"]
    assert [f.id_regra for f in resultado.regras_com_falha] == ["MOD-901"]
    assert "MOD-9O1" in resultado.regras_com_falha[0].erro
