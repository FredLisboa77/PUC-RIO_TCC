# Gabarito das regras em P1–P7 — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** gerar uma planilha cega com todos os candidatos de cada regra em P1–P7, importar os vereditos do Fred para `eval/ground_truth.csv` e medir precisão e recall por regra.

**Architecture:** pacote novo `gabarito/` com três unidades. `candidatos.py` monta o universo e os fatos neutros de cada regra a partir do `ModeloSemantico`, sem chamar funções de regra. `planilha.py` grava e lê o `.xlsx` e o CSV. `metricas.py` cruza o gabarito com os achados. `__main__.py` expõe `gerar | importar [--parcial] | medir`.

**Tech Stack:** Python 3.11, Pydantic 2, `openpyxl` (dependência nova), pytest.

**Spec:** `docs/superpowers/specs/2026-10-11-gabarito-das-regras-design.md`

## Global Constraints

- Tudo em português do Brasil: código, nomes, testes, mensagens, commits.
- Dependência nova única: `openpyxl==3.1.5`, fixada em `requirements.txt`; instalar com `.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5` (o `.venv/pip.ini` já trata o TLS do Norton).
- Chave de cruzamento: `id = "<id_regra>|<projeto>|<objeto>"`, com `objeto` **idêntico** a `Evidencia.objeto` da regra.
- Vereditos exatamente: `viola`, `não viola`, `indeterminado`.
- Cegueira: nenhuma célula da planilha traz severidade, mensagem, `detalhe` ou indicação de que o candidato foi marcado.
- Planilha em `eval/gabarito/anotacao-P1-P7.xlsx` (fora do Git); gabarito oficial em `eval/ground_truth.csv` (UTF-8, vírgula, versionado); resultados em `eval/results/regras-<AAAA-MM-DD>.json`.
- Precisão e recall sem divisor → `None`/`null` (console: `-`), nunca 0 nem 1. Gatilho R-03: precisão principal < 0,7. Gatilho R-12: VP total contra 40, com e sem PERF-003.
- Saída de console em ASCII (o console do Windows quebra com acento fora do cp1252).
- Testes: `.\.venv\Scripts\python.exe -m pytest -q` na raiz; testes sobre `data/` pulados quando a pasta não existe.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push autorizado na branch `fase3-gabarito-regras`.

## Review Focus

- **Objeto com caractere especial** (`→` dos relacionamentos, aspas, colchetes, acento em `Salário`) — a planilha grava e relê o ID idêntico, e o cruzamento casa (teste na Tarefa 3).
- **Veredito digitado à mão com variação** (`Viola`, ` não viola `, `nao viola`) — a lista suspensa impede no Excel, mas colar texto contorna; a importação recusa e aponta a linha, sem normalizar em silêncio (teste na Tarefa 4).
- **Regra sem nenhum achado e sem nenhuma violação** — precisão e recall `None`, macro ignora o `None`, e o console mostra `-` (teste na Tarefa 5).
- **Planilha aberta no Excel durante `importar`** — `PermissionError` vira mensagem com código 1, sem traceback (teste na Tarefa 6).
- **Tabela de data automática** — entra só como candidato da MOD-001; nas outras regras ela é artefato do produto, e não pode virar FN (teste na Tarefa 1).

---

### Task 1: Candidato, carga do dataset e candidatos de tabela e relacionamento

**Files:**
- Modify: `requirements.txt` (acrescentar `openpyxl==3.1.5`)
- Create: `gabarito/__init__.py`
- Create: `gabarito/candidatos.py`
- Test: `tests/test_gabarito_candidatos.py`

**Interfaces:**
- Consumes: `ModeloSemantico`, `Tabela`, `Relacionamento` (`core.model`); `anotacoes`, `tabela_automatica_de_data`, `um_para_um`, `lado_um`, `lado_muitos` (`core.rules.escopo`); `PASTA_PBIP`, `PROJETOS` (`rag.avaliacao`); `abrir_pbip`, `ler_modelo`.
- Produces: `Candidato(id_regra, projeto, objeto, fatos: dict[str, str])` com propriedade `id`; `COLUNAS_DE_FATOS: dict[str, tuple[str, ...]]`; `candidatos_do_modelo(projeto: str, modelo: ModeloSemantico) -> list[Candidato]`; `modelos_do_dataset(pasta: Path = PASTA_PBIP) -> dict[str, ModeloSemantico]`; `candidatos_do_dataset(pasta: Path = PASTA_PBIP) -> list[Candidato]`; `ErroDeGabarito`; `nome_do_relacionamento(r) -> str`.

- [ ] **Step 1: Instalar a dependência e fixá-la**

Run: `.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5`
Acrescentar a linha `openpyxl==3.1.5` em `requirements.txt`, junto das outras dependências fixadas.

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_gabarito_candidatos.py`:

```python
"""Candidatos do gabarito: o universo de cada regra, com fatos neutros."""

from conftest import coluna, medida, relacionamento, tabela

from gabarito.candidatos import COLUNAS_DE_FATOS, candidatos_do_modelo


def _por_regra(candidatos, id_regra):
    return {c.objeto: c for c in candidatos if c.id_regra == id_regra}


def _modelo_basico(ler):
    return ler(
        tabelas=[
            tabela("Vendas", colunas=[coluna("ProdutoKey", tipo_dado="int64"), coluna("DataKey", tipo_dado="int64")]),
            tabela("Produto", colunas=[coluna("ProdutoKey", tipo_dado="int64"), coluna("CategoriaKey", tipo_dado="int64")]),
            tabela("Categoria", colunas=[coluna("CategoriaKey", tipo_dado="int64")]),
            tabela("Medidas", medidas=[medida("Total", "SUM(Vendas[ProdutoKey])")]),
            tabela(
                "LocalDateTable_1",
                colunas=[coluna("Date", tipo_dado="dateTime")],
                annotations={"__PBI_LocalDateTable": "true"},
            ),
        ],
        relacionamentos=[
            relacionamento("Vendas", "ProdutoKey", "Produto", "ProdutoKey", bidirecional=True),
            relacionamento("Produto", "CategoriaKey", "Categoria", "CategoriaKey"),
            relacionamento(
                "Produto", "ProdutoKey", "Categoria", "CategoriaKey",
                cardinalidade_origem="one", cardinalidade_destino="one", bidirecional=True,
            ),
        ],
    )


def test_id_junta_regra_projeto_e_objeto(ler):
    c = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-003")["Produto"]
    assert c.id == "MOD-003|P1|Produto"


def test_mod001_lista_todas_as_tabelas_inclusive_a_automatica(ler):
    mod001 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-001")
    assert set(mod001) == {"Vendas", "Produto", "Categoria", "Medidas", "LocalDateTable_1"}
    assert mod001["LocalDateTable_1"].fatos["anotacoes"] == "__PBI_LocalDateTable"


def test_tabela_automatica_so_e_candidata_da_mod001(ler):
    candidatos = candidatos_do_modelo("P1", _modelo_basico(ler))
    regras = {c.id_regra for c in candidatos if c.objeto == "LocalDateTable_1"}
    assert regras == {"MOD-001"}


def test_mod003_mostra_contagens_sem_julgar(ler):
    mod003 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-003")
    assert set(mod003) == {"Vendas", "Produto", "Categoria", "Medidas"}
    assert mod003["Medidas"].fatos == {"relacionamentos": "0", "medidas": "1", "colunas": "0", "oculta": "não"}
    assert mod003["Produto"].fatos["relacionamentos"] == "3"


def test_mod002_exclui_um_para_um_e_mod007_lista_todos(ler):
    candidatos = candidatos_do_modelo("P1", _modelo_basico(ler))
    mod002 = _por_regra(candidatos, "MOD-002")
    mod007 = _por_regra(candidatos, "MOD-007")
    assert set(mod002) == {"Vendas[ProdutoKey] → Produto[ProdutoKey]", "Produto[CategoriaKey] → Categoria[CategoriaKey]"}
    assert len(mod007) == 3
    um_para_um = mod007["Produto[ProdutoKey] → Categoria[CategoriaKey]"]
    assert um_para_um.fatos["cardinalidades"] == "um:um"
    assert mod002["Vendas[ProdutoKey] → Produto[ProdutoKey]"].fatos["direcao"] == "ambos_sentidos"


