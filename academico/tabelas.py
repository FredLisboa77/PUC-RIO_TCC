"""Tabelas da monografia geradas a partir dos resultados em `eval/results`.

Nenhum número de resultado é digitado na monografia: cada tabela sai daqui,
lida do consolidado, e um teste falha se o arquivo em `gerado/` divergir do
que este módulo produz.
"""

import json
import re
from pathlib import Path

from academico.compilacao import PASTA_MONOGRAFIA, RAIZ_REPO
from core.rules.todas import REGISTRO

CONSOLIDADO = RAIZ_REPO / "eval" / "results" / "consolidado-2026-10-15.json"
PASTA_GERADO = PASTA_MONOGRAFIA / "gerado"
AUSENTE = "—"
_ESPECIAIS = "\\*_#@<>$`[]~/"
_MARCADOR_INICIAL = re.compile(r"^(\s*)([-+=]|\d+\.)")

ROTULOS_GERACAO = {
    "pertinente": "Pertinente",
    "fiel": "Fiel",
    "recomendacao_correta": "Recomendação correta",
}
CRITERIO_AUTOMATICO = {
    "pertinente": "Cita a seção âncora",
    "fiel": "Sem aviso de números ou nomes",
}
ROTULOS_ESTRATEGIA = {"bm25": "BM25", "densa": "Densa (bge-small)", "hibrida": "Híbrida"}
ROTULOS_CONFIGURACAO = {"secao": "seção", "bm25": "BM25", "completo": "completo"}


def num(valor: float | None, casas: int = 2) -> str:
    """Número no padrão brasileiro; ausente vira travessão."""
    if valor is None:
        return AUSENTE
    return f"{valor:.{casas}f}".replace(".", ",")


def faixa(par: list[float] | None) -> str:
    """Intervalo de Wilson como `[piso; teto]`."""
    if par is None:
        return AUSENTE
    return f"[{num(par[0])}; {num(par[1])}]"


def escapar(texto: str) -> str:
    """Texto literal dentro de conteúdo Typst.

    Além dos caracteres de marcação, escapa a barra (`//` e `/*` abrem
    comentário) e os marcadores que só valem no início do texto: `-` (lista),
    `+` e `1.` (enumeração) e `=` (título).
    """
    for caractere in _ESPECIAIS:
        texto = texto.replace(caractere, "\\" + caractere)
    return _MARCADOR_INICIAL.sub(lambda m: m.group(1) + m.group(2)[:-1] + "\\" + m.group(2)[-1], texto)


def carregar(caminho: Path = CONSOLIDADO) -> dict:
    return json.loads(caminho.read_text(encoding="utf-8"))


def _celula(texto: str) -> str:
    return f"[{escapar(texto)}]"


def _negrito(texto: str) -> str:
    return f"[*{escapar(texto)}*]"


def _figura(rotulo: str, legenda: str, cabecalho: list[str], linhas: list[list[str]], alinhamento: list[str], origem: str) -> str:
    """Uma tabela ABNT: legenda acima, fonte abaixo. `linhas` já vem em células Typst."""
    partes = [
        "// Gerado por `python -m academico tabelas`. Nao editar a mao.",
        '#import "../abnt.typ": fonte',
        "#figure(",
        "  table(",
        f"    columns: {len(cabecalho)},",
        f"    align: ({', '.join(alinhamento)}),",
        f"    table.header({', '.join(_negrito(c) for c in cabecalho)}),",
    ]
    partes += [f"    {', '.join(linha)}," for linha in linhas]
    partes += [
        "  ),",
        f"  caption: [{escapar(legenda)}],",
        f") <{rotulo}>",
        f"#fonte[Elaborado pelo autor a partir de `{origem}`.]",
        "",
    ]
    return "\n".join(partes)


def com_piso_e_teto(taxa: dict) -> str:
    """Proporção principal e, entre parênteses, piso–teto quando os indeterminados os afastam dela."""
    principal = taxa["principal"]
    piso, teto = taxa.get("piso", principal), taxa.get("teto", principal)
    if piso == principal and teto == principal:
        return num(principal)
    return f"{num(principal)} ({num(piso)}–{num(teto)})"


def _linha_regra(nome: str, dados: dict, negrito: bool = False) -> list[str]:
    m = dados["matriz"]
    rotulo = _negrito(nome) if negrito else _celula(nome)
    return [
        rotulo,
        _celula(str(m["vp"])),
        _celula(str(m["fp"])),
        _celula(str(m["fn"])),
        _celula(str(m["ind_marcados"])),
        _celula(str(m["ind_nao_marcados"])),
        _celula(com_piso_e_teto(dados["taxas"]["precisao"])),
        _celula(faixa((dados.get("wilson") or {}).get("precisao"))),
        _celula(com_piso_e_teto(dados["taxas"]["recall"])),
    ]


