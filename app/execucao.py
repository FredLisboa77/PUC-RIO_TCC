"""Execução da auditoria para a interface — sem Streamlit.

Roda e grava, guarda o `.zip` enviado, lista e lê resultados salvos, traduz um
trecho, e converte cada falha da seção 4 da spec em `ErroParaUsuario`, cuja
mensagem vai direto para a tela. `criar_llm` e `carregar_base` são os pontos
de troca dos testes.
"""

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core import apresentacao, auditoria
from core.analise.cache import PASTA_CACHE, ClienteComCache
from core.analise.contexto import ErroDeContexto
from core.analise.llm import ClienteOllama, ErroDeLLM, LLMClient
from core.analise.traducao import ErroDeTraducao, traduzir_trecho
from core.auditoria import ErroDeAuditoria, ModoAuditoria, ResultadoAuditoria
from core.ingest import ErroEstruturaPbip
from core.rules.base import Achado
from core.rules.registry import Registro
from rag.indice import BaseRag, ErroDeIndice
from reports.html import gerar_html
from reports.pdf import ErroDePdf, gerar_pdf

COMANDO_INDICE = "python -m rag.indice construir"


class ErroParaUsuario(Exception):
    """Falha com a mensagem pronta para a tela."""


@dataclass
class Execucao:
    resultado: ResultadoAuditoria
    gravado_em: Path | None
    aviso_gravacao: str | None


def criar_llm(modelo: str, *, cache: bool = False) -> LLMClient:
    llm = ClienteOllama(modelo)
    return ClienteComCache(llm, PASTA_CACHE) if cache else llm


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
    cache: bool = False,
) -> Execucao:
    try:
        if modo == "so_regras":
            resultado = auditoria.run_audit(entrada, llm=None, base=None, ao_progredir=ao_progredir)
        else:
            base = _base_pronta(obter_base or carregar_base)
            resultado = auditoria.run_audit(
                entrada, llm=criar_llm(modelo, cache=cache), base=base, ao_progredir=ao_progredir
            )
    except ValidationError as erro:
        # É `ValueError`, mas aqui é bug do pipeline, não projeto ilegível.
        raise ErroParaUsuario(f"Erro inesperado na auditoria: {type(erro).__name__}: {erro}") from erro
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


def executar_envio(nome: str, conteudo: bytes, modo: ModoAuditoria, modelo: str, **kwargs) -> Execucao:
    """O `.zip` enviado vive só durante a auditoria: a pasta `envio-*` é apagada ao fim."""
    try:
        caminho = salvar_envio(nome, conteudo)
    except OSError as erro:
        raise ErroParaUsuario(f"Não consegui guardar o arquivo enviado: {erro}") from erro
    try:
        return executar(caminho, modo, modelo, **kwargs)
    finally:
        shutil.rmtree(caminho.parent, ignore_errors=True)


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
        return apresentacao.ler_resultado(conteudo, auditoria.REGISTRO if registro is None else registro)
    except apresentacao.ErroDeLeitura as erro:
        raise ErroParaUsuario(str(erro)) from erro


def ler_salvo(caminho: Path) -> ResultadoAuditoria:
    """O arquivo listado pode ter sumido entre a listagem e o clique."""
    try:
        conteudo = caminho.read_bytes()
    except OSError as erro:
        raise ErroParaUsuario(f"Não consegui abrir {caminho.name}: {erro}") from erro
    return ler_resultado(conteudo)


def traduzir(texto: str, modelo: str, *, cache: bool = False) -> str:
    try:
        return traduzir_trecho(texto, criar_llm(modelo, cache=cache))
    except (ErroDeLLM, ErroDeTraducao) as erro:
        raise ErroParaUsuario(f"Não consegui traduzir o trecho: {erro}") from erro


def relatorio_pdf(resultado: ResultadoAuditoria, *, tecnico: bool) -> bytes:
    with tempfile.TemporaryDirectory(prefix="relatorio-") as pasta:
        destino = Path(pasta) / "relatorio.pdf"
        try:
            gerar_pdf(gerar_html(resultado, tecnico=tecnico), destino)
        except ErroDePdf as erro:
            raise ErroParaUsuario(str(erro)) from erro
        return destino.read_bytes()
