"""Auditoria de ponta a ponta com LLM falso e base sintética."""

from pathlib import Path

import pytest

from conftest import escrever_pbip, modelo_tmsl, tabela
from core import auditoria
from core.analise.contexto import ErroDeContexto
from core.analise.llm import ContextoExcedido, ErroDeLLM
from core.auditoria import ErroDeAuditoria, ResultadoAuditoria, gravar, resumir, run_audit
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta, resposta


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(
        meta(),
        lambda modelo: [
            achado(objeto=t.nome, mensagem=f"A tabela '{t.nome}' foi gerada automaticamente.")
            for t in modelo.tabelas
        ],
    )
    return registro


def _pbip(tmp_path, tabelas=("LocalDateTable_1", "LocalDateTable_2")):
    return escrever_pbip(tmp_path, model_bim=modelo_tmsl([tabela(n) for n in tabelas]))


def _auditar(tmp_path, tabelas=("LocalDateTable_1", "LocalDateTable_2"), llm=None):
    llm = llm or LLMFalso()
    resultado = run_audit(
        _pbip(tmp_path, tabelas), llm=llm, base=base_padrao(), registro=_registro(),
        gabaritos={"MOD-001": gabarito()},
    )
    return resultado, llm


def test_auditoria_enriquece_cada_achado(tmp_path):
    resultado, llm = _auditar(tmp_path)
    assert (resultado.projeto, resultado.modelo_llm) == ("Minimal", "llm-falso")
    assert [a.achado.evidencia.objeto for a in resultado.achados] == ["LocalDateTable_1", "LocalDateTable_2"]
    assert all(a.situacao == "gerado" for a in resultado.achados)
    assert (llm.aquecimentos, len(llm.chamadas)) == (1, 2)
    assert resultado.regras.regras_executadas == 1
    assert resultado.regras.achados == []


def test_pbip_sem_achados_nao_chama_o_llm(tmp_path):
    resultado, llm = _auditar(tmp_path, tabelas=())
    assert resultado.achados == []
    assert (llm.aquecimentos, llm.chamadas) == (0, [])
    assert "Achados: 0" in resumir(resultado)


def test_llm_fora_do_ar_aborta_no_aquecimento(tmp_path):
    with pytest.raises(ErroDeAuditoria, match="aquecimento"):
        _auditar(tmp_path, llm=LLMFalso(falha_no_aquecimento=True))


def test_regra_sem_ancora_aborta_na_partida_sem_chamar_o_llm(tmp_path):
    llm = LLMFalso()
    with pytest.raises(ErroDeContexto, match="MOD-001"):
        run_audit(_pbip(tmp_path), llm=llm, base=base_padrao(), registro=_registro(), gabaritos={})
    assert llm.aquecimentos == 0


def test_erro_do_llm_num_achado_nao_para_os_outros(tmp_path):
    resultado, _ = _auditar(tmp_path, llm=LLMFalso(ErroDeLLM("timeout")))
    assert [a.situacao for a in resultado.achados] == ["sem_fundamentacao", "gerado"]


def test_nome_do_projeto_de_pasta_com_espaco_e_de_zip(tmp_path):
    assert auditoria.nome_do_projeto(tmp_path / "P1_AdventureWorks Sales") == "P1_AdventureWorks Sales"
    assert auditoria.nome_do_projeto(tmp_path / "projeto.zip") == "projeto"


def test_gravar_usa_projeto_data_e_hora_com_segundos_e_relê_igual(tmp_path):
    resultado, _ = _auditar(tmp_path)
    caminho = gravar(resultado, tmp_path / "saida")
    carimbo = resultado.gerado_em[:19].replace(":", "")
    assert caminho.name == f"Minimal-{carimbo}.json"
    assert caminho.stem == auditoria.nome_base(resultado)
    assert ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8")) == resultado


def test_gravar_so_regras_leva_sufixo(tmp_path):
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    assert gravar(resultado, tmp_path / "saida").name.endswith("-so-regras.json")


