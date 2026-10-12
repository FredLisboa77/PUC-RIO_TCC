"""Cliente do Ollama, com `urlopen` substituído: corpo enviado e falhas."""

import io
import json
import urllib.error

import pytest

from core.analise import llm
from core.analise.llm import ClienteOllama, ErroDeLLM


class UrlopenFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta
        self.erro = erro
        self.pedidos = []

    def __call__(self, pedido, timeout):
        self.pedidos.append((pedido, timeout))
        if self.erro is not None:
            raise self.erro
        return io.BytesIO(json.dumps(self.resposta).encode("utf-8"))


def _instalar(monkeypatch, **kw) -> UrlopenFalso:
    falso = UrlopenFalso(**kw)
    monkeypatch.setattr(llm.urllib.request, "urlopen", falso)
    return falso


def test_gerar_envia_esquema_contexto_temperatura_e_semente(monkeypatch):
    falso = _instalar(monkeypatch, resposta={"message": {"content": '{"a": 1}'}})
    resposta = ClienteOllama("qwen-teste").gerar([{"role": "user", "content": "oi"}], {"type": "object"})
    pedido, timeout = falso.pedidos[0]
    corpo = json.loads(pedido.data)
    assert pedido.full_url == "http://127.0.0.1:11434/api/chat"
    assert (corpo["model"], corpo["stream"], corpo["format"]) == ("qwen-teste", False, {"type": "object"})
    assert corpo["messages"] == [{"role": "user", "content": "oi"}]
    assert corpo["options"] == {"num_ctx": 4096, "temperature": 0, "seed": 42}
    assert timeout == 120
    assert resposta.texto == '{"a": 1}'
    assert resposta.segundos >= 0


def test_aquecer_nao_envia_esquema(monkeypatch):
    falso = _instalar(monkeypatch, resposta={"message": {"content": "ok"}})
    ClienteOllama().aquecer()
    assert "format" not in json.loads(falso.pedidos[0][0].data)


def test_timeout_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, erro=TimeoutError("timed out"))
    with pytest.raises(ErroDeLLM, match="não respondeu"):
        ClienteOllama().gerar([], {})


def test_conexao_recusada_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, erro=urllib.error.URLError("connection refused"))
    with pytest.raises(ErroDeLLM, match="não respondeu"):
        ClienteOllama().aquecer()


def test_modelo_ausente_nomeia_o_modelo(monkeypatch):
    corpo = io.BytesIO(b'{"error":"model \'qwen-x\' not found"}')
    _instalar(monkeypatch, erro=urllib.error.HTTPError("http://x", 404, "Not Found", {}, corpo))
    with pytest.raises(ErroDeLLM, match="404.*qwen-x"):
        ClienteOllama("qwen-x").aquecer()


def test_resposta_sem_conteudo_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, resposta={"done": True})
    with pytest.raises(ErroDeLLM, match="message"):
        ClienteOllama().gerar([], {})