def test_mod006_mostra_quem_filtra_e_quem_e_filtrado(ler):
    mod006 = _por_regra(candidatos_do_modelo("P1", _modelo_basico(ler)), "MOD-006")
    produto = mod006["Produto"].fatos
    # Vendas → Produto (muitos:um): Produto filtra Vendas. Produto → Categoria
    # (muitos:um): Categoria filtra Produto. O um-para-um não tem lado "muitos".
    assert produto["filtra"] == "Vendas"
    assert produto["filtrada_por"] == "Categoria"


def test_todo_candidato_tem_exatamente_as_colunas_de_fatos_da_regra(ler):
    for c in candidatos_do_modelo("P1", _modelo_basico(ler)):
        assert tuple(c.fatos) == COLUNAS_DE_FATOS[c.id_regra], c.id
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_candidatos.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gabarito'`

- [ ] **Step 4: Implementar**

`gabarito/__init__.py`:

```python
"""Gabarito das regras em P1–P7 (Fase 3, semana 8).

Desenho: `docs/superpowers/specs/2026-10-11-gabarito-das-regras-design.md`.
"""
```

`gabarito/candidatos.py`:

```python
"""O universo de candidatos de cada regra, com fatos neutros para o julgamento.

Os candidatos são montados a partir do `ModeloSemantico`, sem chamar as funções
de regra: se saíssem da lógica da regra, o recall mediria a regra contra ela
mesma. Os fatos são os mesmos para candidato marcado e não marcado — é o que
mantém o julgamento cego. O objeto usa o mesmo nome que a regra põe em
`Evidencia.objeto`, porque é a chave do cruzamento.

Ressalva declarada: os candidatos saem do mesmo parser que alimenta as regras;
um objeto que o parser não lê fica fora dos dois lados.
"""

from pathlib import Path

from pydantic import BaseModel

from core.ingest import abrir_pbip
from core.model import ModeloSemantico, Relacionamento, Tabela
from core.parser_bim import ler_modelo
from core.rules.escopo import anotacoes, lado_muitos, lado_um, tabela_automatica_de_data, um_para_um
from rag.avaliacao import PASTA_PBIP, PROJETOS

COLUNAS_DE_FATOS: dict[str, tuple[str, ...]] = {
    "MOD-001": ("oculta", "anotacoes", "colunas"),
    "MOD-002": ("direcao", "cardinalidades", "ativo"),
    "MOD-003": ("relacionamentos", "medidas", "colunas", "oculta"),
    "MOD-005": ("colunas_de_data",),
    "MOD-006": ("filtra", "filtrada_por"),
    "MOD-007": ("cardinalidades", "direcao"),
    "PERF-001": ("expressao",),
    "PERF-003": ("tipo_dado", "resumir_por"),
    "DAX-001": ("sitio", "expressao", "divisoes"),
}


class ErroDeGabarito(Exception):
    """O gabarito não pode ser gerado, importado ou medido sem perder algo em silêncio."""


class Candidato(BaseModel):
    id_regra: str
    projeto: str
    objeto: str
    fatos: dict[str, str]

    @property
    def id(self) -> str:
        return f"{self.id_regra}|{self.projeto}|{self.objeto}"


def _sim_nao(valor: bool) -> str:
    return "sim" if valor else "não"


def nome_do_relacionamento(r: Relacionamento) -> str:
    """O mesmo formato de `core.rules.modelagem._nome_do_relacionamento`."""
    return f"{r.tabela_origem}[{r.coluna_origem}] → {r.tabela_destino}[{r.coluna_destino}]"


def _tabelas_do_autor(modelo: ModeloSemantico) -> list[Tabela]:
    """Todas as tabelas menos as de data automática: essas são artefato do produto,
    julgadas só na MOD-001, e não podem virar falso negativo das outras regras."""
    return [t for t in modelo.tabelas if not tabela_automatica_de_data(t)]


def _mod001(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    return [
        Candidato(
            id_regra="MOD-001",
            projeto=projeto,
            objeto=t.nome,
            fatos={
                "oculta": _sim_nao(t.oculta),
                "anotacoes": ", ".join(sorted(anotacoes(t.bruto))),
                "colunas": str(len(t.colunas)),
            },
        )
        for t in modelo.tabelas
    ]


def _cardinalidades(r: Relacionamento) -> str:
    return f"{r.cardinalidade_origem}:{r.cardinalidade_destino}"


def _mod002(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    return [
        Candidato(
            id_regra="MOD-002",
            projeto=projeto,
            objeto=nome_do_relacionamento(r),
            fatos={"direcao": r.direcao_filtro, "cardinalidades": _cardinalidades(r), "ativo": _sim_nao(r.ativo)},
        )
        for r in modelo.relacionamentos
        if not um_para_um(r)
    ]


def _mod003(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    saida = []
    for t in _tabelas_do_autor(modelo):
        ligacoes = sum(1 for r in modelo.relacionamentos if t.nome in (r.tabela_origem, r.tabela_destino))
        saida.append(
            Candidato(
                id_regra="MOD-003",
                projeto=projeto,
                objeto=t.nome,
                fatos={
                    "relacionamentos": str(ligacoes),
                    "medidas": str(len(t.medidas)),
                    "colunas": str(len(t.colunas)),
                    "oculta": _sim_nao(t.oculta),
                },
            )
        )
    return saida


def _mod006(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    """Filtro desce do lado "um" para o lado "muitos"."""
    saida = []
    for t in _tabelas_do_autor(modelo):
        filtra: set[str] = set()
        filtrada_por: set[str] = set()
        for r in modelo.relacionamentos:
            if t.nome in lado_um(r):
                filtra |= lado_muitos(r) - {t.nome}
            if t.nome in lado_muitos(r):
                filtrada_por |= lado_um(r) - {t.nome}
        saida.append(
            Candidato(
                id_regra="MOD-006",
                projeto=projeto,
                objeto=t.nome,
                fatos={"filtra": ", ".join(sorted(filtra)), "filtrada_por": ", ".join(sorted(filtrada_por))},
            )
        )
    return saida


def _mod007(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    return [
        Candidato(
            id_regra="MOD-007",
            projeto=projeto,
            objeto=nome_do_relacionamento(r),
            fatos={"cardinalidades": _cardinalidades(r), "direcao": r.direcao_filtro},
        )
        for r in modelo.relacionamentos
    ]


GERADORES = [_mod001, _mod002, _mod003, _mod006, _mod007]


def candidatos_do_modelo(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    saida = [c for gerador in GERADORES for c in gerador(projeto, modelo)]
    return sorted(saida, key=lambda c: c.id)


def modelos_do_dataset(pasta: Path = PASTA_PBIP) -> dict[str, ModeloSemantico]:
    modelos: dict[str, ModeloSemantico] = {}
    for codigo in PROJETOS:
        achadas = sorted(pasta.glob(f"{codigo}_*")) if pasta.is_dir() else []
        if not achadas:
            raise ErroDeGabarito(f"{codigo} não encontrado em {pasta} (data/ não é versionado)")
        modelos[codigo] = ler_modelo(abrir_pbip(achadas[0]).model_bim)
    return modelos


def candidatos_do_dataset(pasta: Path = PASTA_PBIP) -> list[Candidato]:
    return [c for projeto, modelo in modelos_do_dataset(pasta).items() for c in candidatos_do_modelo(projeto, modelo)]
```

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_candidatos.py -q`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt gabarito tests/test_gabarito_candidatos.py
git commit -m "feat(gabarito): candidatos de tabela e relacionamento"
```

---

### Task 2: Candidatos de data, coluna e DAX, e o casamento com os achados reais

**Files:**
- Modify: `gabarito/candidatos.py`
- Test: `tests/test_gabarito_candidatos.py` (acrescentar)

**Interfaces:**
- Consumes: `varrer_dax` (`core.rules.expressoes`), `TipoToken` (`core.dax`), `achados_dos_projetos` (`rag.avaliacao`), `Candidato`, `GERADORES` (Task 1).
- Produces: geradores `_mod005`, `_perf001`, `_perf003`, `_dax001` incluídos em `GERADORES`; `LIMITE_EXPRESSAO = 1500`; `TRECHO_DIVISAO = 100`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_gabarito_candidatos.py`:

```python
from pathlib import Path

import pytest

from rag.avaliacao import PASTA_PBIP, achados_dos_projetos
from gabarito.candidatos import candidatos_do_dataset