def test_duas_auditorias_no_mesmo_minuto_nao_se_sobrescrevem(tmp_path):
    resultado, _ = _auditar(tmp_path)
    base = resultado.gerado_em[:17]
    um = resultado.model_copy(update={"gerado_em": base + "01"})
    outro = resultado.model_copy(update={"gerado_em": base + "02"})
    assert gravar(um, tmp_path / "saida") != gravar(outro, tmp_path / "saida")


def test_resumo_so_regras_diz_o_modo_e_nao_fala_de_geracao(tmp_path):
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    texto = resumir(resultado)
    assert "so regras" in texto
    assert "Achados: 2" in texto
    assert "gerados" not in texto
    texto.encode("ascii")


def test_comando_so_regras_nao_carrega_a_base(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)

    def proibido():
        raise AssertionError("--so-regras não pode carregar a base")

    monkeypatch.setattr(auditoria.BaseRag, "carregar", staticmethod(proibido))
    assert auditoria.main([str(_pbip(tmp_path)), "--so-regras"]) == 0
    assert len(list((tmp_path / "saida").glob("Minimal-*-so-regras.json"))) == 1
    assert "so regras" in capsys.readouterr().out


def test_resumo_conta_motivos_e_e_ascii(tmp_path):
    resultado, _ = _auditar(tmp_path, llm=LLMFalso(resposta(citacoes=(9,))))
    texto = resumir(resultado)
    assert "citacao_inexistente=1" in texto
    assert "gerados: 1" in texto
    texto.encode("ascii")


def _comando_falso(monkeypatch, tmp_path, llm=None):
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(auditoria.BaseRag, "carregar", staticmethod(lambda: base_padrao()))
    monkeypatch.setattr(auditoria, "ClienteOllama", lambda modelo: llm or LLMFalso())
    monkeypatch.setattr(auditoria, "REGISTRO", _registro())
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {"MOD-001": gabarito()})


