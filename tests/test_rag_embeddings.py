"""Cache de embeddings. Um embedder falso e determinístico: sem modelo, sem rede."""

import numpy as np

from rag.embeddings import arquivo_do_cache, chave_do_cache, ler_cache, vetores_com_cache


class EmbedderFalso:
    def __init__(self, nome="falso"):
        self.nome = nome
        self.chamadas = 0

    def vetores(self, textos):
        self.chamadas += 1
        return np.array([[len(t), 1.0] for t in textos], dtype=np.float32)

    def vetor_consulta(self, texto):
        return np.array([len(texto), 1.0], dtype=np.float32)


def test_cache_e_gravado_e_reaproveitado(tmp_path):
    embedder = EmbedderFalso()
    primeiro = vetores_com_cache(embedder, ["a", "bb"], pasta=tmp_path, nome="secao-sem")
    segundo = vetores_com_cache(embedder, ["a", "bb"], pasta=tmp_path, nome="secao-sem")
    assert embedder.chamadas == 1
    assert np.array_equal(primeiro, segundo)
    assert arquivo_do_cache(tmp_path, "secao-sem", "falso", ["a", "bb"]).is_file()


def test_mudar_um_texto_ou_o_modelo_muda_a_chave():
    base = chave_do_cache("m", ["a", "b"])
    assert chave_do_cache("m", ["a", "c"]) != base
    assert chave_do_cache("outro", ["a", "b"]) != base
    assert chave_do_cache("m", ["ab"]) != chave_do_cache("m", ["a", "b"])


def test_texto_mudado_recalcula(tmp_path):
    embedder = EmbedderFalso()
    vetores_com_cache(embedder, ["a"], pasta=tmp_path, nome="n")
    vetores_com_cache(embedder, ["b"], pasta=tmp_path, nome="n")
    assert embedder.chamadas == 2


def test_cache_corrompido_e_recalculado_com_aviso(tmp_path, capsys):
    embedder = EmbedderFalso()
    arquivo = arquivo_do_cache(tmp_path, "n", "falso", ["a"])
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_bytes(b"lixo")
    vetores = vetores_com_cache(embedder, ["a"], pasta=tmp_path, nome="n")
    assert embedder.chamadas == 1 and vetores.shape == (1, 2)
    assert "recalculando" in capsys.readouterr().err


def test_cache_com_linhas_erradas_nunca_e_devolvido(tmp_path):
    embedder = EmbedderFalso()
    arquivo = arquivo_do_cache(tmp_path, "n", "falso", ["a", "b"])
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    np.save(arquivo, np.zeros((5, 2), dtype=np.float32))
    assert ler_cache(tmp_path, "n", "falso", ["a", "b"]) is None
    assert vetores_com_cache(embedder, ["a", "b"], pasta=tmp_path, nome="n").shape == (2, 2)


def test_ler_cache_ausente_e_none(tmp_path):
    assert ler_cache(tmp_path, "n", "falso", ["a"]) is None
