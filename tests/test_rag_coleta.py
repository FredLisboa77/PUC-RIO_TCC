"""Coleta das páginas do catálogo.

HTML sintético escrito à mão: nenhum HTML do Learn entra no repositório (termos
de uso, spec do catálogo 5.2).
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rag.coleta import (
    ErroDeColeta,
    PaginaAColetar,
    RegistroColeta,
    anexar_registro,
    caminho_da_pagina,
    ja_coletada,
    ler_registro,
    metadados_da_pagina,
    paginas_do_catalogo,
)

AGORA = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

HTML_COM_META = """<html><head>
<meta name="updated_at" content="2026-08-04T22:03:00Z">
<meta name="ms.date" content="2026-06-29T00:00:00Z">
<meta name="git_commit_id" content="b39c707">
<meta name="document_id" content="8ad6539c">
</head><body><main id="main"><h1 id="x">X</h1></main></body></html>"""


def test_caminho_da_pagina_aninha_pelo_id():
    assert caminho_da_pagina(Path("p"), "learn:dax/calculate-function-dax") == Path(
        "p/learn/dax/calculate-function-dax.html"
    )


@pytest.mark.parametrize("id_ruim", ["sem-prefixo", "learn:", "learn:../fora", ":dax/x"])
def test_caminho_da_pagina_recusa_id_invalido(id_ruim):
    with pytest.raises(ErroDeColeta, match="id inválido"):
        caminho_da_pagina(Path("p"), id_ruim)


def test_metadados_da_pagina():
    assert metadados_da_pagina(HTML_COM_META) == {
        "updated_at": "2026-08-04T22:03:00Z",
        "ms_date": "2026-06-29T00:00:00Z",
        "git_commit_id": "b39c707",
        "document_id": "8ad6539c",
    }


def test_metadados_ausentes_viram_none():
    assert metadados_da_pagina("<html><body>sem meta</body></html>") == {
        "updated_at": None,
        "ms_date": None,
        "git_commit_id": None,
        "document_id": None,
    }


def test_paginas_do_catalogo_so_indexaveis_em_ordem(tmp_path):
    fontes = tmp_path / "sources.yaml"
    fontes.write_text(
        "- id: learn:dax/b\n  url: https://learn.microsoft.com/en-us/dax/b\n  indexar: true\n"
        "- id: sqlbi:x\n  url: https://www.sqlbi.com/articles/x/\n  indexar: false\n"
        "- id: learn:dax/a\n  url: https://learn.microsoft.com/en-us/dax/a\n  indexar: true\n",
        encoding="utf-8",
    )
    assert paginas_do_catalogo(fontes) == [
        PaginaAColetar(id="learn:dax/a", url="https://learn.microsoft.com/en-us/dax/a"),
        PaginaAColetar(id="learn:dax/b", url="https://learn.microsoft.com/en-us/dax/b"),
    ]


def test_catalogo_ausente_ou_sem_indexavel_falha(tmp_path):
    with pytest.raises(ErroDeColeta, match="rag.catalogo"):
        paginas_do_catalogo(tmp_path / "nao-existe.yaml")
    vazio = tmp_path / "sources.yaml"
    vazio.write_text("- id: sqlbi:x\n  url: u\n  indexar: false\n", encoding="utf-8")
    with pytest.raises(ErroDeColeta, match="indexar: true"):
        paginas_do_catalogo(vazio)


def _ok(id_fonte, sha="abc"):
    return RegistroColeta(
        id=id_fonte, url="u", situacao="ok", acessado_em=AGORA, tamanho=3, sha256=sha
    )


def test_registro_guarda_a_ultima_linha_de_cada_id(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    anexar_registro(caminho, RegistroColeta(id="a", url="u", situacao="erro", acessado_em=AGORA, motivo="HTTP 500"))
    anexar_registro(caminho, _ok("a"))
    anexar_registro(caminho, _ok("b"))
    registro = ler_registro(caminho)
    assert registro["a"].situacao == "ok"
    assert set(registro) == {"a", "b"}
    assert b"\r\n" not in caminho.read_bytes()


def test_registro_ausente_e_vazio(tmp_path):
    assert ler_registro(tmp_path / "nao-existe.jsonl") == {}


def test_ultima_linha_truncada_e_ignorada(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    anexar_registro(caminho, _ok("a"))
    with open(caminho, "a", encoding="utf-8") as arquivo:
        arquivo.write('{"id": "b", "url": "u", "situ')
    assert set(ler_registro(caminho)) == {"a"}


def test_linha_invalida_no_meio_falha_nomeando_a_linha(tmp_path):
    caminho = tmp_path / "coleta.jsonl"
    caminho.write_text('{"quebrada": 1}\n' + _ok("a").model_dump_json() + "\n", encoding="utf-8")
    with pytest.raises(ErroDeColeta, match="coleta.jsonl:1"):
        ler_registro(caminho)


def test_ja_coletada_exige_ok_arquivo_e_mesmo_sha256(tmp_path):
    arquivo = caminho_da_pagina(tmp_path, "learn:dax/a")
    arquivo.parent.mkdir(parents=True)
    arquivo.write_bytes(b"abc")
    sha = hashlib.sha256(b"abc").hexdigest()
    assert ja_coletada(_ok("learn:dax/a", sha), tmp_path)
    assert not ja_coletada(_ok("learn:dax/a", "outro"), tmp_path)
    assert not ja_coletada(None, tmp_path)
    erro = RegistroColeta(id="learn:dax/a", url="u", situacao="erro", acessado_em=AGORA, motivo="x")
    assert not ja_coletada(erro, tmp_path)
    arquivo.unlink()
    assert not ja_coletada(_ok("learn:dax/a", sha), tmp_path)