def test_mod005_lista_tabelas_com_coluna_de_data_e_a_variations(ler):
    modelo = ler(
        tabelas=[
            tabela("Calendario", colunas=[coluna("Data", tipo_dado="dateTime", variacao_para="LocalDateTable_9")]),
            tabela("Pedidos", colunas=[coluna("Emissao", tipo_dado="dateTime"), coluna("Valor", tipo_dado="double")]),
            tabela("Produto", colunas=[coluna("Nome")]),
        ]
    )
    mod005 = _por_regra(candidatos_do_modelo("P1", modelo), "MOD-005")
    assert set(mod005) == {"Calendario", "Pedidos"}
    assert mod005["Calendario"].fatos["colunas_de_data"] == "Data -> LocalDateTable_9"
    assert mod005["Pedidos"].fatos["colunas_de_data"] == "Emissao"


def test_perf001_lista_colunas_calculadas_com_a_expressao(ler):
    modelo = ler(
        tabelas=[
            tabela("Pessoa", colunas=[
                coluna("Salário", tipo="calculated", expressao="Pessoa[Base] * 1.1", tipo_dado="double"),
                coluna("Base", tipo_dado="double"),
            ])
        ]
    )
    perf001 = _por_regra(candidatos_do_modelo("P1", modelo), "PERF-001")
    assert set(perf001) == {"Pessoa[Salário]"}
    assert perf001["Pessoa[Salário]"].fatos["expressao"] == "Pessoa[Base] * 1.1"


def test_perf003_lista_toda_coluna_double_somada_ou_nao(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[
                coluna("Valor", tipo_dado="double", resumir_por="sum"),
                coluna("Taxa", tipo_dado="double"),
                coluna("Qtd", tipo_dado="int64", resumir_por="sum"),
            ])
        ]
    )
    perf003 = _por_regra(candidatos_do_modelo("P1", modelo), "PERF-003")
    assert set(perf003) == {"Fato[Valor]", "Fato[Taxa]"}
    assert perf003["Fato[Taxa]"].fatos == {"tipo_dado": "double", "resumir_por": "none"}


def test_dax001_lista_expressoes_com_barra_e_o_que_vem_depois_de_cada_uma(ler):
    modelo = ler(
        tabelas=[
            tabela("Fato", colunas=[coluna("Valor", tipo_dado="double")], medidas=[
                medida("Margem", "SUM(Fato[Valor]) / [Receita]"),
                medida("Metade", "SUM(Fato[Valor]) / 2"),
                medida("Total", "SUM(Fato[Valor])"),
            ])
        ]
    )
    dax001 = _por_regra(candidatos_do_modelo("P1", modelo), "DAX-001")
    assert set(dax001) == {"Fato[Margem]", "Fato[Metade]"}
    assert dax001["Fato[Margem]"].fatos["sitio"] == "medida"
    assert dax001["Fato[Margem]"].fatos["divisoes"] == "/ [Receita]"
    assert dax001["Fato[Metade]"].fatos["divisoes"] == "/ 2"


def test_expressao_longa_e_cortada(ler):
    longa = "SUM(Fato[Valor]) / [Receita] + " + "1 + " * 600 + "1"
    modelo = ler(tabelas=[tabela("Fato", colunas=[coluna("Valor", tipo_dado="double")], medidas=[medida("Longa", longa)])])
    fatos = _por_regra(candidatos_do_modelo("P1", modelo), "DAX-001")["Fato[Longa]"].fatos
    assert len(fatos["expressao"]) == 1500 + len(" […]")
    assert fatos["expressao"].endswith(" […]")


SEM_DADOS = not (PASTA_PBIP / "P1_AdventureWorks Sales").is_dir()


@pytest.mark.skipif(SEM_DADOS, reason="data/ não é versionado")
def test_todo_achado_real_de_p1_a_p7_casa_com_um_candidato():
    ids = {c.id for c in candidatos_do_dataset()}
    faltando = [
        f"{a.id_regra}|{projeto}|{a.evidencia.objeto}"
        for projeto, achados in achados_dos_projetos(PASTA_PBIP).items()
        for a in achados
        if f"{a.id_regra}|{projeto}|{a.evidencia.objeto}" not in ids
    ]
    assert faltando == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_candidatos.py -q`
Expected: os 5 testes novos de regra falham (conjuntos vazios) e o de dados reais falha listando os achados de MOD-005, PERF-001, PERF-003 e DAX-001 sem candidato.

- [ ] **Step 3: Implementar**

Em `gabarito/candidatos.py`, acrescentar aos imports `from core.dax import TipoToken` e `from core.rules.expressoes import varrer_dax`, e antes de `GERADORES`:

```python
LIMITE_EXPRESSAO = 1500
TRECHO_DIVISAO = 100
"""Quantos caracteres depois de cada `/` a linha mostra: o bastante para ver o
denominador, sem decidir por quem lê onde ele termina — isso é lógica da regra."""


def _cortar(texto: str) -> str:
    return texto if len(texto) <= LIMITE_EXPRESSAO else texto[:LIMITE_EXPRESSAO] + " […]"


def _destino_da_variations(bruto: dict) -> str | None:
    for variacao in bruto.get("variations") or []:
        destino = (variacao.get("defaultHierarchy") or {}).get("table")
        if destino:
            return destino
    return None


