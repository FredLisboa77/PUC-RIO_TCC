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
    coletar,
    main,
    paginas_do_catalogo,
    resumo_coleta,
)
from rag.tocs import ErroDeRetrato
from rag import coleta as modulo_coleta

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
def _paginas(n):
    return [
        PaginaAColetar(id=f"learn:dax/p{i}", url=f"https://learn.microsoft.com/en-us/dax/p{i}")
        for i in range(n)
    ]


class Simulador:
    """Buscador, pausa e relógio falsos, com o que foi pedido registrado."""

    def __init__(self, falhas=None):
        self.falhas = falhas or {}
        self.pedidos = []
        self.pausas = []

    def buscar(self, url):
        self.pedidos.append(url)
        if url in self.falhas:
            raise self.falhas[url]
        return HTML_COM_META.replace("<h1 id=\"x\">X</h1>", f"<h1>{url}</h1>").encode()

    def dormir(self, segundos):
        self.pausas.append(segundos)

    def agora(self):
        return AGORA


def _coletar(sim, paginas, tmp_path, **extra):
    return coletar(
        paginas,
        buscar=sim.buscar,
        dormir=sim.dormir,
        agora=sim.agora,
        pasta_paginas=tmp_path / "paginas",
        arquivo_registro=tmp_path / "coleta.jsonl",
        **extra,
    )


def test_coleta_grava_html_e_registro_com_metadados(tmp_path):
    sim = Simulador()
    resumo = _coletar(sim, _paginas(2), tmp_path)
    assert resumo.coletadas == ["learn:dax/p0", "learn:dax/p1"]
    assert resumo.total_ok == resumo.total == 2
    registro = ler_registro(tmp_path / "coleta.jsonl")["learn:dax/p0"]
    arquivo = caminho_da_pagina(tmp_path / "paginas", "learn:dax/p0")
    assert registro.situacao == "ok"
    assert registro.sha256 == hashlib.sha256(arquivo.read_bytes()).hexdigest()
    assert registro.tamanho == len(arquivo.read_bytes())
    assert registro.updated_at == "2026-08-04T22:03:00Z"
    assert registro.acessado_em == AGORA


def test_pausa_entre_requisicoes_e_nao_antes_da_primeira(tmp_path):
    sim = Simulador()
    _coletar(sim, _paginas(3), tmp_path, pausa=1.0)
    assert sim.pausas == [1.0, 1.0]


def test_retomada_pula_o_que_ja_esta_ok(tmp_path):
    _coletar(Simulador(), _paginas(2), tmp_path)
    sim = Simulador()
    resumo = _coletar(sim, _paginas(3), tmp_path)
    assert sim.pedidos == ["https://learn.microsoft.com/en-us/dax/p2"]
    assert resumo.ja_existentes == 2
    assert resumo.total_ok == 3


def test_arquivo_apagado_ou_alterado_e_baixado_de_novo(tmp_path):
    _coletar(Simulador(), _paginas(2), tmp_path)
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/p0").unlink()
    caminho_da_pagina(tmp_path / "paginas", "learn:dax/p1").write_bytes(b"mexido")
    sim = Simulador()
    _coletar(sim, _paginas(2), tmp_path)
    assert len(sim.pedidos) == 2


def test_erro_comum_registra_e_segue(tmp_path):
    url = "https://learn.microsoft.com/en-us/dax/p0"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP 404", status=404)})
    resumo = _coletar(sim, _paginas(3), tmp_path)
    assert resumo.coletadas == ["learn:dax/p1", "learn:dax/p2"]
    assert [e.id for e in resumo.erros] == ["learn:dax/p0"]
    assert resumo.interrompida is None
    assert ler_registro(tmp_path / "coleta.jsonl")["learn:dax/p0"].motivo.endswith("HTTP 404")


@pytest.mark.parametrize("status", [429, 503])
def test_servidor_pedindo_para_parar_interrompe_na_hora(tmp_path, status):
    url = "https://learn.microsoft.com/en-us/dax/p1"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP {status}", status=status)})
    resumo = _coletar(sim, _paginas(4), tmp_path)
    assert len(sim.pedidos) == 2
    assert resumo.interrompida and str(status) in resumo.interrompida


def test_cinco_falhas_seguidas_interrompem(tmp_path):
    paginas = _paginas(8)
    sim = Simulador({p.url: ErroDeRetrato(f"{p.url}: sem rota") for p in paginas})
    resumo = _coletar(sim, paginas, tmp_path)
    assert len(sim.pedidos) == 5
    assert "5 falhas seguidas" in resumo.interrompida


def test_sucesso_zera_a_contagem_de_falhas_seguidas(tmp_path):
    paginas = _paginas(10)
    falhas = {p.url: ErroDeRetrato(f"{p.url}: sem rota") for i, p in enumerate(paginas) if i != 4}
    resumo = _coletar(Simulador(falhas), paginas, tmp_path)
    assert resumo.interrompida is not None
    assert resumo.coletadas == ["learn:dax/p4"]
    assert len(resumo.erros) == 9


def test_limite_coleta_so_as_primeiras_pendentes(tmp_path):
    sim = Simulador()
    resumo = _coletar(sim, _paginas(5), tmp_path, limite=2)
    assert len(sim.pedidos) == 2
    assert resumo.total_ok == 2 and resumo.total == 5


def test_resumo_lista_erros_e_interrupcao(tmp_path):
    url = "https://learn.microsoft.com/en-us/dax/p0"
    sim = Simulador({url: ErroDeRetrato(f"{url}: HTTP 404", status=404)})
    texto = resumo_coleta(_coletar(sim, _paginas(2), tmp_path))
    assert "Coletadas nesta execução: 1" in texto
    assert "Total ok: 1 de 2" in texto
    assert "learn:dax/p0" in texto


def test_main_sem_catalogo_sai_com_erro(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(modulo_coleta, "ARQUIVO_FONTES", tmp_path / "nao-existe.yaml")
    assert main([]) == 1
    assert "rag.catalogo" in capsys.readouterr().err


def test_pagina_que_nao_decodifica_como_utf8_nao_derruba_a_coleta(tmp_path):
    class SimuladorLatin1(Simulador):
        def buscar(self, url):
            self.pedidos.append(url)
            return b"<html><head></head><body><h1>Caf\xe9</h1></body></html>"

    resumo = _coletar(SimuladorLatin1(), _paginas(1), tmp_path)
    assert resumo.coletadas == ["learn:dax/p0"]
    assert ler_registro(tmp_path / "coleta.jsonl")["learn:dax/p0"].updated_at is None
