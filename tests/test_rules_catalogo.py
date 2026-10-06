"""O catálogo.

A tabela de regras do capítulo de metodologia sai daqui, gerada, não mantida à
mão. E o teste de completude é o que faz valer a decisão D-7: regra sem âncora
não entra no registro.
"""

import os
import subprocess
import sys

from core.model import ModeloSemantico
from core.rules.catalogo import IDS_ESPERADOS, como_markdown
from core.rules.runner import avaliar
from core.rules.todas import REGISTRO


def test_as_oito_regras_estao_registradas():
    assert REGISTRO.ids() == IDS_ESPERADOS
    assert len(REGISTRO) == 8


def test_toda_regra_tem_ancora_utilizavel():
    for meta in REGISTRO.metas():
        assert meta.url_canonica.startswith("https://"), meta.id
        assert meta.termos_consulta, meta.id
        assert len(meta.recomendacao_padrao.strip()) >= 40, meta.id
        assert meta.titulo.strip(), meta.id


def test_modelo_vazio_nao_produz_achado_nem_falha():
    """Um PBIP recém-criado não pode derrubar nem assustar a auditoria."""
    resultado = avaliar(ModeloSemantico(), registro=REGISTRO)

    assert resultado.achados == []
    assert resultado.regras_com_falha == []
    assert resultado.regras_executadas == 8


def test_markdown_tem_uma_linha_por_regra():
    texto = como_markdown()
    linhas = [l for l in texto.splitlines() if l.startswith("| MOD-") or l.startswith("| PERF-")]

    assert len(linhas) == 8
    assert "MOD-001" in texto
    assert "https://learn.microsoft.com" in texto


def test_cli_imprime_o_catalogo():
    """O console do Windows usa cp1252; `PYTHONIOENCODING` evita o
    `UnicodeEncodeError` nos títulos acentuados quando a saída é um pipe."""
    saida = subprocess.run(
        [sys.executable, "-m", "core.rules.catalogo"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=os.environ | {"PYTHONIOENCODING": "utf-8"},
        check=True,
    )

    for id_regra in IDS_ESPERADOS:
        assert id_regra in saida.stdout
