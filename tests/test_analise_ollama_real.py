"""Uma geração de verdade contra o Ollama local, com o modelo principal.

Pulado quando o Ollama não responde ou o modelo não está baixado: a suíte padrão
não depende de GPU. Quando roda, confirma que o esquema imposto e o prompt
produzem uma resposta que passa na validação.
"""

import json
import urllib.request

import pytest

from core.analise.llm import MODELO_PADRAO, URL_OLLAMA, ClienteOllama
from core.analise.prompt import ESQUEMA, montar_mensagens
from core.analise.validacao import validar
from fabricas_analise import achado, contexto, meta


def _modelo_disponivel() -> bool:
    try:
        with urllib.request.urlopen(f"{URL_OLLAMA}/api/tags", timeout=2) as resposta:
            modelos = json.loads(resposta.read()).get("models", [])
    except OSError:
        return False
    return any(m.get("name") == MODELO_PADRAO for m in modelos)


pytestmark = [
    pytest.mark.ollama,
    pytest.mark.skipif(not _modelo_disponivel(), reason=f"Ollama ou {MODELO_PADRAO} indisponível"),
]


def test_geracao_real_passa_na_validacao():
    ctx = contexto(2)
    cliente = ClienteOllama()
    cliente.aquecer()
    resposta = cliente.gerar(montar_mensagens(meta(), achado(), ctx), ESQUEMA)
    geracao, motivo = validar(resposta.texto, len(ctx))
    assert motivo is None, resposta.texto
    assert geracao.citacoes
