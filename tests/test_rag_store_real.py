"""A base coletada, conferida contra o catálogo e as âncoras das regras.

Pulados quando `rag/store/` não existe — o conteúdo do Learn não é versionado
(termos de uso). É aqui que se prova que a RAG terá o trecho que cada regra cita.
"""

import pytest
import yaml

from rag.avaliacao import ARQUIVO_GABARITO, ler_frases_marca
from rag.catalogo import ARQUIVO_FONTES, ancoras_do_registro
from rag.coleta import ARQUIVO_REGISTRO, ler_registro
from rag.extracao import PASTA_TEXTOS, VERSAO_EXTRATOR, PaginaExtraida, caminho_do_texto
from rag.texto import normalizar
from rag.urls import caminho_sem_idioma, normalizar_url

pytestmark = pytest.mark.skipif(
    not ARQUIVO_REGISTRO.is_file(), reason="rag/store/ não existe (conteúdo do Learn não é versionado)"
)

FRASES_MARCA = {f.id_regra: f.frase_marca for f in ler_frases_marca(ARQUIVO_GABARITO)}
"""As frases-marca vivem em `eval/recuperacao/gabarito.yaml`."""


def _pagina(id_fonte: str) -> PaginaExtraida:
    return PaginaExtraida.model_validate_json(
        caminho_do_texto(PASTA_TEXTOS, id_fonte).read_text(encoding="utf-8")
    )


def test_toda_pagina_do_catalogo_foi_coletada_e_extraida():
    indexaveis = {
        f["id"] for f in yaml.safe_load(ARQUIVO_FONTES.read_text(encoding="utf-8")) if f["indexar"]
    }
    registro = ler_registro(ARQUIVO_REGISTRO)
    ok = {i for i, r in registro.items() if r.situacao == "ok"}
    assert indexaveis <= ok, sorted(indexaveis - ok)[:10]
    for id_fonte in sorted(indexaveis):
        assert _pagina(id_fonte).versao_extrator == VERSAO_EXTRATOR, id_fonte


def test_toda_regra_tem_frase_marca():
    assert set(FRASES_MARCA) == set(ancoras_do_registro())


@pytest.mark.parametrize("id_regra", sorted(FRASES_MARCA))
def test_a_passagem_citada_pela_regra_esta_no_texto_extraido(id_regra):
    url = ancoras_do_registro()[id_regra]
    pagina = _pagina("learn:" + caminho_sem_idioma(normalizar_url(url)))
    texto = normalizar(" ".join(b.texto for s in pagina.secoes for b in s.blocos))
    assert normalizar(FRASES_MARCA[id_regra]) in texto
