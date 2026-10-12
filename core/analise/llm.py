"""Cliente do LLM (ADR-002): Ollama local, atrás de um protocolo.

O protocolo deixa os testes rodarem com um LLM falso e mantém aberta a troca por
uma API paga sem mexer no resto do pipeline. Temperatura 0 e semente fixa: a
mesma auditoria repetida dá a mesma resposta, o que a avaliação acadêmica pede
(o spike usou 0,2).
"""

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
RESERVA_RESPOSTA = 512
LIMITE_PROMPT = NUM_CTX - RESERVA_RESPOSTA
"""Prompt a partir deste tamanho pode ter sido truncado: o Ollama corta o que passa
do `num_ctx` sem erro na API. O orçamento de contexto é em palavras, e trechos de
código chegam a ~3,4 tokens por palavra (revisão final de 11/10), então o tamanho
real só se sabe pela contagem que o Ollama devolve."""
SEED = 42
TIMEOUT_S = 120


class ErroDeLLM(Exception):
    """O LLM não respondeu, ou respondeu algo que não é uma resposta do chat."""


class RespostaLLM(BaseModel):
    texto: str
    segundos: float
    tokens_prompt: int | None = None
    """O `prompt_eval_count` do Ollama, quando ele informa."""


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
            detalhe = erro.read().decode("utf-8", "replace")[:200]
            raise ErroDeLLM(f"o Ollama respondeu HTTP {erro.code} para o modelo {self.nome}: {detalhe}") from erro
        except OSError as erro:  # URLError, recusa de conexão e timeout são OSError
            raise ErroDeLLM(f"o Ollama não respondeu em {self.url}: {erro}") from erro
        except json.JSONDecodeError as erro:
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
        return RespostaLLM(texto=texto, segundos=round(segundos, 2), tokens_prompt=dados.get("prompt_eval_count"))
