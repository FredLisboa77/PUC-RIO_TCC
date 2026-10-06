"""O registro de regras.

O parâmetro `registro` do decorador existe para os testes: sem ele, cada teste
sujaria o registro global e a ordem de execução passaria a importar.
"""

import pytest

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.registry import REGISTRO, Registro, RegraDuplicada, regra

CAMPOS = {
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "severidade": "baixa",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil.",
}


def test_registra_a_regra_e_devolve_a_funcao_intacta():
    registro = Registro()

    @regra(id="MOD-901", registro=registro, **CAMPOS)
    def minha_regra(modelo):
        yield Achado(
            id_regra="MOD-901",
            evidencia=Evidencia(tipo_objeto="modelo", objeto="modelo"),
            mensagem="achado de teste",
        )

    assert len(registro) == 1
    assert registro.ids() == ["MOD-901"]
    assert registro.meta("MOD-901").titulo == "Regra de teste"
    assert list(minha_regra(ModeloSemantico()))[0].id_regra == "MOD-901"
    assert registro.avaliador("MOD-901") is minha_regra


def test_recusa_id_duplicado():
    """Duplicar ID é erro na importação, não surpresa em execução."""
    registro = Registro()

    @regra(id="MOD-901", registro=registro, **CAMPOS)
    def primeira(modelo):
        return []

    with pytest.raises(RegraDuplicada, match="MOD-901"):

        @regra(id="MOD-901", registro=registro, **CAMPOS)
        def segunda(modelo):
            return []


def test_ids_saem_ordenados_independente_da_ordem_de_registro():
    registro = Registro()
    for id_regra in ("PERF-003", "MOD-002", "MOD-001"):

        @regra(id=id_regra, registro=registro, **CAMPOS)
        def qualquer(modelo):
            return []

    assert registro.ids() == ["MOD-001", "MOD-002", "PERF-003"]
    assert [m.id for m in registro.metas()] == ["MOD-001", "MOD-002", "PERF-003"]


def test_registro_global_existe_e_e_um_registro():
    assert isinstance(REGISTRO, Registro)