def tabela_regras(bloco: dict, rotulo: str, legenda: str) -> str:
    """Indeterminados em duas colunas: os que a regra marcou (Ind. M) entram no
    denominador da precisão; os que ela não marcou (Ind. NM), só no da revocação."""
    linhas = [_linha_regra(regra, bloco["por_regra"][regra]) for regra in sorted(bloco["por_regra"])]
    linhas.append(_linha_regra("Total (micro)", bloco["total_micro"], negrito=True))
    return _figura(
        rotulo,
        legenda,
        ["Regra", "VP", "FP", "FN", "Ind. M", "Ind. NM", "Precisão (piso–teto)", "IC 95% (Wilson)", "Revocação (piso–teto)"],
        linhas,
        ["left"] + ["right"] * 8,
        bloco["origem"],
    )


def tabela_recuperacao(bloco: dict) -> str:
    macro = bloco["macro"]
    linhas = [
        [_celula(k), _celula(num(macro["acerto"][k])), _celula(num(macro["precisao"][k]))]
        for k in ("1", "3", "5", "10")
    ]
    linhas.append([_celula("MRR@10"), _celula(num(macro["mrr"])), _celula(AUSENTE)])
    cfg = bloco["configuracao"]
    legenda = (
        f"Recuperação vencedora (fragmento por {ROTULOS_CONFIGURACAO.get(cfg['chunking'], cfg['chunking'])}, "
        f"busca {ROTULOS_CONFIGURACAO.get(cfg['busca'], cfg['busca'])}, corpus {ROTULOS_CONFIGURACAO.get(cfg['corpus'], cfg['corpus'])}): "
        f"médias macro por regra em {macro['consultas']} consultas"
    )
    return _figura("tab-recuperacao", legenda, ["K", "Acerto@K", "Precisão@K"], linhas, ["left", "right", "right"], bloco["origem"])


def tabela_complementares(bloco: dict) -> str:
    linhas = [
        [_celula(ROTULOS_ESTRATEGIA.get(nome, nome)), _celula(num(v["principal"])), _celula(num(v["piso"])), _celula(num(v["teto"]))]
        for nome, v in bloco["macro"].items()
    ]
    return _figura(
        "tab-complementares",
        "Pertinência dos trechos complementares por estratégia de busca (média macro)",
        ["Estratégia", "Principal", "Piso", "Teto"],
        linhas,
        ["left", "right", "right", "right"],
        bloco["origem"],
    )


def _sim_de_n(contagem: dict) -> str:
    n = contagem["sim"] + contagem["nao"] + contagem["indeterminado"]
    return f"{contagem['sim']} / {n}"


def _linha_item(rotulo: str, total: dict, negrito: bool = False) -> list[str]:
    return [
        _negrito(rotulo) if negrito else _celula(rotulo),
        _celula(_sim_de_n(total["n"])),
        _celula(num(total["principal"])),
        _celula(faixa(total["wilson"])),
    ]


def tabela_geracao(bloco: dict) -> str:
    linhas = [_linha_item(ROTULOS_GERACAO[nome], bloco["itens"][nome]["total"]) for nome in ROTULOS_GERACAO]
    linhas.append(_linha_item("Utilizável como está", bloco["utilizavel"]["total"], negrito=True))
    return _figura(
        "tab-geracao",
        "Rubrica humana das explicações geradas: proporção de \"sim\" por item",
        ["Item", "Sim / n", "Proporção", "IC 95% (Wilson)"],
        linhas,
        ["left", "right", "right", "right"],
        bloco["origem"],
    )


def tabela_geracao_por_regra(bloco: dict) -> str:
    linhas = []
    for regra in sorted(bloco["itens"]["fiel"]["por_regra"]):
        fiel = bloco["itens"]["fiel"]["por_regra"][regra]["n"]
        recomendacao = bloco["itens"]["recomendacao_correta"]["por_regra"][regra]["n"]
        utilizavel = bloco["utilizavel"]["por_regra"][regra]["n"]
        n = fiel["sim"] + fiel["nao"] + fiel["indeterminado"]
        linhas.append([_celula(regra), _celula(str(n)), _celula(_sim_de_n(fiel)), _celula(_sim_de_n(recomendacao)), _celula(_sim_de_n(utilizavel))])
    return _figura(
        "tab-geracao-por-regra",
        "Rubrica humana das explicações por regra",
        ["Regra", "Achados", "Fiel", "Recomendação correta", "Utilizável"],
        linhas,
        ["left"] + ["right"] * 4,
        bloco["origem"],
    )


