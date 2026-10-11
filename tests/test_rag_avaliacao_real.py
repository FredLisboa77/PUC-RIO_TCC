"""O conjunto de avaliação versionado, conferido contra a base e os PBIP reais.

O teste de congelamento é pulado sem `rag/store/` e `data/pbip/`, que não são
versionados. A coerência entre os dois arquivos versionados roda sempre.
"""

import pytest

from rag.avaliacao import (
    ARQUIVO_CONSULTAS,
    ARQUIVO_GABARITO,
    PASTA_PBIP,
    como_yaml,
    gerar_do_repositorio,
    ler_conjunto,
    ler_frases_marca,
)
from rag.coleta import ARQUIVO_REGISTRO

dados_reais = pytest.mark.skipif(
    not (ARQUIVO_REGISTRO.is_file() and PASTA_PBIP.is_dir()),
    reason="rag/store/ ou data/pbip/ ausente (não são versionados)",
)


def test_consultas_versionadas_usam_as_frases_do_gabarito():
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    frases = {f.id_regra: f.frase_marca for f in ler_frases_marca(ARQUIVO_GABARITO)}
    assert {g.id_regra: g.frase_marca for g in conjunto.gabaritos} == frases


def test_contagem_do_conjunto_versionado():
    conjunto = ler_conjunto(ARQUIVO_CONSULTAS)
    assert len(conjunto.gabaritos) == 9
    assert len(conjunto.consultas) == 62
    assert sum(c.tipo == "regra" for c in conjunto.consultas) == 9
    assert len({c.id for c in conjunto.consultas}) == 62


def test_mod003_e_mod006_caem_em_secoes_diferentes_da_mesma_pagina():
    gabaritos = {g.id_regra: g for g in ler_conjunto(ARQUIVO_CONSULTAS).gabaritos}
    assert gabaritos["MOD-003"].id_pagina == gabaritos["MOD-006"].id_pagina
    assert gabaritos["MOD-003"].ancora != gabaritos["MOD-006"].ancora


@dados_reais
def test_consultas_versionadas_sao_o_que_o_gerador_produz():
    assert ARQUIVO_CONSULTAS.read_text(encoding="utf-8") == como_yaml(gerar_do_repositorio()), (
        "eval/recuperacao/consultas.yaml divergiu — rode `python -m rag.avaliacao gerar` e revise o diff"
    )
