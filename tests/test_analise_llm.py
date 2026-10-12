"""Cliente do Ollama, com `urlopen` substituído: corpo enviado e falhas."""

import http.client
import io
import json
import urllib.error

import pytest

from core.analise import llm
from core.analise.llm import ClienteOllama, ContextoExcedido, ErroDeLLM


class LeituraInterrompida(io.BytesIO):
    def read(self, *args):
        raise http.client.IncompleteRead(b"{")


class UrlopenFalso:
    def __init__(self, resposta=None, erro=None, bruto=None, leitura_interrompida=False):
        self.resposta = resposta
        self.erro = erro
        self.bruto = bruto
        self.leitura_interrompida = leitura_interrompida
        self.pedidos = []

    def __call__(self, pedido, timeout):
        self.pedidos.append((pedido, timeout))
        if self.erro is not None:
            raise self.erro
        if self.leitura_interrompida:
            return LeituraInterrompida()
        if self.bruto is not None:
            return io.BytesIO(self.bruto)
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


def test_gerar_devolve_os_tokens_do_prompt(monkeypatch):
    _instalar(monkeypatch, resposta={"message": {"content": "{}"}, "prompt_eval_count": 1234})
    assert ClienteOllama().gerar([], {}).tokens_prompt == 1234


def test_sem_contagem_de_tokens_fica_none(monkeypatch):
    _instalar(monkeypatch, resposta={"message": {"content": "{}"}})
    assert ClienteOllama().gerar([], {}).tokens_prompt is None


def _http_400(mensagem: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", 400, "Bad Request", {}, io.BytesIO(mensagem))


def test_corpo_pede_para_nao_truncar_nem_deslocar_o_contexto(monkeypatch):
    # Sem isto o Ollama corta o prompt em silêncio e perde a instrução de sistema
    # (medido em 11/10: 7.231 tokens viraram 2.050).
    falso = _instalar(monkeypatch, resposta={"message": {"content": "{}"}})
    ClienteOllama().gerar([], {})
    corpo = json.loads(falso.pedidos[0][0].data)
    assert (corpo["truncate"], corpo["shift"]) == (False, False)


def test_prompt_maior_que_o_contexto_vira_contexto_excedido(monkeypatch):
    _instalar(monkeypatch, erro=_http_400(
        b'{"error":"request (7231 tokens) exceeds the available context size (4096 tokens)",'
        b'"type":"exceed_context_size_error"}'
    ))
    with pytest.raises(ContextoExcedido, match="7231"):
        ClienteOllama().gerar([], {})


def test_http_400_de_outro_tipo_nao_e_contexto_excedido(monkeypatch):
    _instalar(monkeypatch, erro=_http_400(b'{"error":"invalid format"}'))
    with pytest.raises(ErroDeLLM) as erro:
        ClienteOllama().gerar([], {})
    assert not isinstance(erro.value, ContextoExcedido)


def test_resposta_cortada_no_limite_do_contexto_vira_contexto_excedido(monkeypatch):
    _instalar(monkeypatch, resposta={"message": {"content": '{"explic'}, "done_reason": "length"})
    with pytest.raises(ContextoExcedido):
        ClienteOllama().gerar([], {})


def test_leitura_interrompida_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, leitura_interrompida=True)
    with pytest.raises(ErroDeLLM):
        ClienteOllama().gerar([], {})


def test_bytes_invalidos_viram_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, bruto=b'{"message": "' + bytes([0xE9]) + b'"}')
    with pytest.raises(ErroDeLLM):
        ClienteOllama().gerar([], {})


def test_conteudo_nulo_vira_erro_de_llm(monkeypatch):
    _instalar(monkeypatch, resposta={"message": {"content": None}})
    with pytest.raises(ErroDeLLM, match="message"):
        ClienteOllama().gerar([], {})
