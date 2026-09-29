import json
import shutil

import pytest

from conftest import escrever_pbip
from core.ingest import ErroEstruturaPbip, abrir_pbip


def test_encontra_o_model_bim_em_um_pbip_valido(pbip_minimo):
    projeto = abrir_pbip(pbip_minimo)

    assert projeto.model_bim == pbip_minimo / "Minimal.SemanticModel" / "model.bim"


def test_aceita_um_zip_contendo_o_projeto(tmp_path):
    projeto = escrever_pbip(tmp_path / "origem")
    zip_path = shutil.make_archive(
        str(tmp_path / "Minimal"), "zip", root_dir=tmp_path / "origem"
    )

    aberto = abrir_pbip(zip_path)

    assert aberto.model_bim.is_file()
    assert json.loads(aberto.model_bim.read_text(encoding="utf-8"))["compatibilityLevel"] == 1600


def test_recusa_projeto_salvo_em_tmdl_explicando_o_motivo(tmp_path):
    projeto = escrever_pbip(tmp_path, tmdl=True)

    with pytest.raises(ErroEstruturaPbip) as erro:
        abrir_pbip(projeto)

    mensagem = str(erro.value)
    assert "TMDL" in mensagem
    assert "model.bim" in mensagem


def test_recusa_modelo_semantico_sem_model_bim(tmp_path):
    projeto = escrever_pbip(tmp_path, model_bim=None)

    with pytest.raises(ErroEstruturaPbip) as erro:
        abrir_pbip(projeto)

    assert "model.bim" in str(erro.value)


def test_recusa_pasta_sem_modelo_semantico(tmp_path):
    (tmp_path / "qualquer.txt").write_text("nao e um pbip", encoding="utf-8")

    with pytest.raises(ErroEstruturaPbip) as erro:
        abrir_pbip(tmp_path)

    assert "SemanticModel" in str(erro.value)