def tabela_concordancia(bloco: dict) -> str:
    linhas = []
    for nome, automatico in CRITERIO_AUTOMATICO.items():
        c = bloco["concordancia"][nome]
        t = c["tabela"]
        linhas.append([
            _celula(ROTULOS_GERACAO[nome]),
            _celula(automatico),
            _celula(str(t["a"])),
            _celula(str(t["b"])),
            _celula(str(t["c"])),
            _celula(str(t["d"])),
            _celula(num(c["concordancia"])),
            _celula(num(c["kappa"])),
        ])
    return _figura(
        "tab-concordancia",
        "Concordância entre a leitura humana e a conferência automática "
        "(a: ambos sim; b: só o automático diz sim; c: só o humano diz sim; d: ambos não)",
        ["Item humano", "Critério automático", "a", "b", "c", "d", "Concordância", "Kappa"],
        linhas,
        ["left", "left"] + ["right"] * 6,
        bloco["origem"],
    )


ROTULOS_GLOSSARIO = {**ROTULOS_GERACAO, "utilizavel": "Utilizável como está"}


def valor_p(p: float) -> str:
    return "<0,001" if p < 0.001 else num(p, 3)


def _rotulo_item(nome: str) -> str:
    return _negrito(ROTULOS_GLOSSARIO[nome]) if nome == "utilizavel" else _celula(ROTULOS_GLOSSARIO[nome])


def _de(sim: int, n: int, proporcao: bool = True) -> str:
    return f"{sim} / {n} ({num(sim / n)})" if proporcao else f"{sim} / {n}"


def tabela_glossario(bloco: dict) -> str:
    linhas = []
    for nome in ROTULOS_GLOSSARIO:
        v = bloco["itens"][nome]
        o, g, d = v["original"], v["glossario"], v["discordantes"]
        linhas.append([_rotulo_item(nome), _celula(_de(o["sim"], o["n"])), _celula(_de(g["sim"], g["n"])),
                       _celula(str(d["so_original"])), _celula(str(d["so_glossario"])), _celula(valor_p(v["p_mcnemar"]))])
    return _figura(
        "tab-glossario",
        "Glossário na instrução, comparação pareada nos 61 achados (análise de erros): vereditos de 14/10 para as "
        "explicações originais e da nova sessão para as com glossário",
        ["Item", "Original", "Com glossário", "Só original", "Só glossário", "p (McNemar)"],
        linhas,
        ["left"] + ["right"] * 5,
        bloco["origem"],
    )


def tabela_glossario_sessao(bloco: dict) -> str:
    exploratoria = bloco["exploratoria_mesma_sessao"]
    n = exploratoria["n"]
    linhas = []
    for nome in ROTULOS_GLOSSARIO:
        c, e = bloco["consistencia"][nome], exploratoria["itens"][nome]
        linhas.append([_rotulo_item(nome), _celula(num(c["concordancia"])), _celula(num(c["kappa"])),
                       _celula(_de(e["original_reanotada"], n, False)), _celula(_de(e["glossario"], n, False)),
                       _celula(num(e["p_mcnemar"], 3))])
    return _figura(
        "tab-glossario-sessao",
        f"Os {n} achados reanotados: consistência do anotador entre 14/10 e a nova sessão, e comparação das duas "
        "versões só com vereditos da nova sessão (análise exploratória, fora do protocolo)",
        ["Item", "Concordância", "Kappa", "Original reanotada", "Com glossário", "p (McNemar)"],
        linhas,
        ["left"] + ["right"] * 5,
        bloco["origem"],
    )


ROTULOS_CATEGORIA = {"modelagem": "modelagem", "performance": "desempenho", "dax": "DAX"}
ROTULOS_SEVERIDADE = {"alta": "alta", "media": "média", "baixa": "baixa"}


def tabela_catalogo() -> str:
    linhas = [
        [
            _celula(m.id),
            _celula(m.titulo),
            _celula(ROTULOS_CATEGORIA.get(m.categoria, m.categoria)),
            _celula(ROTULOS_SEVERIDADE.get(m.severidade, m.severidade)),
            f'[#link("{m.url_canonica}")[{escapar(m.url_canonica)}]]',
        ]
        for m in REGISTRO.metas()
    ]
    return _figura(
        "tab-catalogo",
        "Catálogo das regras e a página do Microsoft Learn que ancora cada uma",
        ["ID", "Regra", "Categoria", "Severidade", "Âncora"],
        linhas,
        ["left"] * 5,
        "core/rules/todas.py",
    )


