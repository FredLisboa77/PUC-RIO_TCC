"""Leitura do `model.bim` (TMSL) para o modelo interno normalizado.

Princípio: nunca falhar por uma propriedade ausente ou desconhecida. O conjunto
de propriedades do TMSL varia com o `compatibilityLevel`, e a Microsoft
acrescenta propriedades sem aviso. Tudo o que não é reconhecido segue em
`bruto`, disponível para as regras.

O mesmo princípio vale para uma propriedade **presente com valor nulo** — um
`model.bim` editado à mão ou gerado por outra ferramenta pode escrever
`"name": null` onde o TMSL esperaria uma string. Toda lista lida daqui usa
`or []`, e todo escalar que alimenta um campo obrigatório do Pydantic usa
`or ""`; `ler_modelo` também recusa, com mensagem clara, um JSON cujo nível
superior não é um objeto. `core/ingest.py` só valida que o arquivo existe,
nunca o conteúdo — então todos esses casos chegam aqui a partir de um arquivo
que a ferramenta já disse saber ler.
"""

import json
from pathlib import Path
from typing import Any

from core.model import (
    Coluna,
    Hierarquia,
    Medida,
    ModeloSemantico,
    Nivel,
    Particao,
    PermissaoDeTabela,
    Relacionamento,
    Role,
    Tabela,
)


def _texto(valor: Any) -> str | None:
    """Normaliza uma expressão DAX ou M.

    O TMSL grava expressões ora como string, ora como lista de linhas. As regras
    trabalham sempre com uma string só, com quebras de linha preservadas.
    """
    if valor is None:
        return None
    if isinstance(valor, list):
        return "\n".join(str(linha) for linha in valor)
    return str(valor)


def _coluna(bruto: dict) -> Coluna:
    return Coluna(
        nome=bruto.get("name") or "",
        tipo_dado=bruto.get("dataType"),
        tipo=bruto.get("type"),
        resumir_por=bruto.get("summarizeBy"),
        expressao=_texto(bruto.get("expression")),
        oculta=bool(bruto.get("isHidden", False)),
        ordenar_por=bruto.get("sortByColumn"),
        bruto=bruto,
    )


def _medida(bruto: dict, tabela: str) -> Medida:
    return Medida(
        nome=bruto.get("name") or "",
        expressao=_texto(bruto.get("expression")) or "",
        tabela=tabela,
        pasta=bruto.get("displayFolder"),
        formato=bruto.get("formatString"),
        oculta=bool(bruto.get("isHidden", False)),
        bruto=bruto,
    )


def _particao(bruto: dict) -> Particao:
    origem = bruto.get("source") or {}
    return Particao(
        nome=bruto.get("name") or "",
        modo=bruto.get("mode"),
        tipo_origem=origem.get("type"),
        origem=_texto(origem.get("expression")),
        bruto=bruto,
    )


def _nivel(bruto: dict, tabela: str) -> Nivel:
    return Nivel(
        nome=bruto.get("name") or "",
        tabela=tabela,
        coluna=bruto.get("column") or "",
        ordem=bruto.get("ordinal"),
    )


def _hierarquia(bruto: dict, tabela: str) -> Hierarquia:
    return Hierarquia(
        nome=bruto.get("name") or "",
        tabela=tabela,
        niveis=[_nivel(n, tabela) for n in bruto.get("levels") or []],
    )


def _role(bruto: dict) -> Role:
    return Role(
        nome=bruto.get("name") or "",
        permissoes=[
            PermissaoDeTabela(
                tabela=p.get("name") or "",
                expressao_filtro=_texto(p.get("filterExpression")),
            )
            for p in bruto.get("tablePermissions") or []
        ],
    )


def _tabela(bruto: dict) -> Tabela:
    nome = bruto.get("name") or ""
    return Tabela(
        nome=nome,
        oculta=bool(bruto.get("isHidden", False)),
        data_category=bruto.get("dataCategory"),
        colunas=[_coluna(c) for c in bruto.get("columns") or []],
        medidas=[_medida(m, nome) for m in bruto.get("measures") or []],
        particoes=[_particao(p) for p in bruto.get("partitions") or []],
        hierarquias=[_hierarquia(h, nome) for h in bruto.get("hierarchies") or []],
        bruto=bruto,
    )


CARDINALIDADE = {"one": "um", "many": "muitos"}


def _cardinalidade(valor: Any, padrao: str) -> str:
    """Normaliza `fromCardinality`/`toCardinality` para o vocabulário interno.

    Ausentes, os dois significam muitos-para-um: o lado `from` é "muitos" e o
    lado `to` é "um". Quando presentes vêm em inglês. As regras dependem disso:
    um `fromCardinality: "one"` explícito descreve um relacionamento
    um-para-um, e tratá-lo como muitos-para-um inverteria os lados.
    """
    if valor is None:
        return padrao
    return CARDINALIDADE.get(str(valor), str(valor))


def _relacionamento(bruto: dict) -> Relacionamento:
    # No TMSL, `crossFilteringBehavior` ausente significa filtro em um sentido.
    # "automatic" deixa o motor decidir; para efeito de auditoria só interessa
    # distinguir o bidirecional explícito, que é o padrão problemático.
    bidirecional = bruto.get("crossFilteringBehavior") == "bothDirections"

    return Relacionamento(
        nome=bruto.get("name") or "",
        tabela_origem=bruto.get("fromTable") or "",
        coluna_origem=bruto.get("fromColumn") or "",
        tabela_destino=bruto.get("toTable") or "",
        coluna_destino=bruto.get("toColumn") or "",
        direcao_filtro="ambos_sentidos" if bidirecional else "um_sentido",
        ativo=bool(bruto.get("isActive", True)),
        cardinalidade_origem=_cardinalidade(bruto.get("fromCardinality"), "muitos"),
        cardinalidade_destino=_cardinalidade(bruto.get("toCardinality"), "um"),
        bruto=bruto,
    )


def ler_modelo(caminho: str | Path) -> ModeloSemantico:
    """Lê um `model.bim` e devolve o modelo normalizado."""
    dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        # JSON válido, mas não é um objeto no nível superior (é lista, string,
        # número...). `ler_modelo` promete nunca falhar por propriedade
        # ausente ou desconhecida — mas isto não é uma propriedade ausente, é
        # o arquivo inteiro não ser o que a ingestão já confirmou chamar-se
        # `model.bim`. Sem esta guarda, `dados.get(...)` a seguir levantaria
        # `AttributeError: 'list' object has no attribute 'get'` — traceback
        # cru numa ferramenta que acabou de dizer que conseguia ler o arquivo.
        raise ValueError(
            f"{caminho}: o JSON de topo não é um objeto (é {type(dados).__name__})"
        )
    # `.get("model", {})` só cairia no padrão com a chave ausente; um
    # `model.bim` editado à mão com `"model": null` tem a chave presente e
    # valor nulo, e `.get` devolveria `None` — e `model.get(...)` abaixo
    # levantaria `AttributeError: 'NoneType' has no attribute 'get'`.
    model = dados.get("model") or {}

    return ModeloSemantico(
        nome=dados.get("name") or "",
        compatibility_level=dados.get("compatibilityLevel"),
        cultura=model.get("culture"),
        tabelas=[_tabela(t) for t in model.get("tables") or []],
        relacionamentos=[
            _relacionamento(r) for r in model.get("relationships") or []
        ],
        roles=[_role(r) for r in model.get("roles") or []],
    )
