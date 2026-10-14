"""Execução da auditoria para a interface: cada falha vira ErroParaUsuario."""

import os
from pathlib import Path

import pytest

from app import execucao
from app.execucao import ErroParaUsuario
from conftest import escrever_pbip, modelo_tmsl, tabela
from core import auditoria
from core.analise.llm import ContextoExcedido
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta

FIXTURE_FORMATO_ANTIGO = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    return registro


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Pipeline com regra, gabarito, base e LLM falsos; saída em tmp."""
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(auditoria, "REGISTRO", _registro())
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {"MOD-001": gabarito()})
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: LLMFalso())
    return tmp_path


def _pbip(raiz):
    return escrever_pbip(raiz, model_bim=modelo_tmsl([tabela("LocalDateTable_1")]))


def test_executa_completo_grava_e_informa_progresso(ambiente):
    progresso = []
    feito = execucao.executar(
        _pbip(ambiente), "completo", "m", obter_base=base_padrao,
        ao_progredir=lambda f, t, a: progresso.append((f, t)),
    )
    assert feito.resultado.modo == "completo"
    assert feito.gravado_em is not None and feito.gravado_em.parent == ambiente / "saida"
    assert (feito.aviso_gravacao, progresso) == (None, [(1, 1)])


def test_executa_so_regras_sem_base(ambiente):
    def proibido():
        raise AssertionError("só regras não carrega a base")

    feito = execucao.executar(_pbip(ambiente), "so_regras", "m", obter_base=proibido)
    assert feito.resultado.modo == "so_regras"


def test_pbip_invalido_vira_mensagem(ambiente):
    with pytest.raises(ErroParaUsuario, match="não é um projeto PBIP válido"):
        execucao.executar(ambiente / "nao-existe", "so_regras", "m")


def test_model_bim_corrompido_vira_mensagem(ambiente):
    pasta = escrever_pbip(ambiente, model_bim=None)
    (pasta / "Minimal.SemanticModel" / "model.bim").write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ErroParaUsuario, match="Não consegui ler o projeto"):
        execucao.executar(pasta, "so_regras", "m")


def test_ollama_fora_do_ar_sugere_so_regras(ambiente, monkeypatch):
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: LLMFalso(falha_no_aquecimento=True))
    with pytest.raises(ErroParaUsuario, match="só regras"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao)


def test_indice_ausente_sugere_construir(ambiente):
    def sem_indice():
        raise FileNotFoundError("rag/store/indice/config.json")

    with pytest.raises(ErroParaUsuario, match="rag.indice construir"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=sem_indice)


def test_ancora_sem_trecho_sugere_construir(ambiente, monkeypatch):
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {})
    with pytest.raises(ErroParaUsuario, match="rag.indice construir"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao)


def test_falha_ao_gravar_devolve_o_resultado_com_aviso(ambiente, monkeypatch):
    def bloqueado(resultado, pasta=None):
        raise PermissionError("arquivo aberto em outro programa")

    monkeypatch.setattr(auditoria, "gravar", bloqueado)
    feito = execucao.executar(_pbip(ambiente), "so_regras", "m")
    assert feito.gravado_em is None
    assert "não foi gravado" in feito.aviso_gravacao


# --- envio do .zip (Review Focus 2) ---

@pytest.mark.parametrize("nome", ["P8.zip", "../../fora.zip", "C:\\x\\y\\P8.zip"])
def test_envio_fica_na_pasta_temporaria_so_com_o_nome_final(nome):
    caminho = execucao.salvar_envio(nome, b"PK")
    assert caminho.name == nome.replace("\\", "/").rsplit("/", 1)[-1]
    assert caminho.parent.name.startswith("envio-")
    assert caminho.read_bytes() == b"PK"


# --- resultados salvos (Review Focus 4) ---

def test_lista_salvos_do_mais_recente_e_tolera_pasta_ausente(tmp_path):
    assert execucao.listar_salvos(tmp_path / "nao-existe") == []
    antigo, novo = tmp_path / "A-2026-10-11T1000.json", tmp_path / "B-2026-10-13T1530-so-regras.json"
    antigo.write_text("{}", encoding="utf-8")
    novo.write_text("{}", encoding="utf-8")
    os.utime(antigo, (1_000_000, 1_000_000))
    salvos = execucao.listar_salvos(tmp_path)
    assert [s.rotulo for s in salvos] == ["B-2026-10-13T1530-so-regras", "A-2026-10-11T1000"]


def test_le_o_formato_antigo():
    resultado = execucao.ler_resultado(FIXTURE_FORMATO_ANTIGO.read_bytes())
    assert resultado.modo == "completo"


@pytest.mark.parametrize("conteudo", [b"{ quebrado", b'{"outra": "coisa"}', b"\xff\xfe\x00"])
def test_conteudo_que_nao_e_resultado_vira_mensagem(conteudo):
    with pytest.raises(ErroParaUsuario, match="não é um resultado de auditoria"):
        execucao.ler_resultado(conteudo)


def test_resultado_com_regra_desconhecida_vira_mensagem():
    texto = FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8").replace("MOD-001", "XYZ-999")
    with pytest.raises(ErroParaUsuario, match="XYZ-999"):
        execucao.ler_resultado(texto)


# --- tradução (Review Focus 5) ---

def test_traduz_pelo_modelo_indicado(monkeypatch):
    usados = []
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: usados.append(modelo) or LLMFalso('{"traducao": "Olá"}'))
    assert execucao.traduzir("Hello", "qwen") == "Olá"
    assert usados == ["qwen"]


@pytest.mark.parametrize("falha", [ContextoExcedido("longo demais"), "não é json"])
def test_traducao_que_falha_vira_mensagem(monkeypatch, falha):
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: LLMFalso(falha))
    with pytest.raises(ErroParaUsuario, match="Não consegui traduzir"):
        execucao.traduzir("Hello", "m")


def test_resultado_com_citacao_fora_do_contexto_vira_mensagem():
    texto = FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8").replace('"citacoes": [1]', '"citacoes": [99]')
    with pytest.raises(ErroParaUsuario, match="não é um resultado de auditoria"):
        execucao.ler_resultado(texto)


def test_ler_salvo_que_sumiu_vira_mensagem(tmp_path):
    with pytest.raises(ErroParaUsuario, match="Não consegui abrir"):
        execucao.ler_salvo(tmp_path / "sumiu.json")


def test_ler_salvo_le_o_arquivo():
    assert execucao.ler_salvo(FIXTURE_FORMATO_ANTIGO).modo == "completo"


def test_criar_llm_com_cache_envolve(monkeypatch, tmp_path):
    from core.analise.cache import ClienteComCache

    monkeypatch.setattr(execucao, "PASTA_CACHE", tmp_path)
    sem = execucao.criar_llm("m")
    com = execucao.criar_llm("m", cache=True)
    assert not isinstance(sem, ClienteComCache)
    assert isinstance(com, ClienteComCache) and com.pasta == tmp_path and com.nome == "m"


def test_executar_repassa_o_cache(ambiente, monkeypatch):
    pedidos = []
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: pedidos.append(cache) or LLMFalso())
    execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao, cache=True)
    assert pedidos == [True]


def test_relatorio_pdf_devolve_bytes_e_erro_vira_mensagem(monkeypatch):
    from reports.pdf import ErroDePdf

    resultado = execucao.ler_resultado(FIXTURE_FORMATO_ANTIGO.read_bytes())

    def falso(html, destino, **kwargs):
        assert "Formato-antigo" in html
        destino.write_bytes(b"%PDF-ok")
        return destino

    monkeypatch.setattr(execucao, "gerar_pdf", falso)
    assert execucao.relatorio_pdf(resultado, tecnico=False) == b"%PDF-ok"

    def falha(html, destino, **kwargs):
        raise ErroDePdf("PDF indisponível: Edge ausente")

    monkeypatch.setattr(execucao, "gerar_pdf", falha)
    with pytest.raises(ErroParaUsuario, match="Edge ausente"):
        execucao.relatorio_pdf(resultado, tecnico=False)


def test_envio_executa_e_apaga_a_pasta_temporaria(ambiente, monkeypatch):
    import io
    import zipfile

    pbip = _pbip(ambiente / "origem")
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        for caminho in pbip.rglob("*"):
            arquivo.write(caminho, caminho.relative_to(pbip.parent))
    gravados = []
    original = execucao.salvar_envio

    def gravar_e_lembrar(nome, conteudo):
        gravados.append(original(nome, conteudo))
        return gravados[-1]

    monkeypatch.setattr(execucao, "salvar_envio", gravar_e_lembrar)
    feito = execucao.executar_envio("Minimal.zip", memoria.getvalue(), "so_regras", "m")
    assert feito.resultado.projeto == "Minimal"
    assert not gravados[0].parent.exists()


def test_envio_que_nao_grava_vira_mensagem(monkeypatch):
    def cheio(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(execucao.tempfile, "mkdtemp", cheio)
    with pytest.raises(ErroParaUsuario, match="disco cheio"):
        execucao.executar_envio("P.zip", b"PK", "so_regras", "m")


def test_erro_de_validacao_do_pipeline_e_erro_inesperado(ambiente, monkeypatch):
    from core.auditoria import ResultadoAuditoria

    def quebra(*args, **kwargs):
        ResultadoAuditoria.model_validate({})

    monkeypatch.setattr(auditoria, "run_audit", quebra)
    with pytest.raises(ErroParaUsuario, match="Erro inesperado"):
        execucao.executar(_pbip(ambiente), "so_regras", "m")