def test_comando_grava_o_json_e_imprime_em_ascii(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    assert auditoria.main([str(_pbip(tmp_path))]) == 0
    assert len(list((tmp_path / "saida").glob("Minimal-*.json"))) == 1
    capsys.readouterr().out.encode("ascii")


def test_comando_com_pbip_invalido_sai_com_erro(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    assert auditoria.main([str(tmp_path / "nao-existe")]) == 1
    assert "erro:" in capsys.readouterr().err


def test_comando_com_ollama_fora_do_ar_sai_com_erro(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path, llm=LLMFalso(falha_no_aquecimento=True))
    assert auditoria.main([str(_pbip(tmp_path))]) == 1
    assert "aquecimento" in capsys.readouterr().err


def test_resumo_conta_os_contextos_reduzidos(tmp_path):
    resultado, _ = _auditar(tmp_path, llm=LLMFalso(ContextoExcedido("7231 tokens")))
    assert "Contexto reduzido para caber: 1" in resumir(resultado)


def test_resumo_sem_reducao_nao_menciona(tmp_path):
    resultado, _ = _auditar(tmp_path)
    assert "reduzido" not in resumir(resultado)


def test_comando_com_model_bim_corrompido_sai_com_mensagem(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    pasta = escrever_pbip(tmp_path, model_bim=None)
    (pasta / "Minimal.SemanticModel" / "model.bim").write_text("{ quebrado", encoding="utf-8")
    assert auditoria.main([str(pasta)]) == 1
    assert "erro:" in capsys.readouterr().err


def test_falha_ao_gravar_sai_com_mensagem_e_ainda_mostra_o_resumo(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)

    def gravar_bloqueado(resultado, pasta=None):
        raise PermissionError("o arquivo está aberto em outro programa")

    monkeypatch.setattr(auditoria, "gravar", gravar_bloqueado)
    assert auditoria.main([str(_pbip(tmp_path))]) == 1
    saida = capsys.readouterr()
    assert "Achados: 2" in saida.out
    assert "erro:" in saida.err


FIXTURE_FORMATO_ANTIGO = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def test_json_no_formato_de_11_10_abre_como_completo():
    resultado = ResultadoAuditoria.model_validate_json(FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8"))
    assert (resultado.modo, resultado.modelo_llm) == ("completo", "qwen2.5:7b-instruct-q4_K_M")
    assert [a.situacao for a in resultado.achados] == ["gerado", "sem_fundamentacao"]


def _resultado(**extra) -> ResultadoAuditoria:
    from core.analise.base import AchadoEnriquecido
    from core.rules.runner import ResultadoRegras
    from fabricas_analise import achado as fabrica_achado

    campos = dict(
        projeto="P", modo="so_regras", modelo_llm=None, gerado_em="2026-10-13T15:30:00",
        regras=ResultadoRegras(regras_executadas=1),
        achados=[AchadoEnriquecido.so_regras(fabrica_achado())], segundos_total=0.1,
    )
    campos.update(extra)
    return ResultadoAuditoria(**campos)


def test_resultado_so_regras_coerente_e_aceito():
    assert _resultado().modo == "so_regras"


def test_resultado_com_modo_e_modelo_que_nao_batem_e_recusado():
    with pytest.raises(ValueError, match="incoerente"):
        _resultado(modelo_llm="m")
    with pytest.raises(ValueError, match="incoerente"):
        _resultado(modo="completo")


def test_so_regras_nao_toca_base_nem_llm_nem_gabaritos(tmp_path, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("o modo só regras não pode carregar gabaritos")

    monkeypatch.setattr(auditoria, "carregar_gabaritos", proibido)
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    assert (resultado.modo, resultado.modelo_llm) == ("so_regras", None)
    assert [a.situacao for a in resultado.achados] == ["so_regras", "so_regras"]
    assert all(a.contexto == [] for a in resultado.achados)


def test_modo_ambiguo_e_erro_de_programacao(tmp_path):
    pbip = _pbip(tmp_path)
    with pytest.raises(ValueError, match="ambíguo"):
        run_audit(pbip, llm=LLMFalso(), base=None, registro=_registro())
    with pytest.raises(ValueError, match="ambíguo"):
        run_audit(pbip, llm=None, base=base_padrao(), registro=_registro())


@pytest.mark.parametrize("modo", ["completo", "so_regras"])
def test_progresso_chamado_uma_vez_por_achado(tmp_path, modo):
    chamadas = []
    completo = modo == "completo"
    run_audit(
        _pbip(tmp_path), llm=LLMFalso() if completo else None, base=base_padrao() if completo else None,
        registro=_registro(), gabaritos={"MOD-001": gabarito()},
        ao_progredir=lambda feito, total, a: chamadas.append((feito, total, a.evidencia.objeto)),
    )
    assert chamadas == [(1, 2, "LocalDateTable_1"), (2, 2, "LocalDateTable_2")]


def test_progresso_sem_achados_nao_e_chamado(tmp_path):
    chamadas = []
    run_audit(_pbip(tmp_path, tabelas=()), llm=None, base=None, registro=_registro(),
              ao_progredir=lambda *a: chamadas.append(a))
    assert chamadas == []


def test_resumo_conta_o_cache_e_tira_do_tempo_medio(tmp_path):
    resultado, _ = _auditar(tmp_path)
    a, b = resultado.achados
    misto = resultado.model_copy(update={"achados": [
        a.model_copy(update={"segundos": 8.0}),
        b.model_copy(update={"segundos": 0.0, "do_cache": True}),
    ]})
    texto = resumir(misto)
    assert "Do cache: 1" in texto
    assert "medio 8.0s" in texto


def test_resumo_sem_cache_nao_menciona(tmp_path):
    resultado, _ = _auditar(tmp_path)
    assert "cache" not in resumir(resultado).lower()
