"""Teste do glossário na instrução da geração — análise de erros.

Protocolo em `docs/superpowers/specs/2026-10-15-teste-do-glossario-design.md`,
versionado antes da rodada. Muda só a instrução de sistema; o código de produção
não muda. `ClienteComInstrucao` troca a mensagem de sistema *antes* do cache, de
modo que as respostas novas entram no cache com chave própria e as originais
continuam reproduzíveis.
"""

import csv
import random
import re
from pathlib import Path

from pydantic import BaseModel

from avaliacao_geracao.estatistica import kappa, mcnemar_exato, wilson
from avaliacao_geracao.planilha import ITENS, LinhaRubrica, escrever_planilha
from avaliacao_geracao.rodada import ItemDaRodada, Rodada
from core.analise.llm import LLMClient, RespostaLLM
from core.analise.prompt import SISTEMA
from rag.avaliacao import RAIZ_REPO

GLOSSARIO = """GLOSSÁRIO — use estes sentidos ao ler os trechos em inglês e ao escrever em português:
- compress, compression: comprimir, compressão — reduzir o espaço que os dados ocupam. Nunca traduza como "compreender".
- VertiPaq: o mecanismo que armazena os dados do modelo comprimidos em memória.
- calculated column: coluna calculada — coluna criada no modelo por uma fórmula DAX.
- BLANK: o valor vazio do DAX, que representa ausência de dado. Uma medida que devolve BLANK não é um erro: em geral é o comportamento desejado, porque os visuais omitem os grupos vazios.
- DAX: a linguagem das medidas, das colunas calculadas e das tabelas calculadas do modelo.
- Power Query: a ferramenta de preparação dos dados, cujas fórmulas são escritas na linguagem M, e não em DAX. Funções DAX como YEAR, FORMAT ou RELATED não existem no Power Query.
- denormalize: desnormalizar — juntar numa só tabela as tabelas de uma mesma dimensão; tabelas de fatos não entram nessa junção."""

SISTEMA_COM_GLOSSARIO = f"{SISTEMA}\n\n{GLOSSARIO}"

SEMENTE = 20261015
N_ORIGINAIS = 20
PASTA = RAIZ_REPO / "eval" / "geracao"
PASTA_RODADA_GLOSSARIO = PASTA / "auditorias-glossario"
PASTA_REEXECUCAO = PASTA / "auditorias-reexecucao"
CHAVE = PASTA / "glossario" / "chave.json"
PLANILHA_CEGA = RAIZ_REPO / "eval" / "gabarito" / "rubrica-glossario-P1-P7.xlsx"
CSV_GLOSSARIO = RAIZ_REPO / "eval" / "rubrica_glossario.csv"
CSV_SENSIBILIDADE = RAIZ_REPO / "eval" / "rubrica_glossario_sensibilidade.csv"
LIMIAR_CONSISTENCIA = 0.80
ALFA = 0.05
ERRO_DE_TRADUCAO = re.compile(r"compreend|descompress", re.IGNORECASE)

INSTRUCOES_CEGAS = [
    "",
    "Esta planilha mistura explicações de mais de uma rodada, em ordem aleatória e com códigos opacos (R01…).",
    "Julgue cada linha por si, pelos mesmos critérios, sem tentar adivinhar de que rodada ela vem.",
]


class ClienteComInstrucao:
    """Envolve um `LLMClient` e substitui a instrução de sistema de cada pedido."""

    def __init__(self, llm: LLMClient, sistema: str) -> None:
        self.llm = llm
        self.sistema = sistema
        self.nome = llm.nome

    def aquecer(self) -> None:
        self.llm.aquecer()

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM:
        if not mensagens or mensagens[0].get("role") != "system":
            raise ValueError("pedido sem instrução de sistema na primeira mensagem")
        return self.llm.gerar([{"role": "system", "content": self.sistema}, *mensagens[1:]], esquema)


