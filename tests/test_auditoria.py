"""Auditoria de ponta a ponta com LLM falso e base sintética."""

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


def test_gravar_usa_projeto_e_data_e_relê_igual(tmp_path):
    resultado, _ = _auditar(tmp_path)
    caminho = gravar(resultado, tmp_path / "saida")
    assert caminho.name == f"Minimal-{resultado.gerado_em[:10]}.json"
    assert ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8")) == resultado


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