def _mod005(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    saida = []
    for t in _tabelas_do_autor(modelo):
        datas = [c for c in t.colunas if c.tipo_dado == "dateTime"]
        if not datas:
            continue
        descricoes = []
        for c in datas:
            destino = _destino_da_variations(c.bruto)
            descricoes.append(f"{c.nome} -> {destino}" if destino else c.nome)
        saida.append(
            Candidato(id_regra="MOD-005", projeto=projeto, objeto=t.nome, fatos={"colunas_de_data": "; ".join(descricoes)})
        )
    return saida


def _perf001(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    return [
        Candidato(
            id_regra="PERF-001", projeto=projeto, objeto=f"{t.nome}[{c.nome}]", fatos={"expressao": _cortar(c.expressao or "")}
        )
        for t in _tabelas_do_autor(modelo)
        for c in t.colunas_calculadas
    ]


def _perf003(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    return [
        Candidato(
            id_regra="PERF-003",
            projeto=projeto,
            objeto=f"{t.nome}[{c.nome}]",
            fatos={"tipo_dado": c.tipo_dado or "", "resumir_por": c.resumir_por or "none"},
        )
        for t in _tabelas_do_autor(modelo)
        for c in t.colunas
        if c.tipo_dado == "double"
    ]


def _dax001(projeto: str, modelo: ModeloSemantico) -> list[Candidato]:
    """Usa a varredura de DAX (o escopo de expressões do autor), não a regra: cada
    `/` aparece com o texto que vem depois, e quem julga decide o denominador."""
    saida = []
    for e in varrer_dax(modelo).expressoes:
        barras = [t for t in e.tokens if t.tipo is TipoToken.OPERADOR and t.texto == "/"]
        if not barras:
            continue
        divisoes = " | ".join(
            " ".join(e.texto[b.posicao : b.posicao + TRECHO_DIVISAO].split()) for b in barras
        )
        saida.append(
            Candidato(
                id_regra="DAX-001",
                projeto=projeto,
                objeto=e.objeto,
                fatos={"sitio": e.sitio, "expressao": _cortar(e.texto), "divisoes": divisoes},
            )
        )
    return saida
```

E trocar `GERADORES` por:

```python
GERADORES = [_mod001, _mod002, _mod003, _mod005, _mod006, _mod007, _perf001, _perf003, _dax001]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_candidatos.py -q`
Expected: 13 passed. Se o teste de dados reais ainda listar faltantes, o nome do objeto diverge da regra: comparar com `Evidencia.objeto` daquele achado e ajustar o gerador — nunca o teste.

- [ ] **Step 5: Commit**

```bash
git add gabarito/candidatos.py tests/test_gabarito_candidatos.py
git commit -m "feat(gabarito): candidatos de data, coluna e DAX; todo achado real casa"
```

---

### Task 3: Gerar a planilha cega

**Files:**
- Create: `gabarito/planilha.py`
- Test: `tests/test_gabarito_planilha.py`

**Interfaces:**
- Consumes: `Candidato`, `COLUNAS_DE_FATOS`, `ErroDeGabarito` (Tasks 1–2); `REGISTRO` (`core.rules.todas`) para o link de cada regra.
- Produces: `VEREDITOS = ("viola", "não viola", "indeterminado")`; `PERGUNTAS: dict[str, str]`; `LINHA_CABECALHO = 4`; `COLUNAS_EDITAVEIS = ("veredito", "justificativa", "referencia")`; `gerar_planilha(candidatos: list[Candidato], destino: Path) -> None`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_gabarito_planilha.py`:

```python
"""Planilha de anotação: cega, protegida, com lista suspensa."""

import pytest
from openpyxl import load_workbook

from gabarito.candidatos import COLUNAS_DE_FATOS, Candidato, ErroDeGabarito
from gabarito.planilha import LINHA_CABECALHO, PERGUNTAS, gerar_planilha


def _candidatos():
    return [
        Candidato(id_regra="MOD-002", projeto="P1", objeto="Vendas[Produto] → Produto[Produto]",
                  fatos={"direcao": "ambos_sentidos", "cardinalidades": "muitos:um", "ativo": "sim"}),
        Candidato(id_regra="PERF-001", projeto="P3", objeto="Pessoa[Salário]",
                  fatos={"expressao": "Pessoa[Base] * 1.1"}),
    ]


def _ids_da_aba(aba):
    return [aba.cell(row=r, column=1).value for r in range(LINHA_CABECALHO + 1, aba.max_row + 1)]


def test_uma_aba_por_regra_mais_instrucoes(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    livro = load_workbook(destino)
    assert livro.sheetnames == ["Instruções", *sorted(COLUNAS_DE_FATOS)]


def test_pergunta_no_topo_e_cabecalho_com_os_fatos(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    assert aba["A1"].value == PERGUNTAS["MOD-002"]
    assert aba["A2"].value.startswith("https://learn.microsoft.com/")
    cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
    assert cabecalho == ["id", "projeto", "objeto", "direcao", "cardinalidades", "ativo", "veredito", "justificativa", "referencia"]


def test_id_com_caracteres_especiais_volta_identico(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    livro = load_workbook(destino)
    assert _ids_da_aba(livro["MOD-002"]) == ["MOD-002|P1|Vendas[Produto] → Produto[Produto]"]
    assert _ids_da_aba(livro["PERF-001"]) == ["PERF-001|P3|Pessoa[Salário]"]


def test_veredito_tem_lista_suspensa(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    validacoes = aba.data_validations.dataValidation
    assert len(validacoes) == 1
    assert validacoes[0].formula1 == '"viola,não viola,indeterminado"'
    assert "G5" in str(validacoes[0].sqref)


def test_aba_protegida_com_so_as_colunas_de_anotacao_livres(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    aba = load_workbook(destino)["MOD-002"]
    assert aba.protection.sheet is True
    assert aba["A5"].protection.locked is True
    assert [aba.cell(row=5, column=c).protection.locked for c in (7, 8, 9)] == [False, False, False]


def test_planilha_e_cega(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    valores = [
        str(celula.value).strip().lower()
        for aba in load_workbook(destino).worksheets
        for linha in aba.iter_rows()
        for celula in linha
        if celula.value is not None
    ]
    textos = " ".join(valores)
    for proibido in ("severidade", "achado", "mensagem"):
        assert proibido not in textos, proibido
    assert not {"alta", "media", "média", "baixa"} & set(valores)


def test_recusa_sobrescrever(tmp_path):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    with pytest.raises(ErroDeGabarito, match="já existe"):
        gerar_planilha(_candidatos(), destino)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_planilha.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gabarito.planilha'`

- [ ] **Step 3: Implementar**

`gabarito/planilha.py`:

```python
"""A planilha de anotação do gabarito (`.xlsx`) e o CSV oficial.

A planilha é cega: lista todos os candidatos com os mesmos fatos neutros, sem
dizer quais a ferramenta marcou. Fica protegida, com só as colunas de anotação
livres, para que um fato ou um ID não seja editado por engano.
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.worksheet.datavalidation import DataValidation

import core.rules.todas  # noqa: F401 — registra as regras
from core.rules.registry import REGISTRO
from gabarito.candidatos import COLUNAS_DE_FATOS, Candidato, ErroDeGabarito

VEREDITOS = ("viola", "não viola", "indeterminado")
COLUNAS_EDITAVEIS = ("veredito", "justificativa", "referencia")
LINHA_CABECALHO = 4

PERGUNTAS = {
    "MOD-001": "Esta tabela foi gerada pelo Tempo automático de data/hora?",
    "MOD-002": "Este relacionamento filtra nos dois sentidos sem que o cenário exija isso, segundo a orientação de relacionamentos bidirecionais?",
    "MOD-003": "Esta tabela deveria se relacionar com o resto do modelo, segundo o star schema? (Tabela de medidas ou de parâmetros isolada de propósito: não viola.)",
    "MOD-005": "Esta tabela funciona como dimensão de data e não está marcada como tabela de data?",
    "MOD-006": "Esta tabela é o elo intermediário de uma dimensão em floco de neve que deveria ser desnormalizada?",
    "MOD-007": "Este relacionamento é um-para-um entre tabelas que descrevem a mesma entidade?",
    "PERF-001": "Esta coluna calculada poderia ser criada no Power Query ou na origem, como a orientação de redução de dados recomenda?",
    "PERF-003": "Esta coluna de ponto flutuante é somada de forma que a imprecisão do tipo possa afetar o resultado?",
    "DAX-001": "Alguma divisão desta expressão tem denominador que pode ser zero ou BLANK, caso em que a documentação recomenda DIVIDE?",
}

INSTRUCOES = [
    "Gabarito das regras em P1–P7 — protocolo de anotação",
    "",
    "1. Julgue cada linha pela pergunta no topo da aba e pela página do Learn indicada, não por preferência pessoal.",
    "2. veredito: 'viola', 'não viola' ou 'indeterminado' (use a lista suspensa).",
    "3. 'indeterminado' só quando o modelo não traz a informação necessária (ex.: a distribuição dos valores de uma coluna).",
    "4. Justificativa obrigatória em 'viola' e 'indeterminado'.",
    "5. Referência: a URL de qualquer fonte usada além da página indicada no topo da aba.",
    "6. A planilha não mostra o que a ferramenta decidiu, de propósito: o julgamento é cego.",
    "7. Para conferir o andamento: python -m gabarito importar --parcial",
]


def _aba_de_regra(livro: Workbook, id_regra: str, candidatos: list[Candidato]) -> None:
    aba = livro.create_sheet(id_regra)
    aba["A1"] = PERGUNTAS[id_regra]
    aba["A1"].font = Font(bold=True)
    aba["A2"] = REGISTRO.meta(id_regra).url_canonica
    cabecalho = ["id", "projeto", "objeto", *COLUNAS_DE_FATOS[id_regra], *COLUNAS_EDITAVEIS]
    for coluna, nome in enumerate(cabecalho, start=1):
        celula = aba.cell(row=LINHA_CABECALHO, column=coluna, value=nome)
        celula.font = Font(bold=True)

    primeira_editavel = len(cabecalho) - len(COLUNAS_EDITAVEIS) + 1
    linhas = sorted(candidatos, key=lambda c: (c.projeto, c.objeto))
    for i, c in enumerate(linhas, start=LINHA_CABECALHO + 1):
        valores = [c.id, c.projeto, c.objeto, *(c.fatos[f] for f in COLUNAS_DE_FATOS[id_regra])]
        for coluna, valor in enumerate(valores, start=1):
            aba.cell(row=i, column=coluna, value=valor).alignment = Alignment(wrap_text=True, vertical="top")
        for coluna in range(primeira_editavel, len(cabecalho) + 1):
            aba.cell(row=i, column=coluna).protection = Protection(locked=False)

    if linhas:
        letra = aba.cell(row=LINHA_CABECALHO, column=primeira_editavel).column_letter
        validacao = DataValidation(type="list", formula1=f'"{",".join(VEREDITOS)}"', allow_blank=True)
        validacao.add(f"{letra}{LINHA_CABECALHO + 1}:{letra}{LINHA_CABECALHO + len(linhas)}")
        aba.add_data_validation(validacao)
    aba.freeze_panes = aba.cell(row=LINHA_CABECALHO + 1, column=4)
    aba.protection.sheet = True


def gerar_planilha(candidatos: list[Candidato], destino: Path) -> None:
    if destino.exists():
        raise ErroDeGabarito(f"{destino} já existe e pode ter vereditos — apague ou renomeie antes de gerar outra")
    livro = Workbook()
    instrucoes = livro.active
    instrucoes.title = "Instruções"
    for i, linha in enumerate(INSTRUCOES, start=1):
        instrucoes.cell(row=i, column=1, value=linha)
    for id_regra in sorted(COLUNAS_DE_FATOS):
        _aba_de_regra(livro, id_regra, [c for c in candidatos if c.id_regra == id_regra])
    destino.parent.mkdir(parents=True, exist_ok=True)
    livro.save(destino)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_planilha.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add gabarito/planilha.py tests/test_gabarito_planilha.py
git commit -m "feat(gabarito): planilha cega com lista suspensa e protecao"
```

---

### Task 4: Ler a planilha, validar e gravar o CSV

**Files:**
- Modify: `gabarito/planilha.py`
- Test: `tests/test_gabarito_planilha.py` (acrescentar)

**Interfaces:**
- Consumes: `gerar_planilha`, `VEREDITOS`, `LINHA_CABECALHO`, `COLUNAS_EDITAVEIS` (Task 3); `Candidato`, `ErroDeGabarito`.
- Produces: `LinhaGabarito(id, projeto, id_regra, objeto, veredito, justificativa, referencia)` (Pydantic); `Problema(aba: str, linha: int, id: str, motivo: str)`; `ler_planilha(caminho: Path) -> list[tuple[str, int, LinhaGabarito]]` (aba, nº da linha, linha); `validar(lidas, candidatos: list[Candidato], parcial: bool) -> list[Problema]`; `progresso(lidas) -> dict[str, tuple[int, int]]` (regra → julgadas, total); `gravar_csv(linhas: list[LinhaGabarito], destino: Path) -> None`; `ler_csv(caminho: Path) -> list[LinhaGabarito]`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_gabarito_planilha.py`:

```python
from openpyxl import load_workbook as _abrir

from gabarito.planilha import gravar_csv, ler_csv, ler_planilha, progresso, validar


def _preencher(destino, vereditos):
    """vereditos: {id: (veredito, justificativa)} — escreve como o Fred faria."""
    livro = _abrir(destino)
    for aba in livro.worksheets[1:]:
        cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
        col_v = cabecalho.index("veredito") + 1
        for r in range(LINHA_CABECALHO + 1, aba.max_row + 1):
            id_ = aba.cell(row=r, column=1).value
            if id_ in vereditos:
                veredito, justificativa = vereditos[id_]
                aba.cell(row=r, column=col_v, value=veredito)
                aba.cell(row=r, column=col_v + 1, value=justificativa)
    livro.save(destino)


ID_REL = "MOD-002|P1|Vendas[Produto] → Produto[Produto]"
ID_COL = "PERF-001|P3|Pessoa[Salário]"


def _planilha(tmp_path, vereditos):
    destino = tmp_path / "a.xlsx"
    gerar_planilha(_candidatos(), destino)
    _preencher(destino, vereditos)
    return destino


def test_planilha_completa_valida_sem_problemas(tmp_path):
    destino = _planilha(tmp_path, {ID_REL: ("viola", "bidirecional sem motivo"), ID_COL: ("não viola", None)})
    lidas = ler_planilha(destino)
    assert validar(lidas, _candidatos(), parcial=False) == []
    assert {l.id: l.veredito for _, _, l in lidas} == {ID_REL: "viola", ID_COL: "não viola"}


def test_veredito_ausente_e_problema(tmp_path):
    destino = _planilha(tmp_path, {ID_REL: ("viola", "x")})
    problemas = validar(ler_planilha(destino), _candidatos(), parcial=False)
    assert [(p.id, p.motivo) for p in problemas] == [(ID_COL, "sem veredito")]


@pytest.mark.parametrize("valor", ["Viola", " não viola ", "nao viola", "talvez"])
def test_veredito_fora_da_lista_e_problema_sem_normalizar(tmp_path, valor):
    destino = _planilha(tmp_path, {ID_REL: (valor, "x"), ID_COL: ("não viola", None)})
    problemas = validar(ler_planilha(destino), _candidatos(), parcial=False)
    assert [(p.aba, p.id) for p in problemas] == [("MOD-002", ID_REL)]
    assert "fora da lista" in problemas[0].motivo


@pytest.mark.parametrize("veredito", ["viola", "indeterminado"])
def test_viola_e_indeterminado_exigem_justificativa(tmp_path, veredito):
    destino = _planilha(tmp_path, {ID_REL: (veredito, "  "), ID_COL: ("não viola", None)})
    problemas = validar(ler_planilha(destino), _candidatos(), parcial=False)
    assert [(p.id, p.motivo) for p in problemas] == [(ID_REL, "sem justificativa")]


def test_id_faltando_e_sobrando_sao_problemas(tmp_path):
    destino = _planilha(tmp_path, {ID_REL: ("viola", "x"), ID_COL: ("não viola", None)})
    atuais = [_candidatos()[0], Candidato(id_regra="PERF-001", projeto="P3", objeto="Pessoa[Novo]", fatos={"expressao": "1"})]
    motivos = {(p.id, p.motivo) for p in validar(ler_planilha(destino), atuais, parcial=False)}
    assert motivos == {(ID_COL, "não é mais candidato"), ("PERF-001|P3|Pessoa[Novo]", "candidato ausente da planilha")}


def test_parcial_aceita_em_branco_e_informa_progresso(tmp_path):
    destino = _planilha(tmp_path, {ID_REL: ("viola", "x")})
    lidas = ler_planilha(destino)
    assert validar(lidas, _candidatos(), parcial=True) == []
    assert progresso(lidas)["MOD-002"] == (1, 1)
    assert progresso(lidas)["PERF-001"] == (0, 1)


def test_csv_ida_e_volta(tmp_path):
    destino = _planilha(tmp_path, {ID_REL: ("viola", "bidirecional, sem motivo"), ID_COL: ("não viola", None)})
    linhas = [l for _, _, l in ler_planilha(destino)]
    csv = tmp_path / "ground_truth.csv"
    gravar_csv(linhas, csv)
    assert csv.read_text(encoding="utf-8").splitlines()[0] == "id,projeto,id_regra,objeto,veredito,justificativa,referencia"
    assert ler_csv(csv) == sorted(linhas, key=lambda l: l.id)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_planilha.py -q`
Expected: FAIL — `ImportError: cannot import name 'gravar_csv'`

- [ ] **Step 3: Implementar**

Em `gabarito/planilha.py`, acrescentar `import csv` e `from openpyxl import load_workbook` e `from pydantic import BaseModel` aos imports, e ao fim do arquivo:

```python
CAMPOS_CSV = ("id", "projeto", "id_regra", "objeto", "veredito", "justificativa", "referencia")


class LinhaGabarito(BaseModel):
    id: str
    projeto: str
    id_regra: str
    objeto: str
    veredito: str | None = None
    justificativa: str | None = None
    referencia: str | None = None


class Problema(BaseModel):
    aba: str
    linha: int
    id: str
    motivo: str


def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor)
    return texto if texto.strip() else None


def ler_planilha(caminho: Path) -> list[tuple[str, int, LinhaGabarito]]:
    livro = load_workbook(caminho, read_only=True)
    lidas: list[tuple[str, int, LinhaGabarito]] = []
    for aba in livro.worksheets[1:]:
        linhas = list(aba.iter_rows(min_row=LINHA_CABECALHO, values_only=True))
        if not linhas:
            continue
        cabecalho = list(linhas[0])
        posicao = {nome: cabecalho.index(nome) for nome in ("id", "projeto", "objeto", *COLUNAS_EDITAVEIS)}
        for numero, valores in enumerate(linhas[1:], start=LINHA_CABECALHO + 1):
            if valores[posicao["id"]] is None:
                continue
            lidas.append(
                (
                    aba.title,
                    numero,
                    LinhaGabarito(
                        id=str(valores[posicao["id"]]),
                        projeto=str(valores[posicao["projeto"]]),
                        id_regra=aba.title,
                        objeto=str(valores[posicao["objeto"]]),
                        veredito=_texto(valores[posicao["veredito"]]),
                        justificativa=_texto(valores[posicao["justificativa"]]),
                        referencia=_texto(valores[posicao["referencia"]]),
                    ),
                )
            )
    livro.close()
    return lidas


def validar(lidas: list[tuple[str, int, LinhaGabarito]], candidatos: list[Candidato], parcial: bool) -> list[Problema]:
    """Não normaliza: um veredito fora da lista é apontado, não corrigido em silêncio."""
    problemas: list[Problema] = []
    for aba, numero, linha in lidas:
        if linha.veredito is None:
            if not parcial:
                problemas.append(Problema(aba=aba, linha=numero, id=linha.id, motivo="sem veredito"))
            continue
        if linha.veredito not in VEREDITOS:
            problemas.append(
                Problema(aba=aba, linha=numero, id=linha.id, motivo=f"veredito fora da lista: {linha.veredito!r}")
            )
        elif linha.veredito != "não viola" and linha.justificativa is None:
            problemas.append(Problema(aba=aba, linha=numero, id=linha.id, motivo="sem justificativa"))

    na_planilha = {linha.id: (aba, numero) for aba, numero, linha in lidas}
    atuais = {c.id: c for c in candidatos}
    for id_, (aba, numero) in na_planilha.items():
        if id_ not in atuais:
            problemas.append(Problema(aba=aba, linha=numero, id=id_, motivo="não é mais candidato"))
    for id_, c in atuais.items():
        if id_ not in na_planilha:
            problemas.append(Problema(aba=c.id_regra, linha=0, id=id_, motivo="candidato ausente da planilha"))
    return problemas


def progresso(lidas: list[tuple[str, int, LinhaGabarito]]) -> dict[str, tuple[int, int]]:
    contagem: dict[str, tuple[int, int]] = {}
    for aba, _, linha in lidas:
        julgadas, total = contagem.get(aba, (0, 0))
        contagem[aba] = (julgadas + (linha.veredito is not None), total + 1)
    return contagem


def gravar_csv(linhas: list[LinhaGabarito], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV, lineterminator="
")
        escritor.writeheader()
        for linha in sorted(linhas, key=lambda l: l.id):
            escritor.writerow({campo: getattr(linha, campo) or "" for campo in CAMPOS_CSV})


def ler_csv(caminho: Path) -> list[LinhaGabarito]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            LinhaGabarito(**{campo: (valor or None) for campo, valor in linha.items()})
            for linha in csv.DictReader(arquivo)
        ]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_planilha.py -q`
Expected: 18 passed (7 da Tarefa 3 + 11 novos, contando os parametrizados).

- [ ] **Step 5: Commit**

```bash
git add gabarito/planilha.py tests/test_gabarito_planilha.py
git commit -m "feat(gabarito): leitura, validacao e CSV do gabarito"
```

---

### Task 5: Métricas

**Files:**
- Create: `gabarito/metricas.py`
- Test: `tests/test_gabarito_metricas.py`

**Interfaces:**
- Consumes: `LinhaGabarito` (Task 4); `Achado`; `ErroDeGabarito`; `REGISTRO` para a categoria de cada regra.
- Produces: `Matriz(vp, fp, fn, vn, ind_marcados, ind_nao_marcados)` com `+`; `taxas(m: Matriz) -> dict[str, dict[str, float | None]]` (`{"precisao": {"principal","piso","teto"}, "recall": {...}}`); `ResultadoMedicao` (Pydantic: `por_regra`, `por_categoria`, `por_projeto`, `total_micro`, `macro`, `r03`, `r12`, `divergencias`); `medir(gabarito: list[LinhaGabarito], achados: dict[str, list[Achado]]) -> ResultadoMedicao`; `LIMITE_R03 = 0.7`; `GATILHO_R12 = 40`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_gabarito_metricas.py`:

```python
"""Métricas do gabarito: contas feitas à mão."""

import pytest

from core.rules.base import Achado, Evidencia
from gabarito.candidatos import ErroDeGabarito
from gabarito.metricas import Matriz, medir, taxas
from gabarito.planilha import LinhaGabarito


def _linha(id_regra, projeto, objeto, veredito):
    return LinhaGabarito(id=f"{id_regra}|{projeto}|{objeto}", projeto=projeto, id_regra=id_regra, objeto=objeto,
                         veredito=veredito, justificativa="j" if veredito != "não viola" else None)


def _achado(id_regra, objeto):
    return Achado(id_regra=id_regra, evidencia=Evidencia(tipo_objeto="tabela", objeto=objeto), mensagem="m")


def test_taxas_principal_piso_e_teto():
    m = Matriz(vp=6, fp=2, fn=1, vn=10, ind_marcados=2, ind_nao_marcados=1)
    t = taxas(m)
    assert t["precisao"] == {"principal": 6 / 8, "piso": 6 / 10, "teto": 8 / 10}
    assert t["recall"] == {"principal": 6 / 7, "piso": 6 / 8, "teto": 8 / 9}


def test_sem_divisor_e_none_nunca_zero_nem_um():
    t = taxas(Matriz())
    assert t["precisao"] == {"principal": None, "piso": None, "teto": None}
    assert t["recall"] == {"principal": None, "piso": None, "teto": None}


def _cenario():
    gabarito = [
        _linha("MOD-003", "P1", "A", "viola"),          # marcado → VP
        _linha("MOD-003", "P1", "B", "não viola"),      # marcado → FP
        _linha("MOD-003", "P2", "C", "viola"),          # não marcado → FN
        _linha("MOD-003", "P2", "D", "não viola"),      # não marcado → VN
        _linha("PERF-003", "P1", "T[x]", "indeterminado"),  # marcado → ind
        _linha("PERF-003", "P1", "T[y]", "viola"),      # marcado → VP
        _linha("MOD-001", "P1", "Z", "não viola"),      # não marcado → VN
    ]
    achados = {
        "P1": [_achado("MOD-003", "A"), _achado("MOD-003", "B"), _achado("PERF-003", "T[x]"), _achado("PERF-003", "T[y]")],
        "P2": [],
    }
    return gabarito, achados


def test_matriz_por_regra():
    r = medir(*_cenario())
    assert r.por_regra["MOD-003"].matriz == Matriz(vp=1, fp=1, fn=1, vn=1)
    assert r.por_regra["PERF-003"].matriz == Matriz(vp=1, ind_marcados=1)


def test_regra_sem_achado_nem_violacao_fica_none():
    r = medir(*_cenario())
    mod001 = r.por_regra["MOD-001"]
    assert mod001.taxas["precisao"]["principal"] is None
    assert mod001.taxas["recall"]["principal"] is None


def test_micro_soma_e_macro_ignora_none():
    r = medir(*_cenario())
    assert r.total_micro.matriz == Matriz(vp=2, fp=1, fn=1, vn=2, ind_marcados=1)
    assert r.macro["precisao"] == pytest.approx((0.5 + 1.0) / 2)


def test_por_categoria():
    r = medir(*_cenario())
    assert r.por_categoria["modelagem"].matriz == Matriz(vp=1, fp=1, fn=1, vn=2)
    assert r.por_categoria["performance"].matriz == Matriz(vp=1, ind_marcados=1)


def test_gatilhos_r03_e_r12():
    r = medir(*_cenario())
    assert r.r03 == ["MOD-003"]
    assert r.r12 == {"vp": 2, "vp_sem_perf003": 1, "gatilho": 40}


def test_divergencias_listam_fp_e_fn_com_justificativa():
    r = medir(*_cenario())
    assert [(d.tipo, d.id) for d in r.divergencias] == [("FP", "MOD-003|P1|B"), ("FN", "MOD-003|P2|C")]


def test_achado_sem_linha_no_gabarito_aborta():
    gabarito, achados = _cenario()
    achados["P2"].append(_achado("MOD-003", "Sumida"))
    with pytest.raises(ErroDeGabarito, match="MOD-003\\|P2\\|Sumida"):
        medir(gabarito, achados)


def test_gabarito_com_veredito_vazio_aborta():
    gabarito, achados = _cenario()
    gabarito[0] = _linha("MOD-003", "P1", "A", None)
    with pytest.raises(ErroDeGabarito, match="sem veredito"):
        medir(gabarito, achados)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_metricas.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'gabarito.metricas'`

- [ ] **Step 3: Implementar**

`gabarito/metricas.py`:

```python
"""Precisão e recall por regra, cruzando o gabarito com os achados.

`indeterminado` não é forçado para lado nenhum: cada regra sai com a versão
principal (sem os indeterminados), o piso (contra a regra) e o teto (a favor) —
o mesmo raciocínio que recusou a PERF-005. Sem divisor, a taxa é `None`: uma
regra sem achado não tem precisão 1, nem 0.
"""

from statistics import mean

from pydantic import BaseModel

import core.rules.todas  # noqa: F401 — registra as regras
from core.rules.base import Achado
from core.rules.registry import REGISTRO
from gabarito.candidatos import ErroDeGabarito
from gabarito.planilha import LinhaGabarito

LIMITE_R03 = 0.7
GATILHO_R12 = 40


class Matriz(BaseModel):
    vp: int = 0
    fp: int = 0
    fn: int = 0
    vn: int = 0
    ind_marcados: int = 0
    ind_nao_marcados: int = 0

    def __add__(self, outra: "Matriz") -> "Matriz":
        return Matriz(**{campo: getattr(self, campo) + getattr(outra, campo) for campo in Matriz.model_fields})


def _razao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def taxas(m: Matriz) -> dict[str, dict[str, float | None]]:
    return {
        "precisao": {
            "principal": _razao(m.vp, m.vp + m.fp),
            "piso": _razao(m.vp, m.vp + m.fp + m.ind_marcados),
            "teto": _razao(m.vp + m.ind_marcados, m.vp + m.fp + m.ind_marcados),
        },
        "recall": {
            "principal": _razao(m.vp, m.vp + m.fn),
            "piso": _razao(m.vp, m.vp + m.fn + m.ind_nao_marcados),
            "teto": _razao(m.vp + m.ind_marcados, m.vp + m.ind_marcados + m.fn),
        },
    }


class Medida(BaseModel):
    matriz: Matriz
    taxas: dict[str, dict[str, float | None]]


def _medida(m: Matriz) -> Medida:
    return Medida(matriz=m, taxas=taxas(m))


class Divergencia(BaseModel):
    tipo: str
    id: str
    justificativa: str | None


class ResultadoMedicao(BaseModel):
    por_regra: dict[str, Medida]
    por_categoria: dict[str, Medida]
    por_projeto: dict[str, Medida]
    total_micro: Medida
    macro: dict[str, float | None]
    r03: list[str]
    r12: dict[str, int]
    divergencias: list[Divergencia]


def medir(gabarito: list[LinhaGabarito], achados: dict[str, list[Achado]]) -> ResultadoMedicao:
    sem_veredito = [l.id for l in gabarito if l.veredito is None]
    if sem_veredito:
        raise ErroDeGabarito(f"{len(sem_veredito)} linha(s) do gabarito sem veredito, ex.: {sem_veredito[0]}")
    marcados = {f"{a.id_regra}|{projeto}|{a.evidencia.objeto}" for projeto, lista in achados.items() for a in lista}
    ids = {l.id for l in gabarito}
    sem_candidato = sorted(marcados - ids)
    if sem_candidato:
        raise ErroDeGabarito(f"achado(s) sem linha no gabarito — furo no gerador de candidatos: {', '.join(sem_candidato)}")

    por_regra: dict[str, Matriz] = {}
    por_projeto: dict[str, Matriz] = {}
    divergencias: list[Divergencia] = []
    for l in sorted(gabarito, key=lambda x: x.id):
        marcado = l.id in marcados
        if l.veredito == "indeterminado":
            parcela = Matriz(ind_marcados=1) if marcado else Matriz(ind_nao_marcados=1)
        elif l.veredito == "viola":
            parcela = Matriz(vp=1) if marcado else Matriz(fn=1)
        else:
            parcela = Matriz(fp=1) if marcado else Matriz(vn=1)
        if parcela.fp or parcela.fn:
            divergencias.append(Divergencia(tipo="FP" if parcela.fp else "FN", id=l.id, justificativa=l.justificativa))
        por_regra[l.id_regra] = por_regra.get(l.id_regra, Matriz()) + parcela
        por_projeto[l.projeto] = por_projeto.get(l.projeto, Matriz()) + parcela

    por_categoria: dict[str, Matriz] = {}
    for id_regra, m in por_regra.items():
        categoria = REGISTRO.meta(id_regra).categoria
        por_categoria[categoria] = por_categoria.get(categoria, Matriz()) + m

    medidas = {id_regra: _medida(m) for id_regra, m in sorted(por_regra.items())}
    total = sum(por_regra.values(), Matriz())

    def _macro(qual: str) -> float | None:
        valores = [m.taxas[qual]["principal"] for m in medidas.values() if m.taxas[qual]["principal"] is not None]
        return mean(valores) if valores else None

    return ResultadoMedicao(
        por_regra=medidas,
        por_categoria={c: _medida(m) for c, m in sorted(por_categoria.items())},
        por_projeto={p: _medida(m) for p, m in sorted(por_projeto.items())},
        total_micro=_medida(total),
        macro={"precisao": _macro("precisao"), "recall": _macro("recall")},
        r03=[
            id_regra
            for id_regra, m in medidas.items()
            if m.taxas["precisao"]["principal"] is not None and m.taxas["precisao"]["principal"] < LIMITE_R03
        ],
        r12={
            "vp": total.vp,
            "vp_sem_perf003": total.vp - por_regra.get("PERF-003", Matriz()).vp,
            "gatilho": GATILHO_R12,
        },
        divergencias=divergencias,
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_metricas.py -q`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add gabarito/metricas.py tests/test_gabarito_metricas.py
git commit -m "feat(gabarito): precisao e recall por regra com piso, teto e gatilhos"
```

---

### Task 6: Comando `python -m gabarito`

**Files:**
- Create: `gabarito/__main__.py`
- Modify: `.gitignore` (acrescentar `eval/gabarito/`)
- Test: `tests/test_gabarito_comando.py`

**Interfaces:**
- Consumes: `candidatos_do_dataset`, `ErroDeGabarito` (Tasks 1–2); `gerar_planilha`, `ler_planilha`, `validar`, `progresso`, `gravar_csv`, `ler_csv` (Tasks 3–4); `medir`, `ResultadoMedicao` (Task 5); `achados_dos_projetos`, `PASTA_PBIP`, `RAIZ_REPO`, `ErroDeAvaliacao` (`rag.avaliacao`).
- Produces: `main(argv: list[str] | None = None) -> int`; constantes de módulo `ARQUIVO_PLANILHA`, `ARQUIVO_CSV`, `PASTA_RESULTADOS`; `formatar(resultado: ResultadoMedicao) -> str`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_gabarito_comando.py`:

```python
"""O comando python -m gabarito: gerar, importar e medir, com dados falsos."""

import json

import pytest

from core.rules.base import Achado, Evidencia
from gabarito import __main__ as comando
from gabarito.candidatos import Candidato
from gabarito.planilha import LINHA_CABECALHO

CANDIDATOS = [
    Candidato(id_regra="MOD-003", projeto="P1", objeto="A", fatos={"relacionamentos": "0", "medidas": "0", "colunas": "3", "oculta": "não"}),
    Candidato(id_regra="MOD-003", projeto="P1", objeto="B", fatos={"relacionamentos": "2", "medidas": "0", "colunas": "3", "oculta": "não"}),
]


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setattr(comando, "ARQUIVO_PLANILHA", tmp_path / "gabarito" / "anotacao.xlsx")
    monkeypatch.setattr(comando, "ARQUIVO_CSV", tmp_path / "ground_truth.csv")
    monkeypatch.setattr(comando, "PASTA_RESULTADOS", tmp_path / "results")
    monkeypatch.setattr(comando, "candidatos_do_dataset", lambda: CANDIDATOS)
    achado = Achado(id_regra="MOD-003", evidencia=Evidencia(tipo_objeto="tabela", objeto="A"), mensagem="m")
    monkeypatch.setattr(comando, "achados_dos_projetos", lambda pasta: {"P1": [achado]})
    return tmp_path


def _preencher_tudo(caminho, veredito="viola"):
    from openpyxl import load_workbook

    livro = load_workbook(caminho)
    aba = livro["MOD-003"]
    cabecalho = [c.value for c in aba[LINHA_CABECALHO]]
    col_v = cabecalho.index("veredito") + 1
    for r in range(LINHA_CABECALHO + 1, aba.max_row + 1):
        aba.cell(row=r, column=col_v, value=veredito)
        aba.cell(row=r, column=col_v + 1, value="justificativa")
    livro.save(caminho)


def test_gerar_cria_a_planilha_e_recusa_a_segunda_vez(ambiente, capsys):
    assert comando.main(["gerar"]) == 0
    assert (ambiente / "gabarito" / "anotacao.xlsx").is_file()
    assert comando.main(["gerar"]) == 1
    assert "existe e pode ter vereditos" in capsys.readouterr().err


def test_importar_incompleto_lista_problemas_e_nao_grava(ambiente, capsys):
    comando.main(["gerar"])
    assert comando.main(["importar"]) == 1
    assert "sem veredito" in capsys.readouterr().err
    assert not (ambiente / "ground_truth.csv").exists()


def test_importar_parcial_mostra_progresso(ambiente, capsys):
    comando.main(["gerar"])
    assert comando.main(["importar", "--parcial"]) == 0
    assert "MOD-003: 0/2" in capsys.readouterr().out


def test_importar_completo_grava_o_csv(ambiente):
    comando.main(["gerar"])
    _preencher_tudo(ambiente / "gabarito" / "anotacao.xlsx")
    assert comando.main(["importar"]) == 0
    assert (ambiente / "ground_truth.csv").read_text(encoding="utf-8").count("\n") == 3


def test_planilha_aberta_no_excel_vira_mensagem(ambiente, monkeypatch, capsys):
    comando.main(["gerar"])

    def bloqueada(caminho):
        raise PermissionError("arquivo em uso")

    monkeypatch.setattr(comando, "ler_planilha", bloqueada)
    assert comando.main(["importar"]) == 1
    assert "erro:" in capsys.readouterr().err


def test_medir_grava_json_e_imprime_em_ascii(ambiente, capsys):
    comando.main(["gerar"])
    _preencher_tudo(ambiente / "gabarito" / "anotacao.xlsx")
    comando.main(["importar"])
    assert comando.main(["medir"]) == 0
    resultados = list((ambiente / "results").glob("regras-*.json"))
    assert len(resultados) == 1
    dados = json.loads(resultados[0].read_text(encoding="utf-8"))
    assert dados["por_regra"]["MOD-003"]["matriz"]["vp"] == 1
    saida = capsys.readouterr().out
    saida.encode("ascii")
    assert "MOD-003" in saida and "R-12" in saida


def test_medir_sem_csv_sai_com_erro(ambiente, capsys):
    assert comando.main(["medir"]) == 1
    assert "importar" in capsys.readouterr().err
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_comando.py -q`
Expected: FAIL — `ImportError: cannot import name '__main__' from 'gabarito'`

- [ ] **Step 3: Implementar**

`gabarito/__main__.py`:

```python
"""python -m gabarito gerar | importar [--parcial] | medir

Desenho: `docs/superpowers/specs/2026-10-11-gabarito-das-regras-design.md`.
"""

import argparse
import sys
from datetime import date

from gabarito.candidatos import ErroDeGabarito, candidatos_do_dataset
from gabarito.metricas import ResultadoMedicao, medir
from gabarito.planilha import gerar_planilha, gravar_csv, ler_csv, ler_planilha, progresso, validar
from rag.avaliacao import PASTA_PBIP, RAIZ_REPO, ErroDeAvaliacao, achados_dos_projetos

ARQUIVO_PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "anotacao-P1-P7.xlsx"
ARQUIVO_CSV = RAIZ_REPO / "eval" / "ground_truth.csv"
PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def _pct(valor: float | None) -> str:
    return "-" if valor is None else f"{valor:.2f}"


def formatar(r: ResultadoMedicao) -> str:
    linhas = ["regra      VP  FP  FN  VN  ind   precisao (piso-teto)   recall (piso-teto)"]
    for id_regra, m in r.por_regra.items():
        x, p, c = m.matriz, m.taxas["precisao"], m.taxas["recall"]
        linhas.append(
            f"{id_regra:<9} {x.vp:>3} {x.fp:>3} {x.fn:>3} {x.vn:>3} {x.ind_marcados + x.ind_nao_marcados:>4}   "
            f"{_pct(p['principal'])} ({_pct(p['piso'])}-{_pct(p['teto'])})        "
            f"{_pct(c['principal'])} ({_pct(c['piso'])}-{_pct(c['teto'])})"
        )
    for categoria, m in r.por_categoria.items():
        linhas.append(
            f"categoria {categoria}: precisao {_pct(m.taxas['precisao']['principal'])}, "
            f"recall {_pct(m.taxas['recall']['principal'])}"
        )
    total = r.total_micro.taxas
    linhas.append(
        f"total micro: precisao {_pct(total['precisao']['principal'])}, recall {_pct(total['recall']['principal'])} | "
        f"macro: precisao {_pct(r.macro['precisao'])}, recall {_pct(r.macro['recall'])}"
    )
    linhas.append(f"R-03 (precisao < 0,7): {', '.join(r.r03) or 'nenhuma regra'}")
    linhas.append(
        f"R-12: {r.r12['vp']} achados confirmados (sem PERF-003: {r.r12['vp_sem_perf003']}) contra o gatilho de {r.r12['gatilho']}"
    )
    linhas.append(f"Divergencias para releitura: {len(r.divergencias)}")
    return _ascii("\n".join(linhas))


def _gerar() -> int:
    gerar_planilha(candidatos_do_dataset(), ARQUIVO_PLANILHA)
    print(_ascii(f"Planilha gerada em {ARQUIVO_PLANILHA}"))
    return 0


def _importar(parcial: bool) -> int:
    lidas = ler_planilha(ARQUIVO_PLANILHA)
    problemas = validar(lidas, candidatos_do_dataset(), parcial=parcial)
    if problemas:
        for p in problemas:
            print(_ascii(f"erro: {p.aba} linha {p.linha} | {p.id} | {p.motivo}"), file=sys.stderr)
        print(f"erro: {len(problemas)} problema(s); nada foi gravado", file=sys.stderr)
        return 1
    if parcial:
        for regra, (julgadas, total) in sorted(progresso(lidas).items()):
            print(f"{regra}: {julgadas}/{total}")
        return 0
    gravar_csv([l for _, _, l in lidas], ARQUIVO_CSV)
    print(_ascii(f"Gabarito gravado em {ARQUIVO_CSV} ({len(lidas)} linhas)"))
    return 0


def _medir() -> int:
    if not ARQUIVO_CSV.is_file():
        print(f"erro: {ARQUIVO_CSV.name} ausente - rode `python -m gabarito importar`", file=sys.stderr)
        return 1
    resultado = medir(ler_csv(ARQUIVO_CSV), achados_dos_projetos(PASTA_PBIP))
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"regras-{date.today().isoformat()}.json"
    destino.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(formatar(resultado))
    print(_ascii(f"Resultado em {destino}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m gabarito", description="Gabarito das regras em P1-P7.")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("gerar", help="gera a planilha de anotacao cega")
    importar = sub.add_parser("importar", help="valida a planilha e grava eval/ground_truth.csv")
    importar.add_argument("--parcial", action="store_true", help="so mostra o progresso, aceita linhas em branco")
    sub.add_parser("medir", help="precisao e recall por regra")
    args = parser.parse_args(argv)
    try:
        if args.comando == "gerar":
            return _gerar()
        if args.comando == "importar":
            return _importar(args.parcial)
        return _medir()
    except (ErroDeGabarito, ErroDeAvaliacao, OSError) as erro:
        # OSError cobre a planilha aberta no Excel (PermissionError) e arquivo ausente.
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Em `.gitignore`, na seção "Dados de projetos PBIP reais e artefatos gerados", acrescentar a linha `eval/gabarito/`.

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_comando.py -q`
Expected: 7 passed. `_preencher_tudo` acha a coluna `veredito` pelo cabeçalho, como o `_preencher` da Task 4.

- [ ] **Step 5: Suíte inteira e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q` — Expected: tudo passa.

```bash
git add gabarito/__main__.py .gitignore tests/test_gabarito_comando.py
git commit -m "feat(gabarito): comando gerar, importar e medir"
```

---

### Task 7: Gerar a planilha real, conferir e registrar

**Files:**
- Modify: `docs/project/progress-log.md` (entrada nova ao fim)
- Modify: `docs/project/status.md` (linha da Fase 3)

- [ ] **Step 1: Gerar a planilha de P1–P7**

Run: `.\.venv\Scripts\python.exe -m gabarito gerar`
Expected: `Planilha gerada em ...\eval\gabarito\anotacao-P1-P7.xlsx`.

- [ ] **Step 2: Conferir as contagens por regra**

Run: `.\.venv\Scripts\python.exe -m gabarito importar --parcial`
Expected: uma linha por regra, todas com `0/<total>`. Anotar os totais; a spec estimou ~400–450 linhas no total. Abrir a planilha no Excel e conferir à mão: lista suspensa na coluna `veredito`, células de fatos bloqueadas, pergunta e link no topo de cada aba.

- [ ] **Step 3: Registrar no progress-log e no status**

Acrescentar ao fim de `docs/project/progress-log.md` uma entrada `## <data> — Gabarito das regras: ferramentas prontas, planilha gerada` com: o que foi construído (pacote `gabarito/`, julgamento cego, piso e teto do `indeterminado`); os totais de candidatos por regra do Step 2; a ressalva do parser comum; e `**Próximo passo:**` "o Fred preenche `eval/gabarito/anotacao-P1-P7.xlsx`; depois `python -m gabarito importar` e `medir`". Atualizar a linha da Fase 3 em `docs/project/status.md` com "gabarito das regras: planilha gerada, anotação em andamento".

- [ ] **Step 4: Commit e push**

```bash
git add docs/project/progress-log.md docs/project/status.md
git commit -m "docs: gabarito das regras - planilha gerada para anotacao"
git push
```