SIGLAS_INDETERMINADOS = "; Ind. M e Ind. NM: indeterminados marcados e não marcados pela regra"


def gerar_todas(consolidado: dict) -> dict[str, str]:
    regras = consolidado["regras"]
    pos = consolidado["regras_pos_correcao"]
    return {
        "regras.typ": tabela_regras(regras, "tab-regras", f"Desempenho das regras contra o gabarito em P1–P7 ({regras['rotulo']}){SIGLAS_INDETERMINADOS}"),
        "regras-pos-correcao.typ": tabela_regras(pos, "tab-regras-pos-correcao", f"Desempenho das regras após a correção da MOD-003 e da PERF-001 ({pos['rotulo']}){SIGLAS_INDETERMINADOS}"),
        "recuperacao.typ": tabela_recuperacao(consolidado["recuperacao"]),
        "complementares.typ": tabela_complementares(consolidado["complementares"]),
        "geracao.typ": tabela_geracao(consolidado["geracao"]),
        "geracao-por-regra.typ": tabela_geracao_por_regra(consolidado["geracao"]),
        "concordancia.typ": tabela_concordancia(consolidado["geracao"]),
        "glossario.typ": tabela_glossario(consolidado["glossario"]),
        "glossario-sessao.typ": tabela_glossario_sessao(consolidado["glossario"]),
        "catalogo.typ": tabela_catalogo(),
    }


def escrever(tabelas: dict[str, str], pasta: Path = PASTA_GERADO) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, conteudo in tabelas.items():
        (pasta / nome).write_text(conteudo, encoding="utf-8", newline="\n")


README = RAIZ_REPO / "README.md"


def _md(cabecalho: list[str], linhas: list[list[str]]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    saida += ["| " + " | ".join(linha) + " |" for linha in linhas]
    return "\n".join(saida)


def blocos_markdown(consolidado: dict) -> dict[str, str]:
    """As três tabelas principais, em Markdown, para a seção Resultados do README."""
    regras = consolidado["regras"]
    linhas_regras = []
    for regra in sorted(regras["por_regra"]):
        d = regras["por_regra"][regra]
        m = d["matriz"]
        linhas_regras.append([regra, str(m["vp"]), str(m["fp"]), str(m["fn"]), num(d["taxas"]["precisao"]["principal"]), faixa((d.get("wilson") or {}).get("precisao"))])
    t = regras["total_micro"]
    linhas_regras.append(["**Total (micro)**", str(t["matriz"]["vp"]), str(t["matriz"]["fp"]), str(t["matriz"]["fn"]), num(t["taxas"]["precisao"]["principal"]), faixa(t["wilson"]["precisao"])])

    rec = consolidado["recuperacao"]["macro"]
    linhas_rec = [[k, num(rec["acerto"][k]), num(rec["precisao"][k])] for k in ("1", "3", "5", "10")]
    linhas_rec.append(["MRR@10", num(rec["mrr"]), AUSENTE])

    ger = consolidado["geracao"]
    linhas_ger = [
        [ROTULOS_GERACAO[n], _sim_de_n(ger["itens"][n]["total"]["n"]), num(ger["itens"][n]["total"]["principal"]), faixa(ger["itens"][n]["total"]["wilson"])]
        for n in ROTULOS_GERACAO
    ]
    u = ger["utilizavel"]["total"]
    linhas_ger.append(["**Utilizável como está**", _sim_de_n(u["n"]), num(u["principal"]), faixa(u["wilson"])])

    return {
        "regras": _md(["Regra", "VP", "FP", "FN", "Precisão", "IC 95% (Wilson)"], linhas_regras),
        "recuperacao": _md(["K", "Acerto@K", "Precisão@K"], linhas_rec),
        "geracao": _md(["Item", "Sim / n", "Proporção", "IC 95% (Wilson)"], linhas_ger),
    }


def atualizar_readme(texto: str, blocos: dict[str, str]) -> str:
    """Troca o miolo de cada bloco `<!-- tabela:nome -->` … `<!-- /tabela -->`."""
    for nome, conteudo in blocos.items():
        abertura = f"<!-- tabela:{nome} -->\n"
        inicio = texto.find(abertura)
        if inicio < 0:
            raise KeyError(f"bloco <!-- tabela:{nome} --> ausente do README")
        miolo = inicio + len(abertura)
        fim = texto.index("<!-- /tabela -->", miolo)
        texto = texto[:miolo] + conteudo + "\n" + texto[fim:]
    return texto
