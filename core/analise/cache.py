"""Cache das respostas do LLM (F16; spec de 13/10/2026, seção 4).

Uma auditoria repetida do mesmo projeto roda ao vivo em segundos e com os mesmos
textos. A chave cobre modelo, mensagens, esquema e opções de geração: qualquer
mudança no prompt — regra, contexto recuperado, texto do prompt — é outra chave,
e não há invalidação manual. Só respostas bem-sucedidas entram. `aquecer()` vai
sempre ao modelo real: com o Ollama fora do ar a auditoria aborta (ADR-003).
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from core.analise.llm import NUM_CTX, SEED, LLMClient, RespostaLLM
from rag.avaliacao import RAIZ_REPO

logger = logging.getLogger(__name__)

PASTA_CACHE = RAIZ_REPO / "outputs" / "cache-llm"


def chave_de(modelo: str, mensagens: list[dict[str, str]], esquema: dict) -> str:
    canonico = json.dumps(
        {
            "modelo": modelo,
            "mensagens": mensagens,
            "esquema": esquema,
            "opcoes": {"num_ctx": NUM_CTX, "temperature": 0, "seed": SEED},
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class ClienteComCache:
    def __init__(self, llm: LLMClient, pasta: Path = PASTA_CACHE) -> None:
        self.llm = llm
        self.pasta = pasta
        self.nome = llm.nome

    def aquecer(self) -> None:
        self.llm.aquecer()

    def _ler(self, arquivo: Path) -> dict | None:
        if not arquivo.is_file():
            return None
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            logger.warning("cache ilegível em %s, chamando o LLM: %s", arquivo.name, erro)
            return None
        if not isinstance(dados, dict) or not isinstance(dados.get("texto"), str):
            logger.warning("cache de outro formato em %s, chamando o LLM", arquivo.name)
            return None
        return dados

    def _gravar(self, arquivo: Path, resposta: RespostaLLM) -> None:
        dados = {
            "texto": resposta.texto,
            "tokens_prompt": resposta.tokens_prompt,
            "modelo": self.nome,
            "gravado_em": datetime.now().isoformat(timespec="seconds"),
        }
        temporario = arquivo.with_suffix(".tmp")
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            os.replace(temporario, arquivo)
        except OSError as erro:
            logger.warning("não consegui gravar o cache em %s: %s", self.pasta, erro)

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM:
        inicio = time.perf_counter()
        arquivo = self.pasta / f"{chave_de(self.nome, mensagens, esquema)}.json"
        guardada = self._ler(arquivo)
        if guardada is not None:
            return RespostaLLM(
                texto=guardada["texto"],
                segundos=round(time.perf_counter() - inicio, 2),
                tokens_prompt=guardada.get("tokens_prompt"),
                do_cache=True,
            )
        resposta = self.llm.gerar(mensagens, esquema)
        self._gravar(arquivo, resposta)
        return resposta
