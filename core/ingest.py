"""Entrada da auditoria: localiza e valida a estrutura de um projeto PBIP."""

import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path


class ErroEstruturaPbip(Exception):
    """A pasta indicada não é um PBIP que o MVP saiba ler.

    A mensagem é escrita para o usuário final da interface, não para o
    desenvolvedor: diz o que falta e, quando cabe, o que fazer a respeito.
    """


@dataclass(frozen=True)
class ProjetoPbip:
    """As peças do PBIP que o MVP lê."""

    raiz: Path
    model_bim: Path
    extraido_em: Path | None = None
    """Pasta temporária da extração, quando a entrada foi um .zip."""


def abrir_pbip(caminho: str | Path) -> ProjetoPbip:
    """Abre um projeto PBIP a partir de uma pasta local ou de um arquivo .zip."""
    origem = Path(caminho)
    extraido_em = None

    if zipfile.is_zipfile(origem):
        extraido_em = Path(tempfile.mkdtemp(prefix="pbip-"))
        with zipfile.ZipFile(origem) as arquivo:
            arquivo.extractall(extraido_em)
        raiz = extraido_em
    elif origem.is_dir():
        raiz = origem
    else:
        raise ErroEstruturaPbip(
            f"{origem} não é uma pasta nem um arquivo .zip que eu consiga abrir."
        )

    # Num .zip o projeto costuma vir dentro de uma pasta, então a busca desce a
    # árvore em vez de olhar só o primeiro nível.
    semanticos = sorted(raiz.rglob("*.SemanticModel"))
    if not semanticos:
        raise ErroEstruturaPbip(
            f"Não encontrei nenhuma pasta '.SemanticModel' em {raiz}. "
            "Indique a pasta do projeto PBIP, aquela que contém o arquivo .pbip."
        )

    semantic = semanticos[0]
    model_bim = semantic / "model.bim"

    if not model_bim.is_file():
        if (semantic / "definition").is_dir():
            raise ErroEstruturaPbip(
                f"O projeto em {semantic.name} está salvo em TMDL (pasta 'definition'), "
                "e esta ferramenta lê apenas o formato TMSL (arquivo 'model.bim'). "
                "Para auditá-lo, desligue o recurso de visualização "
                "'Store semantic model using TMDL format' no Power BI Desktop e "
                "salve o projeto novamente. Atenção: a conversão para TMDL é "
                "irreversível, então salve como um projeto novo."
            )
        raise ErroEstruturaPbip(
            f"Não encontrei o arquivo 'model.bim' em {semantic.name}. "
            "A pasta do modelo semântico existe, mas está incompleta."
        )

    return ProjetoPbip(raiz=raiz, model_bim=model_bim, extraido_em=extraido_em)
