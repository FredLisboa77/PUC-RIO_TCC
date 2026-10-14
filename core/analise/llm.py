"""Cliente do LLM (ADR-002): Ollama local, atrás de um protocolo.

O protocolo deixa os testes rodarem com um LLM falso e mantém aberta a troca por
uma API paga sem mexer no resto do pipeline. Temperatura 0 e semente fixa: a
mesma auditoria repetida dá a mesma resposta, o que a avaliação acadêmica pede
(o spike usou 0,2).
"""

import http.client
import json
import time
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel

URL_OLLAMA = "http://127.0.0.1:11434"
MODELO_PADRAO = "qwen2.5:7b-instruct-q4_K_M"
NUM_CTX = 4096
"""O 7B em Q4_K_M ocupa ~5,3 GB dos 6 GB de VRAM com este contexto (spike de
29/09); aumentá-lo empurraria camadas para a CPU."""
SEED = 42
TIMEOUT_S = 120


class ErroDeLLM(Exception):
    """O LLM não respondeu, ou respondeu algo que não é uma resposta do chat."""


class ContextoExcedido(ErroDeLLM):
    """O prompt, ou o prompt mais a resposta, não cabe no `num_ctx`.

    Por padrão o Ollama corta o prompt em silêncio e informa só o tamanho já
    cortado — medido em 11/10: 7.231 tokens viraram 2.050 e a instrução de sistema
    se perdeu. Com `truncate` e `shift` desligados ele recusa ou para no limite, e
    quem chama decide o que tirar do contexto."""


class RespostaLLM(BaseModel):
    texto: str
    segundos: float
    tokens_prompt: int | None = None
    """O `prompt_eval_count` do Ollama, quando ele informa."""
    do_cache: bool = False
    """Veio de `ClienteComCache`, não de uma chamada ao modelo."""


class LLMClient(Protocol):
    nome: str

    def aquecer(self) -> None: ...

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM: ...


class ClienteOllama:
    def __init__(self, modelo: str = MODELO_PADRAO, url: str = URL_OLLAMA, timeout: float = TIMEOUT_S) -> None:
        self.nome = modelo
        self.url = url
        self.timeout = timeout

    def _corpo(self, mensagens: list[dict[str, str]], esquema: dict | None = None) -> dict:
        corpo = {
            "model": self.nome,
            "messages": mensagens,
            "stream": False,
            "truncate": False,
            "shift": False,
            "options": {"num_ctx": NUM_CTX, "temperature": 0, "seed": SEED},
        }
        if esquema is not None:
            corpo["format"] = esquema
        return corpo

    def _chamar(self, corpo: dict) -> dict:
        pedido = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                return json.loads(resposta.read())
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", "replace")
            if erro.code == 400 and "exceed" in detalhe:
                raise ContextoExcedido(
                    f"o prompt não cabe no contexto de {NUM_CTX} tokens: {detalhe[:200]}"
                ) from erro
            raise ErroDeLLM(
                f"o Ollama respondeu HTTP {erro.code} para o modelo {self.nome}: {detalhe[:200]}"
            ) from erro
        # URLError, recusa de conexão e timeout são OSError; leitura interrompida é
        # HTTPException. Nenhum deles pode derrubar a auditoria inteira.
        except (OSError, http.client.HTTPException) as erro:
            raise ErroDeLLM(f"o Ollama não respondeu em {self.url}: {erro!r}") from erro
        except ValueError as erro:  # JSON inválido ou bytes que não são UTF-8
            raise ErroDeLLM(f"o Ollama devolveu algo que não é JSON: {erro}") from erro

    def aquecer(self) -> None:
        """Carrega o modelo na VRAM fora da medição: a carga custa dezenas de
        segundos uma vez por sessão, não por achado (ressalva de método do spike)."""
        self._chamar(self._corpo([{"role": "user", "content": "Responda apenas: ok"}]))

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM:
        inicio = time.perf_counter()
        dados = self._chamar(self._corpo(mensagens, esquema))
        segundos = time.perf_counter() - inicio
        try:
            texto = dados["message"]["content"]
        except (KeyError, TypeError) as erro:
            raise ErroDeLLM("resposta do Ollama sem message.content") from erro
        if not isinstance(texto, str):
            raise ErroDeLLM("resposta do Ollama sem message.content em texto")
        if dados.get("done_reason") == "length":
            raise ContextoExcedido(f"a resposta foi cortada no limite de {NUM_CTX} tokens do contexto")
        return RespostaLLM(texto=texto, segundos=round(segundos, 2), tokens_prompt=dados.get("prompt_eval_count"))