def _gerados(rodada: Rodada) -> list[str]:
    return sorted(k for k, r in rodada.items() if r.item.situacao == "gerado")


def montar_amostra(original: Rodada, nova: Rodada, *, n_originais: int = N_ORIGINAIS,
                   semente: int = SEMENTE) -> dict[str, dict[str, str]]:
    """Código opaco → versão e achado: todas as explicações novas e `n_originais`
    originais sorteadas, embaralhadas (protocolo, passo 3)."""
    sorteio = random.Random(semente)
    linhas = [("original", a) for a in sorteio.sample(_gerados(original), n_originais)]
    linhas += [("glossario", a) for a in _gerados(nova)]
    sorteio.shuffle(linhas)
    return {f"R{n:02d}": {"versao": v, "achado": a} for n, (v, a) in enumerate(linhas, start=1)}


def rodada_da_chave(chave: dict[str, dict[str, str]], original: Rodada, nova: Rodada) -> Rodada:
    """A rodada combinada, indexada pelo código: é contra ela que a planilha é validada."""
    fontes = {"original": original, "glossario": nova}
    return {codigo: fontes[v["versao"]][v["achado"]] for codigo, v in chave.items()}


def gerar_planilha_cega(chave: dict[str, dict[str, str]], original: Rodada, nova: Rodada, destino,
                        *, forcar: bool = False) -> int:
    combinada = rodada_da_chave(chave, original, nova)
    itens: list[tuple[str, ItemDaRodada]] = [(codigo, combinada[codigo]) for codigo in chave]
    return escrever_planilha(itens, destino, forcar=forcar, instrucoes_extra=INSTRUCOES_CEGAS)


def _utilizavel(linha: LinhaRubrica | None) -> str:
    if linha is None:  # achado sem explicação nova: conta como não utilizável (protocolo, passo 1)
        return "não"
    vereditos = [getattr(linha, n) for n in ITENS]
    if "não" in vereditos:
        return "não"
    return "sim" if all(v == "sim" for v in vereditos) else "indeterminado"


def _veredito(linha: LinhaRubrica | None, item: str) -> str:
    if item == "utilizavel":
        return _utilizavel(linha)
    return "não" if linha is None else getattr(linha, item)


def _proporcao(vereditos: list[str]) -> dict:
    sim, n = sum(v == "sim" for v in vereditos), len(vereditos)
    faixa = wilson(sim, n)
    return {"sim": sim, "n": n, "proporcao": sim / n if n else None, "wilson": list(faixa) if faixa else None}


