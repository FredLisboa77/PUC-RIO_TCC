"""Execução da auditoria para a interface — sem Streamlit.

Roda e grava, guarda o `.zip` enviado, lista e lê resultados salvos, traduz um
trecho, e converte cada falha da seção 4 da spec em `ErroParaUsuario`, cuja
mensagem vai direto para a tela. `criar_llm` e `carregar_base` são os pontos
de troca dos testes.
"""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core import auditoria
from core.analise.contexto import ErroDeContexto
from core.analise.llm import ClienteOllama, ErroDeLLM, LLMClient
from core.analise.traducao import ErroDeTraducao, traduzir_trecho
from core.auditoria import ErroDeAuditoria, ModoAuditoria, ResultadoAuditoria
from core.ingest import ErroEstruturaPbip
from core.rules.base import Achado
from core.rules.registry import Registro
from rag.indice import BaseRag, ErroDeIndice

COMANDO_INDICE = "python -m rag.indice construir"


class ErroParaUsuario(Exception):
    """Falha com a mensagem pronta para a tela."""


@dataclass
class Execucao:
    resultado: ResultadoAuditoria
    gravado_em: Path | None
    aviso_gravacao: str | None


def criar_llm(modelo: str) -> LLMClient:
    return ClienteOllama(modelo)


def carregar_base() -> BaseRag:
    return BaseRag.carregar()


def _base_nao_pronta(erro: Exception) -> ErroParaUsuario:
    return ErroParaUsuario(
        f"A base da RAG não está pronta ({erro}). Construa o índice com `{COMANDO_INDICE}` "
        "ou rode no modo só regras."
    )


def _base_pronta(obter_base: Callable[[], BaseRag]) -> BaseRag:
    try:
        return obter_base()
    except (ErroDeIndice, OSError, ValueError) as erro:
        raise _base_nao_pronta(erro) from erro


def executar(
    entrada: Path,
    modo: ModoAuditoria,
    modelo: str,
    *,
    ao_progredir: Callable[[int, int, Achado], None] | None = None,
    obter_base: Callable[[], BaseRag] | None = None,
) -> Execucao:
    try:
        if modo == "so_regras":
            resultado = auditoria.run_audit(entrada, llm=None, base=None, ao_progredir=ao_progredir)
        else:
            base = _base_pronta(obter_base or carregar_base)
            resultado = auditoria.run_audit(
                entrada, llm=criar_llm(modelo), base=base, ao_progredir=ao_progredir
            )
    except ErroEstruturaPbip as erro:
        raise ErroParaUsuario(f"Isto não é um projeto PBIP válido: {erro}") from erro
    except ErroDeAuditoria as erro:
        raise ErroParaUsuario(
            f"A auditoria completa não pôde começar: {erro}. Inicie o Ollama (`ollama serve`) "
            "ou rode no modo só regras."
        ) from erro
    except (ErroDeIndice, ErroDeContexto) as erro:
        raise _base_nao_pronta(erro) from erro
    except (ValueError, OSError) as erro:
        # `model.bim` corrompido (JSONDecodeError é ValueError) ou ilegível.
        raise ErroParaUsuario(f"Não consegui ler o projeto: {type(erro).__name__}: {erro}") from erro
    try:
        return Execucao(resultado, auditoria.gravar(resultado), None)
    except OSError as erro:
        # A geração já custou minutos: mostra o resultado mesmo sem gravar.
        return Execucao(resultado, None, f"O resultado não foi gravado em outputs/: {erro}")


def salvar_envio(nome: str, conteudo: bytes) -> Path:
    """Grava o `.zip` enviado com o nome original, para `nome_do_projeto` dar o
    nome do projeto. Só o nome final: um nome com caminho não sai da pasta."""
    pasta = Path(tempfile.mkdtemp(prefix="envio-"))
    caminho = pasta / Path(nome.replace("\\", "/")).name
    caminho.write_bytes(conteudo)
    return caminho


@dataclass(frozen=True)
class Salvo:
    caminho: Path
    rotulo: str


def listar_salvos(pasta: Path | None = None) -> list[Salvo]:
    """Pelo nome e pela data de modificação, sem abrir cada JSON: o Streamlit
    reexecuta o script a cada clique. Um JSON inválido vira mensagem ao abrir."""
    pasta = auditoria.PASTA_SAIDA if pasta is None else pasta
    if not pasta.is_dir():
        return []
    arquivos = sorted(pasta.glob("*.json"), key=lambda c: c.stat().st_mtime, reverse=True)
    return [Salvo(c, c.stem) for c in arquivos]


def ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria:
    try:
        resultado = ResultadoAuditoria.model_validate_json(conteudo)
    except ValidationError as erro:
        raise ErroParaUsuario(
            "O arquivo não é um resultado de auditoria desta ferramenta "
            f"({erro.error_count()} problema(s) no formato)."
        ) from erro
    registro = auditoria.REGISTRO if registro is None else registro
    desconhecidas = sorted({a.achado.id_regra for a in resultado.achados} - set(registro.ids()))
    if desconhecidas:
        raise ErroParaUsuario(
            f"O resultado tem regras que esta versão da ferramenta não conhece: {', '.join(desconhecidas)}."
        )
    return resultado


def traduzir(texto: str, modelo: str) -> str:
    try:
        return traduzir_trecho(texto, criar_llm(modelo))
    except (ErroDeLLM, ErroDeTraducao) as erro:
        raise ErroParaUsuario(f"Não consegui traduzir o trecho: {erro}") from erro