def medir_glossario(originais: list[LinhaRubrica], novas: list[LinhaRubrica], chave: dict[str, dict[str, str]],
                    *, achados: list[str]) -> dict:
    """`achados`: os ids da rodada original avaliada (a base do pareamento).
    Para o McNemar, "sim" × qualquer outro veredito."""
    primeira = {l.id: l for l in originais}
    nova_por_achado = {chave[l.id]["achado"]: l for l in novas if chave[l.id]["versao"] == "glossario"}
    reanotada = {chave[l.id]["achado"]: l for l in novas if chave[l.id]["versao"] == "original"}
    nomes = (*ITENS, "utilizavel")

    itens, por_regra = {}, {}
    for item in nomes:
        antes = [_veredito(primeira[a], item) for a in achados]
        depois = [_veredito(nova_por_achado.get(a), item) for a in achados]
        b = sum(x == "sim" and y != "sim" for x, y in zip(antes, depois))
        c = sum(x != "sim" and y == "sim" for x, y in zip(antes, depois))
        itens[item] = {"original": _proporcao(antes), "glossario": _proporcao(depois),
                       "discordantes": {"so_original": b, "so_glossario": c}, "p_mcnemar": mcnemar_exato(b, c)}
        for regra in sorted({a.split("|")[1] for a in achados}):
            dela = [i for i, a in enumerate(achados) if a.split("|")[1] == regra]
            por_regra.setdefault(regra, {})[item] = {
                "original": f"{sum(antes[i] == 'sim' for i in dela)} / {len(dela)}",
                "glossario": f"{sum(depois[i] == 'sim' for i in dela)} / {len(dela)}",
            }

    consistencia = {}
    for item in nomes:
        pares = [(_veredito(primeira[a], item) == "sim", _veredito(l, item) == "sim") for a, l in sorted(reanotada.items())]
        t = {"a": sum(x and y for x, y in pares), "b": sum(x and not y for x, y in pares),
             "c": sum(not x and y for x, y in pares), "d": sum(not x and not y for x, y in pares)}
        n = len(pares)
        consistencia[item] = {"n": n, "tabela": t, "concordancia": (t["a"] + t["d"]) / n if n else None,
                              "kappa": kappa(t["a"], t["b"], t["c"], t["d"])}

    # Acrescentada depois da medição, ao ver a consistência baixa: compara as duas
    # versões só com vereditos dados na mesma sessão, nos achados reanotados.
    exploratoria = {}
    for item in nomes:
        pares = [(_veredito(l, item) == "sim", _veredito(nova_por_achado.get(a), item) == "sim")
                 for a, l in sorted(reanotada.items())]
        b = sum(x and not y for x, y in pares)
        c = sum(not x and y for x, y in pares)
        exploratoria[item] = {"original_reanotada": sum(x for x, _ in pares), "glossario": sum(y for _, y in pares),
                              "so_original": b, "so_glossario": c, "p_mcnemar": mcnemar_exato(b, c)}

    u = itens["utilizavel"]
    concordancia_u = consistencia["utilizavel"]["concordancia"]
    return {
        "estatuto": "análise de erros",
        "protocolo": "docs/superpowers/specs/2026-10-15-teste-do-glossario-design.md",
        "n_pares": len(achados),
        "itens": itens,
        "por_regra": por_regra,
        "consistencia": consistencia,
        "exploratoria_mesma_sessao": {
            "nota": "análise exploratória, fora do protocolo: vereditos da mesma sessão nos achados reanotados",
            "n": len(reanotada),
            "itens": exploratoria,
        },
        "decisao": {
            "melhora": u["glossario"]["sim"] > u["original"]["sim"] and u["p_mcnemar"] < ALFA,
            "fragil": concordancia_u is None or concordancia_u < LIMIAR_CONSISTENCIA,
        },
    }


def indicador_lexico(rodada: Rodada, regra: str = "PERF-001") -> dict:
    """Explicações da regra que trazem o erro de tradução de "compress" (protocolo, passo 5)."""
    textos = [r.item.geracao.explicacao for r in rodada.values()
              if r.item.achado.id_regra == regra and r.item.situacao == "gerado"]
    return {"com_erro": sum(bool(ERRO_DE_TRADUCAO.search(t)) for t in textos), "explicacoes": len(textos)}


class Correcao(BaseModel):
    """Veredito revisto na análise de sensibilidade, com o motivo."""

    codigo: str
    item: str
    de: str
    para: str
    motivo: str


def ler_correcoes(caminho: Path = CSV_SENSIBILIDADE) -> list[Correcao]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [Correcao(**linha) for linha in csv.DictReader(arquivo)]


def aplicar_correcoes(linhas: list[LinhaRubrica], correcoes: list[Correcao]) -> list[LinhaRubrica]:
    """Cópias corrigidas; a anotação lida não muda. Falha se o veredito anotado não for o `de`."""
    por_id = {l.id: l.model_copy() for l in linhas}
    for c in correcoes:
        linha = por_id.get(c.codigo)
        if linha is None or getattr(linha, c.item) != c.de:
            raise ValueError(f"correção {c.codigo}/{c.item}: o veredito anotado não é '{c.de}'")
        setattr(linha, c.item, c.para)
    return [por_id[l.id] for l in linhas]
