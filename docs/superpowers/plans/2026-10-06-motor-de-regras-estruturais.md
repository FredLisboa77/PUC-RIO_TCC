# Motor de Regras Estruturais — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o motor de regras determinísticas (contrato, registro, escopo, runner, catálogo) e as 8 regras estruturais, produzindo exatamente 15 achados no PBIP real P8.

**Architecture:** Cada regra é uma função pura `(ModeloSemantico) -> Iterable[Achado]`, registrada por decorador num catálogo que guarda os metadados — inclusive a URL canónica do Microsoft Learn que sustenta o achado. O runner itera o registro em ordem de ID, isola exceção por regra e devolve achados ordenados deterministicamente. As exclusões de escopo ("auditar o que o autor escreveu") vivem num módulo só delas, nunca dentro de uma regra.

**Tech Stack:** Python 3.11.9 · Pydantic 2.13.5 · pytest 9.1.1. Sem novas dependências.

**Spec:** [`docs/superpowers/specs/2026-10-06-motor-de-regras-estruturais-design.md`](../specs/2026-10-06-motor-de-regras-estruturais-design.md)

## Global Constraints

- **Python 3.11.9**, no `.venv/` da raiz. Ativar com `.\.venv\Scripts\Activate.ps1` (PowerShell) antes de qualquer comando.
- **Sem novas dependências.** `requirements.txt` fica em `pydantic==2.13.5` e `pytest==9.1.1`.
- **Nomes de código em português**, como o resto de `core/`. Docstrings em português, explicando o *porquê* — o estilo de `core/parser_bim.py` é a referência.
- **Nenhum `__init__.py`.** `core/` e `core/rules/` são pacotes de namespace; `pytest.ini` já tem `pythonpath = .`.
- **Mensagens de commit em ASCII sem acentos**, como todo o histórico do repositório (`git log --oneline`).
- **TDD obrigatório:** o teste é escrito primeiro, executado para ver falhar, e só então vem a implementação mínima.
- **Nenhum achado pode afirmar mais do que a fonte citada.** Toda `recomendacao_padrao` carrega as exceções que a própria página do Learn declara (spec, seção 4).
- **Os 15 testes existentes continuam passando** em todas as tarefas.
- **Severidade e demais metadados moram só no catálogo.** `Achado` tem três campos: `id_regra`, `evidencia`, `mensagem`.

## Review Focus

Cinco classes de entrada que a spec implica e que quebrariam a auditoria em silêncio. Cada uma tem seu teste na tarefa que possui o código.

1. **Relacionamento com uma ponta fora do escopo.** Em P8, `DimPromotion[StartDate] → LocalDateTable_x[Date]` é `dateTime → dateTime` e a tabela automática não tem `dataCategory: "Time"` — se MOD-005 não filtrar por escopo, inventa 3 achados. Teste na Tarefa 7.
2. **`fromCardinality: "one"` explícito.** O P8 tem um um-para-um. Presumir `from` = "muitos" faz MOD-007 não achar nada e MOD-002 marcar um relacionamento cuja configuração é imposta pelo produto. Testes nas Tarefas 1 e 8.
3. **Relacionamento referenciando tabela ou coluna que não existe.** Modelo editado à mão ou PBIP salvo em estado intermediário: o lookup de tipo de coluna precisa devolver `None`, não levantar `KeyError`. Teste na Tarefa 4.
4. **`crossFilteringBehavior: "automatic"`.** Não é bidirecional explícito; MOD-002 não pode marcá-lo. Teste na Tarefa 6.
5. **`GENERATESERIES` com variação de caixa, espaço ou linha de comentário antes.** O predicado de parâmetro hipotético é o que impede um falso positivo de MOD-003; se ele for literal demais, o falso positivo volta sem aviso. Teste na Tarefa 4.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `core/model.py` (modificar) | Acrescenta as propriedades TMSL que as regras leem |
| `core/parser_bim.py` (modificar) | Mapeia essas propriedades; normaliza cardinalidade |
| `core/rules/base.py` (criar) | `RegraMeta`, `Evidencia`, `Achado`, `ORDEM_SEVERIDADE` |
| `core/rules/registry.py` (criar) | `Registro`, decorador `@regra`, `RegraDuplicada` |
| `core/rules/escopo.py` (criar) | Quem entra na auditoria: exclusões, lados do relacionamento, dimensão de data |
| `core/rules/modelagem.py` (criar) | MOD-001, MOD-002, MOD-003, MOD-005, MOD-006, MOD-007 |
| `core/rules/performance.py` (criar) | PERF-001, PERF-003 |
| `core/rules/runner.py` (criar) | `ResultadoRegras`, `avaliar()` |
| `core/rules/todas.py` (criar) | Importa os módulos de regra, populando o registro global |
| `core/rules/catalogo.py` (criar) | Catálogo em Markdown via `python -m core.rules.catalogo` |
| `tests/conftest.py` (modificar) | Construtores de `model.bim` sintético e fixture `ler` |
| `tests/test_rules_base.py` (criar) | Validação do contrato |
| `tests/test_rules_registry.py` (criar) | Registro e decorador |
| `tests/test_rules_escopo.py` (criar) | Exclusões e lados |
| `tests/test_rules_runner.py` (criar) | Ordenação e isolamento de erro |
| `tests/test_rules_modelagem.py` (criar) | As seis regras de modelagem |
| `tests/test_rules_performance.py` (criar) | As duas de performance |
| `tests/test_rules_catalogo.py` (criar) | Completude do catálogo e saída do CLI |
| `tests/test_pbip_real.py` (modificar) | Regressão: as 15 ocorrências do P8 |

---

### Task 1: Propriedades do TMSL que as regras precisam

**Files:**
- Modify: `core/model.py`
- Modify: `core/parser_bim.py`
- Test: `tests/test_parser_bim.py`

**Interfaces:**
- Consumes: nada (primeira tarefa).
- Produces: `Coluna.tipo: str | None`, `Coluna.resumir_por: str | None`, `Tabela.data_category: str | None`, `Particao.tipo_origem: str | None`, e `Relacionamento.cardinalidade_origem` / `cardinalidade_destino` normalizados para `"um"` / `"muitos"`.

- [ ] **Step 1: Write the failing test**

Acrescentar ao fim de `tests/test_parser_bim.py`:

O arquivo já tem o helper `modelo_com(tmp_path, model)` e os imports de `json` e `ler_modelo`. Use o helper — ele monta o PBIP e devolve o caminho do `model.bim`.

```python
def test_le_as_propriedades_que_as_regras_precisam(tmp_path):
    """`type`, `summarizeBy`, `dataCategory` e `source.type` viram campos próprios."""
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [
                {
                    "name": "DimCalendar",
                    "dataCategory": "Time",
                    "columns": [
                        {"name": "Data", "dataType": "dateTime", "summarizeBy": "none"},
                        {
                            "name": "Ano",
                            "dataType": "string",
                            "type": "calculated",
                            "summarizeBy": "none",
                            "expression": "YEAR([Data])",
                        },
                        {"name": "Valor", "dataType": "double", "summarizeBy": "sum"},
                    ],
                    "partitions": [
                        {
                            "name": "p",
                            "mode": "import",
                            "source": {"type": "calculated", "expression": "CALENDAR(1, 2)"},
                        }
                    ],
                }
            ],
            "relationships": [],
        },
    )

    modelo = ler_modelo(caminho)
    tabela = modelo.tabelas[0]
    data, ano, valor = tabela.colunas

    assert tabela.data_category == "Time"
    assert data.tipo is None
    assert ano.tipo == "calculated"
    assert valor.resumir_por == "sum"
    assert data.resumir_por == "none"
    assert tabela.particoes[0].tipo_origem == "calculated"


def test_normaliza_a_cardinalidade_do_relacionamento(tmp_path):
    """O TMSL grava `one`/`many`; o padrão ausente é muitos-para-um.

    O P8 tem um relacionamento com `fromCardinality: "one"` explícito, que é
    um-para-um. Presumir muitos-para-um faria MOD-006 e MOD-007 errarem.
    """
    caminho = modelo_com(
        tmp_path,
        {
            "tables": [],
            "relationships": [
                {"name": "padrao", "fromTable": "F", "fromColumn": "k", "toTable": "D", "toColumn": "k"},
                {
                    "name": "um-para-um",
                    "fromTable": "A",
                    "fromColumn": "k",
                    "toTable": "B",
                    "toColumn": "k",
                    "fromCardinality": "one",
                },
                {
                    "name": "explicito",
                    "fromTable": "F2",
                    "fromColumn": "k",
                    "toTable": "D2",
                    "toColumn": "k",
                    "fromCardinality": "many",
                    "toCardinality": "one",
                },
            ],
        },
    )

    padrao, um_para_um, explicito = ler_modelo(caminho).relacionamentos

    assert (padrao.cardinalidade_origem, padrao.cardinalidade_destino) == ("muitos", "um")
    assert (um_para_um.cardinalidade_origem, um_para_um.cardinalidade_destino) == ("um", "um")
    assert (explicito.cardinalidade_origem, explicito.cardinalidade_destino) == ("muitos", "um")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_parser_bim.py -k "propriedades or cardinalidade" -v`
Expected: FAIL. O primeiro teste falha com `AttributeError: 'Tabela' object has no attribute 'data_category'`; o segundo com `assert ('muitos', 'um') == ('um', 'um')`, porque hoje o parser repassa `"one"` sem traduzir.

- [ ] **Step 3: Acrescentar os campos em `core/model.py`**

Em `Coluna`, logo depois de `tipo_dado`:

```python
    tipo: str | None = None
    """`type` do TMSL: `calculated` numa coluna calculada em DAX,
    `calculatedTableColumn` numa coluna de tabela calculada, ausente numa coluna
    vinda da origem. Não confundir com `tipo_dado`, que é o `dataType`."""
    resumir_por: str | None = None
    """`summarizeBy`: a agregação implícita que o Power BI oferece ao autor do
    relatório. `none` significa que a coluna não é somável por padrão."""
```

Em `Tabela`, logo depois de `oculta`:

```python
    data_category: str | None = None
    """`dataCategory`: vale `Time` numa tabela marcada como tabela de data."""
```

Em `Particao`, logo depois de `modo`:

```python
    tipo_origem: str | None = None
    """`source.type`: `m` numa partição de Power Query, `calculated` numa
    tabela calculada em DAX."""
```

- [ ] **Step 4: Mapear os campos em `core/parser_bim.py`**

Em `_coluna`, acrescentar os dois argumentos:

```python
def _coluna(bruto: dict) -> Coluna:
    return Coluna(
        nome=bruto.get("name", ""),
        tipo_dado=bruto.get("dataType"),
        tipo=bruto.get("type"),
        resumir_por=bruto.get("summarizeBy"),
        expressao=_texto(bruto.get("expression")),
        oculta=bool(bruto.get("isHidden", False)),
        bruto=bruto,
    )
```

Em `_particao`:

```python
def _particao(bruto: dict) -> Particao:
    origem = bruto.get("source") or {}
    return Particao(
        nome=bruto.get("name", ""),
        modo=bruto.get("mode"),
        tipo_origem=origem.get("type"),
        origem=_texto(origem.get("expression")),
        bruto=bruto,
    )
```

Em `_tabela`, acrescentar `data_category=bruto.get("dataCategory"),` depois de `oculta=...`.

Acrescentar a função de normalização, antes de `_relacionamento`:

```python
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
```

E usá-la em `_relacionamento`:

```python
        cardinalidade_origem=_cardinalidade(bruto.get("fromCardinality"), "muitos"),
        cardinalidade_destino=_cardinalidade(bruto.get("toCardinality"), "um"),
```

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS, 17 testes (os 15 anteriores mais os 2 novos). Os testes do P8 continuam pulados se `data/` não existir.

- [ ] **Step 6: Commit**

```bash
git add core/model.py core/parser_bim.py tests/test_parser_bim.py
git commit -m "feat(model): propriedades TMSL que as regras leem

type, summarizeBy, dataCategory e source.type viram campos proprios, e a
cardinalidade do relacionamento passa a ser normalizada para um/muitos.
O P8 tem um fromCardinality one explicito: tratar o lado from como
muitos inverteria os lados e faria MOD-006 e MOD-007 errarem."
```

---

### Task 2: O contrato — `core/rules/base.py`

**Files:**
- Create: `core/rules/base.py`
- Test: `tests/test_rules_base.py`

**Interfaces:**
- Consumes: nada de Task 1.
- Produces: `RegraMeta(id, titulo, categoria, severidade, url_canonica, termos_consulta, recomendacao_padrao, nota_de_verificacao=None)`; `Evidencia(tipo_objeto, objeto, tabela=None, trecho=None, detalhe={})`; `Achado(id_regra, evidencia, mensagem)`; `ORDEM_SEVERIDADE: dict[str, int]`.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_base.py`:

```python
"""O contrato entre as regras e o resto do pipeline.

A validação aqui não é cerimônia: a ADR-003 exige que todo achado seja
fundamentado num trecho de documentação recuperado, e uma regra sem URL
canónica, sem termos de consulta ou sem recomendação padrão não tem como
cumprir isso. Por isso o `RegraMeta` se recusa a existir sem eles.
"""

import pytest
from pydantic import ValidationError

from core.rules.base import ORDEM_SEVERIDADE, Achado, Evidencia, RegraMeta

COMPLETA = {
    "id": "MOD-999",
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "severidade": "alta",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema", "dimension table"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil ao leitor.",
}


def test_regra_meta_aceita_metadados_completos():
    meta = RegraMeta(**COMPLETA)

    assert meta.id == "MOD-999"
    assert meta.termos_consulta == ("star schema", "dimension table")
    assert meta.nota_de_verificacao is None


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("url_canonica", ""),
        ("url_canonica", "ver documentacao da Microsoft"),
        ("termos_consulta", []),
        ("recomendacao_padrao", ""),
        ("recomendacao_padrao", "   "),
        ("recomendacao_padrao", "Evite isso."),
        ("severidade", "critica"),
        ("categoria", "modelo"),
    ],
)
def test_regra_meta_recusa_metadado_que_nao_sustenta_o_achado(campo, valor):
    campos = COMPLETA | {campo: valor}

    with pytest.raises(ValidationError):
        RegraMeta(**campos)


def test_achado_carrega_so_a_ocorrencia():
    """Nada de título, severidade ou URL copiados: o catálogo é fonte única."""
    achado = Achado(
        id_regra="MOD-999",
        evidencia=Evidencia(tipo_objeto="tabela", objeto="DimProduct"),
        mensagem="A tabela 'DimProduct' tem o problema X.",
    )

    assert set(achado.model_dump()) == {"id_regra", "evidencia", "mensagem"}
    assert achado.evidencia.detalhe == {}
    assert achado.evidencia.tabela is None


def test_a_ordem_de_severidade_vai_da_alta_para_a_baixa():
    assert ORDEM_SEVERIDADE["alta"] < ORDEM_SEVERIDADE["media"] < ORDEM_SEVERIDADE["baixa"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_base.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.base'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/base.py`:

```python
"""Contrato entre as regras e o resto do pipeline.

Três objetos. `RegraMeta` descreve a regra e vive no catálogo; `Evidencia`
descreve o objeto problemático e o que a regra leu para afirmar isso; `Achado`
liga os dois.

O achado guarda apenas o `id_regra`, nunca uma cópia dos metadados. O catálogo
é fonte única de verdade: é dele que sai a tabela de regras da monografia, e
nenhum achado pode divergir dele.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Categoria = Literal["modelagem", "performance", "dax", "m"]
Severidade = Literal["alta", "media", "baixa"]
TipoObjeto = Literal[
    "tabela", "coluna", "medida", "relacionamento", "particao", "modelo"
]

ORDEM_SEVERIDADE: dict[str, int] = {"alta": 0, "media": 1, "baixa": 2}

TAMANHO_MINIMO_RECOMENDACAO = 40
"""Uma recomendação padrão curta demais é um rótulo, não uma orientação. Ela sai
no relatório quando a geração do LLM é descartada (ADR-003), então é a única
coisa que o leitor recebe nesse caso."""


class RegraMeta(BaseModel):
    """Metadados de uma regra. Imutável: o catálogo não muda em execução."""

    model_config = {"frozen": True}

    id: str
    titulo: str
    categoria: Categoria
    severidade: Severidade
    url_canonica: str
    """A página da documentação oficial que sustenta o achado. A Fase 5 compara
    a citação escolhida pelo LLM com esta URL para medir pertinência."""
    termos_consulta: tuple[str, ...]
    """Termos de busca em inglês, para a recuperação com `bge-small-en`."""
    recomendacao_padrao: str
    """Precisa conter as exceções que a própria fonte declara."""
    nota_de_verificacao: str | None = None
    """Ressalva sobre a detecção, quando houver pendência empírica."""

    @field_validator("url_canonica")
    @classmethod
    def _precisa_ser_url(cls, valor: str) -> str:
        if not valor.startswith("https://"):
            raise ValueError(
                "url_canonica precisa ser uma URL https da documentação oficial"
            )
        return valor

    @field_validator("termos_consulta")
    @classmethod
    def _precisa_ter_termos(cls, valor: tuple[str, ...]) -> tuple[str, ...]:
        if not valor:
            raise ValueError(
                "termos_consulta não pode ser vazio: a Fase 3 recupera por eles"
            )
        return valor

    @field_validator("recomendacao_padrao")
    @classmethod
    def _precisa_ter_texto(cls, valor: str) -> str:
        if len(valor.strip()) < TAMANHO_MINIMO_RECOMENDACAO:
            raise ValueError(
                "recomendacao_padrao precisa de pelo menos "
                f"{TAMANHO_MINIMO_RECOMENDACAO} caracteres de texto útil"
            )
        return valor


class Evidencia(BaseModel):
    """Onde está o problema, e o que a regra leu para afirmar isso."""

    tipo_objeto: TipoObjeto
    objeto: str
    """Nome qualificado: `DimProduct[ProductKey]` numa coluna."""
    tabela: str | None = None
    trecho: str | None = None
    """O DAX, o M ou a propriedade TMSL lida."""
    detalhe: dict[str, Any] = Field(default_factory=dict)
    """Os valores que a regra de fato leu."""


class Achado(BaseModel):
    """Uma ocorrência. Um achado por objeto violador, nunca agregado."""

    id_regra: str
    evidencia: Evidencia
    mensagem: str
    """A frase da ocorrência específica, escrita pela regra."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_base.py -v`
Expected: PASS, 11 testes (1 + 8 parametrizados + 2).

- [ ] **Step 5: Commit**

```bash
git add core/rules/base.py tests/test_rules_base.py
git commit -m "feat(rules): contrato RegraMeta, Evidencia e Achado

O RegraMeta se recusa a existir sem URL canonica, termos de consulta e
recomendacao padrao com texto real: sob a ADR-003, regra sem ancora e
regra que o pipeline nao consegue sustentar. O Achado carrega so a
ocorrencia, para que o catalogo seja fonte unica de verdade."
```

---

### Task 3: O registro — `core/rules/registry.py`

**Files:**
- Create: `core/rules/registry.py`
- Test: `tests/test_rules_registry.py`

**Interfaces:**
- Consumes: `core.rules.base.RegraMeta`, `Achado`.
- Produces: `Registro` com `registrar(meta, avaliador)`, `meta(id)`, `metas()`, `ids()`, `avaliador(id)`, `__len__`; exceção `RegraDuplicada`; decorador `regra(*, registro=None, **campos)`; instância global `REGISTRO`; alias de tipo `Avaliador`.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_registry.py`:

```python
"""O registro de regras.

O parâmetro `registro` do decorador existe para os testes: sem ele, cada teste
sujaria o registro global e a ordem de execução passaria a importar.
"""

import pytest

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.registry import REGISTRO, Registro, RegraDuplicada, regra

CAMPOS = {
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "severidade": "baixa",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil.",
}


def test_registra_a_regra_e_devolve_a_funcao_intacta():
    registro = Registro()

    @regra(id="MOD-901", registro=registro, **CAMPOS)
    def minha_regra(modelo):
        yield Achado(
            id_regra="MOD-901",
            evidencia=Evidencia(tipo_objeto="modelo", objeto="modelo"),
            mensagem="achado de teste",
        )

    assert len(registro) == 1
    assert registro.ids() == ["MOD-901"]
    assert registro.meta("MOD-901").titulo == "Regra de teste"
    assert list(minha_regra(ModeloSemantico()))[0].id_regra == "MOD-901"
    assert registro.avaliador("MOD-901") is minha_regra


def test_recusa_id_duplicado():
    """Duplicar ID é erro na importação, não surpresa em execução."""
    registro = Registro()

    @regra(id="MOD-901", registro=registro, **CAMPOS)
    def primeira(modelo):
        return []

    with pytest.raises(RegraDuplicada, match="MOD-901"):

        @regra(id="MOD-901", registro=registro, **CAMPOS)
        def segunda(modelo):
            return []


def test_ids_saem_ordenados_independente_da_ordem_de_registro():
    registro = Registro()
    for id_regra in ("PERF-003", "MOD-002", "MOD-001"):

        @regra(id=id_regra, registro=registro, **CAMPOS)
        def qualquer(modelo):
            return []

    assert registro.ids() == ["MOD-001", "MOD-002", "PERF-003"]
    assert [m.id for m in registro.metas()] == ["MOD-001", "MOD-002", "PERF-003"]


def test_registro_global_existe_e_e_um_registro():
    assert isinstance(REGISTRO, Registro)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_registry.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.registry'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/registry.py`:

```python
"""Registro das regras.

O registro guarda metadados e função lado a lado, indexados pelo ID. É o que
permite ao achado carregar só o `id_regra` e ao catálogo ser gerado a partir do
código, em vez de mantido à mão.
"""

from collections.abc import Callable, Iterable

from core.model import ModeloSemantico
from core.rules.base import Achado, RegraMeta

Avaliador = Callable[[ModeloSemantico], Iterable[Achado]]


class RegraDuplicada(ValueError):
    """Duas regras com o mesmo ID. Erro de programação, não de dado."""


class Registro:
    """Coleção de regras. Instanciável, para que os testes usem o seu próprio."""

    def __init__(self) -> None:
        self._metas: dict[str, RegraMeta] = {}
        self._avaliadores: dict[str, Avaliador] = {}

    def registrar(self, meta: RegraMeta, avaliador: Avaliador) -> None:
        if meta.id in self._metas:
            raise RegraDuplicada(f"a regra {meta.id} já está registrada")
        self._metas[meta.id] = meta
        self._avaliadores[meta.id] = avaliador

    def ids(self) -> list[str]:
        """IDs em ordem alfabética — a ordem de execução do runner."""
        return sorted(self._metas)

    def meta(self, id_regra: str) -> RegraMeta:
        return self._metas[id_regra]

    def metas(self) -> list[RegraMeta]:
        return [self._metas[i] for i in self.ids()]

    def avaliador(self, id_regra: str) -> Avaliador:
        return self._avaliadores[id_regra]

    def __len__(self) -> int:
        return len(self._metas)


REGISTRO = Registro()
"""Registro global. Só fica populado depois de importar `core.rules.todas`."""


def regra(*, registro: Registro | None = None, **campos) -> Callable[[Avaliador], Avaliador]:
    """Registra a função decorada como regra.

    Os `campos` são os de `RegraMeta`, e é ele quem os valida — uma regra sem
    âncora falha aqui, na importação do módulo.
    """

    def decorador(funcao: Avaliador) -> Avaliador:
        destino = REGISTRO if registro is None else registro
        destino.registrar(RegraMeta(**campos), funcao)
        return funcao

    return decorador
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_registry.py -v`
Expected: PASS, 4 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/registry.py tests/test_rules_registry.py
git commit -m "feat(rules): registro e decorador de regra

ID duplicado levanta RegraDuplicada na importacao. O decorador aceita um
registro alternativo para que os testes nao sujem o global."
```

---

### Task 4: Escopo e construtores de fixture

**Files:**
- Create: `core/rules/escopo.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_rules_escopo.py`

**Interfaces:**
- Consumes: `core.model.{ModeloSemantico, Tabela, Coluna, Relacionamento}` com os campos da Task 1.
- Produces, em `core.rules.escopo`: `anotacoes(bruto) -> dict[str, str]`; `tabela_automatica_de_data(t)`, `tabela_apenas_de_medidas(t)`, `tabela_de_parametro_hipotetico(t)`, `tabela_gerada_por_analise(t)`, `fora_de_escopo(t)` → `bool`; `tabelas_em_escopo(modelo) -> list[Tabela]`; `nomes_em_escopo(modelo) -> set[str]`; `relacionamentos_em_escopo(modelo) -> list[Relacionamento]`; `coluna_gerada_por_analise(c) -> bool`; `tabela_por_nome(modelo, nome) -> Tabela | None`; `tipo_da_coluna(modelo, tabela, coluna) -> str | None`; `dimensao_de_data(modelo) -> set[str]`; `um_para_um(r) -> bool`; `lado_um(r) -> set[str]`; `lado_muitos(r) -> set[str]`.
- Produces, em `tests/conftest.py`: `coluna`, `medida`, `particao`, `tabela`, `relacionamento`, `modelo_tmsl` (construtores de dicionário TMSL) e a fixture `ler`.

- [ ] **Step 1: Acrescentar os construtores em `tests/conftest.py`**

Acrescentar ao fim do arquivo, mantendo `escrever_pbip` e `pbip_minimo` como estão:

```python
from core.model import ModeloSemantico
from core.parser_bim import ler_modelo


def coluna(
    nome: str,
    *,
    tipo_dado: str = "string",
    tipo: str | None = None,
    expressao: str | None = None,
    resumir_por: str = "none",
    oculta: bool = False,
    annotations: dict[str, str] | None = None,
) -> dict:
    """Uma coluna TMSL. `tipo` é o `type`: `calculated`, `calculatedTableColumn`."""
    bruto: dict = {"name": nome, "dataType": tipo_dado, "summarizeBy": resumir_por}
    if tipo is not None:
        bruto["type"] = tipo
    if expressao is not None:
        bruto["expression"] = expressao
    if oculta:
        bruto["isHidden"] = True
    if annotations:
        bruto["annotations"] = _annotations(annotations)
    return bruto


def medida(nome: str, expressao: str = "1") -> dict:
    return {"name": nome, "expression": expressao}


def particao(
    nome: str = "particao",
    *,
    tipo: str = "m",
    expressao: str = "let Fonte = 1 in Fonte",
) -> dict:
    return {
        "name": nome,
        "mode": "import",
        "source": {"type": tipo, "expression": expressao},
    }


def tabela(
    nome: str,
    *,
    colunas: list[dict] | tuple = (),
    medidas: list[dict] | tuple = (),
    particoes: list[dict] | tuple = (),
    data_category: str | None = None,
    annotations: dict[str, str] | None = None,
) -> dict:
    bruto: dict = {
        "name": nome,
        "columns": list(colunas),
        "measures": list(medidas),
        "partitions": list(particoes),
    }
    if data_category is not None:
        bruto["dataCategory"] = data_category
    if annotations:
        bruto["annotations"] = _annotations(annotations)
    return bruto


def relacionamento(
    origem: str,
    coluna_origem: str,
    destino: str,
    coluna_destino: str,
    *,
    bidirecional: bool = False,
    cross_filtering: str | None = None,
    cardinalidade_origem: str | None = None,
    cardinalidade_destino: str | None = None,
) -> dict:
    """Um relacionamento TMSL.

    `cross_filtering` existe para exercitar valores que não são
    `bothDirections`, como `automatic`.
    """
    bruto: dict = {
        "name": f"{origem}-{destino}-{coluna_origem}",
        "fromTable": origem,
        "fromColumn": coluna_origem,
        "toTable": destino,
        "toColumn": coluna_destino,
    }
    if bidirecional:
        bruto["crossFilteringBehavior"] = "bothDirections"
    elif cross_filtering is not None:
        bruto["crossFilteringBehavior"] = cross_filtering
    if cardinalidade_origem is not None:
        bruto["fromCardinality"] = cardinalidade_origem
    if cardinalidade_destino is not None:
        bruto["toCardinality"] = cardinalidade_destino
    return bruto


def modelo_tmsl(tabelas=(), relacionamentos=()) -> dict:
    return {
        "name": "SemanticModel",
        "compatibilityLevel": 1600,
        "model": {
            "culture": "pt-BR",
            "tables": list(tabelas),
            "relationships": list(relacionamentos),
        },
    }


def _annotations(pares: dict[str, str]) -> list[dict]:
    return [{"name": n, "value": v} for n, v in pares.items()]


@pytest.fixture
def ler(tmp_path: Path):
    """Escreve um `model.bim` sintético e devolve o modelo já parseado.

    As regras recebem `ModeloSemantico`, não dicionário. Passar pelo parser nos
    testes garante que o que a regra lê é o que o parser produz.
    """

    def _ler(tabelas=(), relacionamentos=()) -> ModeloSemantico:
        caminho = tmp_path / "model.bim"
        caminho.write_text(
            json.dumps(modelo_tmsl(tabelas, relacionamentos), ensure_ascii=False),
            encoding="utf-8",
        )
        return ler_modelo(caminho)

    return _ler
```

- [ ] **Step 2: Write the failing test**

Criar `tests/test_rules_escopo.py`:

```python
"""Quem entra na auditoria.

Princípio: auditar o que o autor escreveu. Cada exclusão aqui evita um falso
positivo concreto, observado no P8 — e nenhuma é por nome de objeto.
"""

from core.rules.escopo import (
    anotacoes,
    coluna_gerada_por_analise,
    dimensao_de_data,
    lado_muitos,
    lado_um,
    nomes_em_escopo,
    relacionamentos_em_escopo,
    tabela_apenas_de_medidas,
    tabela_automatica_de_data,
    tabela_de_parametro_hipotetico,
    tabela_gerada_por_analise,
    tabela_por_nome,
    tipo_da_coluna,
    um_para_um,
)
from conftest import coluna, medida, particao, relacionamento, tabela


def test_anotacoes_viram_dicionario(ler):
    modelo = ler(tabelas=[tabela("T", annotations={"PBI_Id": "abc"})])

    assert anotacoes(modelo.tabelas[0].bruto) == {"PBI_Id": "abc"}


def test_anotacoes_de_objeto_sem_annotations(ler):
    modelo = ler(tabelas=[tabela("T")])

    assert anotacoes(modelo.tabelas[0].bruto) == {}


def test_exclui_tabela_automatica_de_data(ler):
    modelo = ler(
        tabelas=[
            tabela("LocalDateTable_x", annotations={"__PBI_LocalDateTable": "true"}),
            tabela("DateTableTemplate_x", annotations={"__PBI_TemplateDateTable": "true"}),
            tabela("DimCalendar"),
        ]
    )
    local, template, calendario = modelo.tabelas

    assert tabela_automatica_de_data(local)
    assert tabela_automatica_de_data(template)
    assert not tabela_automatica_de_data(calendario)
    assert nomes_em_escopo(modelo) == {"DimCalendar"}


def test_exclui_tabela_apenas_de_medidas(ler):
    """Como a `_Medidas` do P8: medidas e nenhuma coluna de dados."""
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64")],
                medidas=[medida("Faturamento")],
                particoes=[particao(tipo="calculated", expressao='Row("Coluna", BLANK())')],
            ),
            tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")]),
        ]
    )
    so_medidas, dimensao = modelo.tabelas

    assert tabela_apenas_de_medidas(so_medidas)
    assert not tabela_apenas_de_medidas(dimensao)


def test_tabela_com_medidas_e_coluna_de_dados_continua_em_escopo(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "FactOnlineSales",
                colunas=[coluna("Valor", tipo_dado="decimal", resumir_por="sum")],
                medidas=[medida("Total")],
            )
        ]
    )

    assert not tabela_apenas_de_medidas(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == {"FactOnlineSales"}


def test_exclui_tabela_de_parametro_hipotetico(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Parâmetro",
                colunas=[coluna("Parâmetro", tipo="calculatedTableColumn", tipo_dado="double")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")],
            )
        ]
    )

    assert tabela_de_parametro_hipotetico(modelo.tabelas[0])


def test_parametro_hipotetico_sem_medida_continua_fora_de_escopo(ler):
    """A exclusão existe por si, não pelo acaso de a tabela ter uma medida."""
    modelo = ler(
        tabelas=[
            tabela(
                "Meta",
                colunas=[coluna("Meta", tipo="calculatedTableColumn", tipo_dado="double")],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 100, 10)")],
            )
        ]
    )
    assert not tabela_apenas_de_medidas(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == set()


def test_reconhece_generateseries_com_caixa_espaco_e_comentario(ler):
    """Review Focus 5: um predicado literal demais reabre o falso positivo."""
    variantes = [
        "  generateseries(0, 1, 0.05)",
        "GENERATESERIES (0, 1, 0.05)",
        "// parametro de previsao\n\nGenerateSeries(0, 1, 0.05)",
        ["", "// comentario", "GENERATESERIES(0, 1, 0.05)"],
    ]
    for i, expressao in enumerate(variantes):
        modelo = ler(
            tabelas=[
                tabela(f"P{i}", particoes=[particao(tipo="calculated", expressao=expressao)])
            ]
        )
        assert tabela_de_parametro_hipotetico(modelo.tabelas[0]), expressao


def test_nao_confunde_outra_tabela_calculada_com_parametro(ler):
    modelo = ler(
        tabelas=[tabela("DimCalendar", particoes=[particao(tipo="calculated", expressao="CALENDAR(1, 2)")])]
    )

    assert not tabela_de_parametro_hipotetico(modelo.tabelas[0])


def test_exclui_tabela_gerada_por_analise(ler):
    modelo = ler(tabelas=[tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "1"})])

    assert tabela_gerada_por_analise(modelo.tabelas[0])
    assert nomes_em_escopo(modelo) == set()


def test_exclui_coluna_de_agrupamento_ou_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimCustomer",
                colunas=[
                    coluna(
                        "Faixa de Renda",
                        tipo="calculated",
                        expressao="SWITCH(...)",
                        annotations={"GroupingDesignState": "{}"},
                    ),
                    coluna("Salário", tipo="calculated", expressao="[Base] * 1.1", tipo_dado="double"),
                ],
            )
        ]
    )
    faixa, salario = modelo.tabelas[0].colunas

    assert coluna_gerada_por_analise(faixa)
    assert not coluna_gerada_por_analise(salario)


def test_relacionamentos_em_escopo_descartam_pontas_excluidas(ler):
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
            tabela("FactOnlineSales", colunas=[coluna("PromotionKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date"),
            relacionamento("FactOnlineSales", "PromotionKey", "DimPromotion", "PromotionKey"),
        ],
    )

    nomes = [r.nome for r in relacionamentos_em_escopo(modelo)]

    assert nomes == ["FactOnlineSales-DimPromotion-PromotionKey"]


def test_tipo_da_coluna_devolve_none_em_referencia_inexistente(ler):
    """Review Focus 3: modelo inconsistente não pode virar KeyError."""
    modelo = ler(tabelas=[tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")])])

    assert tipo_da_coluna(modelo, "DimProduct", "ProductKey") == "int64"
    assert tipo_da_coluna(modelo, "DimProduct", "NaoExiste") is None
    assert tipo_da_coluna(modelo, "TabelaFantasma", "ProductKey") is None
    assert tabela_por_nome(modelo, "TabelaFantasma") is None


def test_dimensao_de_data_sobrevive_a_relacionamento_orfao(ler):
    """Review Focus 3, continuação: o lookup falho não derruba a detecção."""
    modelo = ler(
        tabelas=[tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")])],
        relacionamentos=[relacionamento("TabelaFantasma", "DateKey", "DimCalendar", "Data")],
    )

    assert dimensao_de_data(modelo) == set()


def test_dimensao_de_data_e_o_lado_um_de_relacionamento_entre_datas(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data"),
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey"),
        ],
    )

    assert dimensao_de_data(modelo) == {"DimCalendar"}


def test_lados_do_relacionamento_respeitam_a_cardinalidade(ler):
    modelo = ler(
        relacionamentos=[
            relacionamento("FactOnlineSales", "k", "DimStore", "k"),
            relacionamento("DimGeography", "k", "DimCustomer", "k", cardinalidade_origem="one"),
        ]
    )
    muitos_para_um, de_um_para_um = modelo.relacionamentos

    assert lado_um(muitos_para_um) == {"DimStore"}
    assert lado_muitos(muitos_para_um) == {"FactOnlineSales"}
    assert not um_para_um(muitos_para_um)

    assert lado_um(de_um_para_um) == {"DimGeography", "DimCustomer"}
    assert lado_muitos(de_um_para_um) == set()
    assert um_para_um(de_um_para_um)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_rules_escopo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.escopo'`.

- [ ] **Step 4: Write minimal implementation**

Criar `core/rules/escopo.py`:

```python
"""Quem entra na auditoria.

Princípio único: **auditar o que o autor escreveu.** O Power BI gera objetos por
conta própria — tabelas de data automáticas, tabelas de mapeamento de cluster,
colunas de agrupamento — e marcá-los como defeito do autor é falso positivo.
Alguns padrões legítimos também precisam de exceção: a tabela que só carrega
medidas e a tabela de parâmetro hipotético não têm relacionamento por natureza.

Cada exclusão aqui é um predicado explícito em TMSL. Nenhuma é por nome de
objeto: nome é convenção, annotation é fato.

Este módulo é a única casa desse julgamento. Nenhuma regra o reimplementa.
"""

from core.model import Coluna, ModeloSemantico, Relacionamento, Tabela

ANOTACOES_DATA_AUTOMATICA = ("__PBI_TemplateDateTable", "__PBI_LocalDateTable")
ANOTACAO_ANALISE_GERADA = "ClusterMappingTable"
ANOTACAO_COLUNA_GERADA = "GroupingDesignState"
FUNCAO_PARAMETRO_HIPOTETICO = "GENERATESERIES"


def anotacoes(bruto: dict) -> dict[str, str]:
    """As annotations do objeto TMSL, como nome → valor.

    O parser guarda o TMSL de origem em `bruto` justamente para isto: a
    annotation não foi normalizada, mas está acessível sem reabrir o arquivo.
    """
    return {
        item.get("name", ""): item.get("value", "")
        for item in bruto.get("annotations", [])
        if isinstance(item, dict)
    }


def _primeira_linha_util(expressao: str | None) -> str:
    """A primeira linha que não é vazia nem comentário `//`."""
    for linha in (expressao or "").splitlines():
        limpa = linha.strip()
        if limpa and not limpa.startswith("//"):
            return limpa
    return ""


def tabela_automatica_de_data(t: Tabela) -> bool:
    """Tabela de data gerada pelo Tempo automático de data/hora (MOD-001)."""
    marcas = anotacoes(t.bruto)
    return any(marca in marcas for marca in ANOTACOES_DATA_AUTOMATICA)


def tabela_apenas_de_medidas(t: Tabela) -> bool:
    """Tabela que só carrega medidas: nenhuma coluna de dados.

    Numa tabela dessas todas as colunas são `calculatedTableColumn` — a coluna
    fictícia que o Power BI cria para a tabela existir. É padrão consagrado para
    organizar medidas, não defeito.
    """
    if not t.medidas:
        return False
    return all(c.tipo == "calculatedTableColumn" for c in t.colunas)


def tabela_de_parametro_hipotetico(t: Tabela) -> bool:
    """Tabela de parâmetro hipotético: tabela calculada com `GENERATESERIES`.

    É a assinatura canónica desse objeto, e ele não tem relacionamento por
    natureza. A detecção tolera caixa, espaço e linha de comentário porque o
    predicado é o que separa um achado de um falso positivo.
    """
    for p in t.particoes:
        if p.tipo_origem != "calculated":
            continue
        if _primeira_linha_util(p.origem).upper().startswith(FUNCAO_PARAMETRO_HIPOTETICO):
            return True
    return False


def tabela_gerada_por_analise(t: Tabela) -> bool:
    """Tabela criada pelos recursos de agrupamento e clustering do Power BI."""
    return ANOTACAO_ANALISE_GERADA in anotacoes(t.bruto)


def fora_de_escopo(t: Tabela) -> bool:
    return (
        tabela_automatica_de_data(t)
        or tabela_apenas_de_medidas(t)
        or tabela_de_parametro_hipotetico(t)
        or tabela_gerada_por_analise(t)
    )


def tabelas_em_escopo(modelo: ModeloSemantico) -> list[Tabela]:
    return [t for t in modelo.tabelas if not fora_de_escopo(t)]


def nomes_em_escopo(modelo: ModeloSemantico) -> set[str]:
    return {t.nome for t in tabelas_em_escopo(modelo)}


def relacionamentos_em_escopo(modelo: ModeloSemantico) -> list[Relacionamento]:
    """Relacionamentos cujas duas pontas estão em escopo.

    Sem isto, MOD-005 marcaria as tabelas de data automáticas — elas são alvo de
    relacionamento `dateTime → dateTime` e não têm `dataCategory: "Time"`.
    """
    nomes = nomes_em_escopo(modelo)
    return [
        r
        for r in modelo.relacionamentos
        if r.tabela_origem in nomes and r.tabela_destino in nomes
    ]


def coluna_gerada_por_analise(c: Coluna) -> bool:
    """Coluna cujo DAX foi escrito pela interface de grupos e clusters."""
    return ANOTACAO_COLUNA_GERADA in anotacoes(c.bruto)


def tabela_por_nome(modelo: ModeloSemantico, nome: str) -> Tabela | None:
    for t in modelo.tabelas:
        if t.nome == nome:
            return t
    return None


def tipo_da_coluna(modelo: ModeloSemantico, tabela: str, coluna: str) -> str | None:
    """Tipo de dado de uma coluna, ou `None` se a referência não existir.

    Relacionamento apontando para objeto inexistente é modelo inconsistente, não
    motivo para a auditoria falhar.
    """
    alvo = tabela_por_nome(modelo, tabela)
    if alvo is None:
        return None
    for c in alvo.colunas:
        if c.nome == coluna:
            return c.tipo_dado
    return None


def dimensao_de_data(modelo: ModeloSemantico) -> set[str]:
    """Tabelas que servem de dimensão de data no modelo.

    Critério estrutural: estar no lado "um" de um relacionamento cujas duas
    pontas são `dateTime`. Serve a dois propósitos opostos — é o alvo de MOD-005
    e a exclusão de PERF-001 —, e é por isso que mora aqui.
    """
    dimensoes: set[str] = set()
    for r in relacionamentos_em_escopo(modelo):
        tipo_origem = tipo_da_coluna(modelo, r.tabela_origem, r.coluna_origem)
        tipo_destino = tipo_da_coluna(modelo, r.tabela_destino, r.coluna_destino)
        if tipo_origem == "dateTime" and tipo_destino == "dateTime":
            dimensoes |= lado_um(r)
    return dimensoes


def um_para_um(r: Relacionamento) -> bool:
    return r.cardinalidade_origem == "um" and r.cardinalidade_destino == "um"


def lado_um(r: Relacionamento) -> set[str]:
    """Tabelas no lado "um" — as duas, se o relacionamento for um-para-um."""
    lados = set()
    if r.cardinalidade_origem == "um":
        lados.add(r.tabela_origem)
    if r.cardinalidade_destino == "um":
        lados.add(r.tabela_destino)
    return lados


def lado_muitos(r: Relacionamento) -> set[str]:
    lados = set()
    if r.cardinalidade_origem == "muitos":
        lados.add(r.tabela_origem)
    if r.cardinalidade_destino == "muitos":
        lados.add(r.tabela_destino)
    return lados
```

**Atenção em `dimensao_de_data`:** num relacionamento `dateTime → dateTime` um-para-um, `lado_um` devolve as duas pontas. É o comportamento correto — ambas são candidatas a dimensão de data —, e MOD-005 decide pela `dataCategory` de cada uma.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_rules_escopo.py -v`
Expected: PASS, 16 testes.

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: PASS. Nenhum teste anterior quebra — `escrever_pbip` e `pbip_minimo` não foram tocados.

- [ ] **Step 7: Commit**

```bash
git add core/rules/escopo.py tests/conftest.py tests/test_rules_escopo.py
git commit -m "feat(rules): escopo da auditoria e construtores de fixture

Auditar o que o autor escreveu: exclui tabelas de data automaticas,
tabelas so de medidas, parametros hipoteticos e tabelas de cluster, mais
colunas de agrupamento. Cada exclusao e um predicado em TMSL, nunca um
nome de objeto. O lookup de coluna devolve None em referencia orfa, e os
lados do relacionamento saem da cardinalidade, nao de from/to."
```

---

### Task 5: O runner — `core/rules/runner.py`

**Files:**
- Create: `core/rules/runner.py`
- Test: `tests/test_rules_runner.py`

**Interfaces:**
- Consumes: `Registro`, `REGISTRO`, `regra`, `ORDEM_SEVERIDADE`, `Achado`, `Evidencia`.
- Produces: `FalhaDeRegra(id_regra, erro)`; `ResultadoRegras(achados, regras_com_falha, regras_executadas)` com propriedade `total_de_regras`; `avaliar(modelo, registro=None) -> ResultadoRegras`.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_runner.py`:

```python
"""Execução das regras.

Duas garantias que o resto do projeto depende: a ordem da saída é
determinística, porque a Fase 5 compara listas; e uma regra que explode não
derruba a auditoria, mas também não desaparece em silêncio.
"""

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.registry import Registro, regra
from core.rules.runner import avaliar

CAMPOS = {
    "titulo": "Regra de teste",
    "categoria": "modelagem",
    "url_canonica": "https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    "termos_consulta": ["star schema"],
    "recomendacao_padrao": "Texto de recomendação com tamanho suficiente para ser útil.",
}


def _achado(id_regra: str, objeto: str) -> Achado:
    return Achado(
        id_regra=id_regra,
        evidencia=Evidencia(tipo_objeto="tabela", objeto=objeto),
        mensagem=f"problema em {objeto}",
    )


def test_ordena_por_severidade_depois_id_depois_objeto():
    registro = Registro()

    @regra(id="MOD-902", severidade="baixa", registro=registro, **CAMPOS)
    def baixa(modelo):
        return [_achado("MOD-902", "Zebra"), _achado("MOD-902", "Alfa")]

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def alta(modelo):
        return [_achado("MOD-901", "Beta")]

    @regra(id="PERF-901", severidade="alta", registro=registro, **CAMPOS)
    def outra_alta(modelo):
        return [_achado("PERF-901", "Alfa")]

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert [(a.id_regra, a.evidencia.objeto) for a in resultado.achados] == [
        ("MOD-901", "Beta"),
        ("PERF-901", "Alfa"),
        ("MOD-902", "Alfa"),
        ("MOD-902", "Zebra"),
    ]
    assert resultado.regras_executadas == 3
    assert resultado.total_de_regras == 3


def test_isola_a_regra_que_levanta_excecao():
    registro = Registro()

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def explode(modelo):
        raise KeyError("propriedade inesperada")

    @regra(id="MOD-902", severidade="alta", registro=registro, **CAMPOS)
    def funciona(modelo):
        return [_achado("MOD-902", "DimProduct")]

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert [a.id_regra for a in resultado.achados] == ["MOD-902"]
    assert [f.id_regra for f in resultado.regras_com_falha] == ["MOD-901"]
    assert "KeyError" in resultado.regras_com_falha[0].erro
    assert resultado.regras_executadas == 1
    assert resultado.total_de_regras == 2


def test_isola_tambem_a_regra_geradora_que_explode_no_meio():
    """`yield` antes da exceção: o erro só aparece ao consumir o gerador."""
    registro = Registro()

    @regra(id="MOD-901", severidade="alta", registro=registro, **CAMPOS)
    def explode_no_meio(modelo):
        yield _achado("MOD-901", "DimProduct")
        raise ValueError("estado inesperado")

    resultado = avaliar(ModeloSemantico(), registro=registro)

    assert resultado.achados == []
    assert [f.id_regra for f in resultado.regras_com_falha] == ["MOD-901"]


def test_registro_vazio_devolve_resultado_vazio():
    resultado = avaliar(ModeloSemantico(), registro=Registro())

    assert resultado.achados == []
    assert resultado.regras_com_falha == []
    assert resultado.total_de_regras == 0
```

Nota sobre o terceiro teste: a regra geradora que explode no meio **perde** os achados já produzidos, porque a exceção interrompe o `extend`. É o comportamento desejado — resultado parcial de regra com defeito é pior que resultado nenhum, e a falha aparece em `regras_com_falha`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_runner.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.runner'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/runner.py`:

```python
"""Execução das regras.

A auditoria é sequencial e sem estado (ADR-003). Este módulo é o passo "regras"
do fluxo: recebe o modelo normalizado e devolve os achados, em ordem estável.
"""

import logging

from pydantic import BaseModel, Field

from core.model import ModeloSemantico
from core.rules.base import ORDEM_SEVERIDADE, Achado
from core.rules.registry import REGISTRO, Registro

logger = logging.getLogger(__name__)


class FalhaDeRegra(BaseModel):
    id_regra: str
    erro: str


class ResultadoRegras(BaseModel):
    """O que a etapa de regras entrega.

    Não é uma lista nua de propósito: a interface precisa poder dizer "7 de 8
    regras executadas" em vez de entregar menos achados em silêncio.
    """

    achados: list[Achado] = Field(default_factory=list)
    regras_com_falha: list[FalhaDeRegra] = Field(default_factory=list)
    regras_executadas: int = 0

    @property
    def total_de_regras(self) -> int:
        return self.regras_executadas + len(self.regras_com_falha)


def avaliar(
    modelo: ModeloSemantico, registro: Registro | None = None
) -> ResultadoRegras:
    """Executa as regras do registro sobre o modelo.

    A ordem da saída é severidade (alta → baixa), ID da regra e nome do objeto.
    Determinismo não é estética: a avaliação da Fase 5 compara listas, e uma
    ordem instável viraria diferença falsa entre execuções.

    Uma regra que levanta exceção é isolada e registrada. O usuário final não
    perde a auditoria inteira por causa de uma propriedade inesperada do TMSL.
    """
    reg = REGISTRO if registro is None else registro
    achados: list[Achado] = []
    falhas: list[FalhaDeRegra] = []
    executadas = 0

    for id_regra in reg.ids():
        try:
            achados.extend(reg.avaliador(id_regra)(modelo))
        except Exception as erro:  # noqa: BLE001 — isolar é o objetivo
            logger.exception("a regra %s falhou", id_regra)
            falhas.append(
                FalhaDeRegra(id_regra=id_regra, erro=f"{type(erro).__name__}: {erro}")
            )
        else:
            executadas += 1

    achados.sort(
        key=lambda a: (
            ORDEM_SEVERIDADE[reg.meta(a.id_regra).severidade],
            a.id_regra,
            a.evidencia.objeto,
        )
    )
    return ResultadoRegras(
        achados=achados, regras_com_falha=falhas, regras_executadas=executadas
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_runner.py -v`
Expected: PASS, 4 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/runner.py tests/test_rules_runner.py
git commit -m "feat(rules): runner com ordem estavel e isolamento de erro

A saida e ordenada por severidade, id e objeto, porque a Fase 5 compara
listas. Regra que explode vira FalhaDeRegra em vez de derrubar a
auditoria, e o resultado diz quantas regras executaram."
```

---

### Task 6: MOD-001, MOD-002 e MOD-003

**Files:**
- Create: `core/rules/modelagem.py`
- Test: `tests/test_rules_modelagem.py`

**Interfaces:**
- Consumes: `regra`, `Achado`, `Evidencia`, e de `escopo`: `anotacoes`, `ANOTACOES_DATA_AUTOMATICA`, `tabela_automatica_de_data`, `tabelas_em_escopo`, `relacionamentos_em_escopo`, `um_para_um`.
- Produces: as funções `tempo_automatico_ligado`, `relacionamento_bidirecional`, `tabela_sem_relacionamento`, registradas como `MOD-001`, `MOD-002`, `MOD-003` no `REGISTRO` global.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_modelagem.py`:

```python
"""As regras de modelagem.

Cada regra tem caso positivo e negativo. Os negativos são o que separa uma
auditoria útil de uma lista de ruído, e vários deles vêm de falsos positivos
observados no P8.
"""

from core.rules.modelagem import (
    relacionamento_bidirecional,
    tabela_sem_relacionamento,
    tempo_automatico_ligado,
)
from conftest import coluna, medida, particao, relacionamento, tabela


def test_mod001_marca_cada_tabela_de_data_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela("DateTableTemplate_abc", annotations={"__PBI_TemplateDateTable": "true"}),
            tabela("LocalDateTable_def", annotations={"__PBI_LocalDateTable": "true"}),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
        ]
    )

    achados = list(tempo_automatico_ligado(modelo))

    assert {a.evidencia.objeto for a in achados} == {
        "DateTableTemplate_abc",
        "LocalDateTable_def",
    }
    assert all(a.id_regra == "MOD-001" for a in achados)
    assert all(a.evidencia.tipo_objeto == "tabela" for a in achados)
    assert achados[0].evidencia.detalhe["annotation"] in (
        "__PBI_TemplateDateTable",
        "__PBI_LocalDateTable",
    )


def test_mod001_nao_marca_modelo_sem_tempo_automatico(ler):
    modelo = ler(tabelas=[tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")])])

    assert list(tempo_automatico_ligado(modelo)) == []


def test_mod002_marca_relacionamento_bidirecional(ler):
    modelo = ler(
        tabelas=[
            tabela("DimProduct", colunas=[coluna("SubKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey", bidirecional=True)
        ],
    )

    achados = list(relacionamento_bidirecional(modelo))

    assert len(achados) == 1
    assert achados[0].id_regra == "MOD-002"
    assert achados[0].evidencia.tipo_objeto == "relacionamento"
    assert "DimProduct[SubKey]" in achados[0].evidencia.objeto
    assert achados[0].evidencia.detalhe["crossFilteringBehavior"] == "bothDirections"


def test_mod002_ignora_um_para_um(ler):
    """Review Focus 2: todo um-para-um é obrigatoriamente bidirecional.

    A documentação diz que não é possível configurar de outro jeito, então o
    achado de bidirecional traria recomendação impossível de cumprir. O problema
    real é o um-para-um, e quem o afirma é MOD-007.
    """
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento(
                "DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                bidirecional=True, cardinalidade_origem="one",
            )
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod002_ignora_cross_filtering_automatic(ler):
    """Review Focus 4: `automatic` deixa o motor decidir, não é bidirecional."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey", cross_filtering="automatic")
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod002_ignora_relacionamento_com_tabela_automatica(ler):
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[
            relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date", bidirecional=True)
        ],
    )

    assert list(relacionamento_bidirecional(modelo)) == []


def test_mod003_marca_tabela_sem_relacionamento(ler):
    modelo = ler(
        tabelas=[
            tabela("DimEmployee", colunas=[coluna("EmployeeKey", tipo_dado="int64")]),
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    achados = list(tabela_sem_relacionamento(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimEmployee"]
    assert achados[0].id_regra == "MOD-003"


def test_mod003_ignora_tabela_apenas_de_medidas(ler):
    """Como a `_Medidas` do P8: 92 medidas, zero relacionamento, e tudo certo."""
    modelo = ler(
        tabelas=[
            tabela(
                "_Medidas",
                colunas=[coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64")],
                medidas=[medida("Faturamento")],
                particoes=[particao(tipo="calculated", expressao='Row("Coluna", BLANK())')],
            )
        ]
    )

    assert list(tabela_sem_relacionamento(modelo)) == []


def test_mod003_ignora_parametro_hipotetico_e_tabela_de_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela("Parâmetro", particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")]),
            tabela("ClusterMappingTable", annotations={"ClusterMappingTable": "1"}),
        ]
    )

    assert list(tabela_sem_relacionamento(modelo)) == []


def test_mod003_considera_relacionada_a_tabela_ligada_so_a_uma_automatica(ler):
    """A tabela automática está fora de escopo, mas o relacionamento existe."""
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date")],
    )

    assert list(tabela_sem_relacionamento(modelo)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_modelagem.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.modelagem'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/modelagem.py`:

```python
"""Regras de modelagem.

Cada regra declara a página do Microsoft Learn que a sustenta, e a recomendação
padrão repete as exceções que essa página declara. Afirmar mais do que a fonte é
o defeito que esta etapa evitou duas vezes ao verificar as âncoras antes de
escrever código (spec, seção 9).
"""

from collections.abc import Iterator

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.escopo import (
    ANOTACOES_DATA_AUTOMATICA,
    anotacoes,
    relacionamentos_em_escopo,
    tabela_automatica_de_data,
    tabelas_em_escopo,
    um_para_um,
)
from core.rules.registry import regra


def _nome_do_relacionamento(r) -> str:
    return (
        f"{r.tabela_origem}[{r.coluna_origem}] → "
        f"{r.tabela_destino}[{r.coluna_destino}]"
    )


@regra(
    id="MOD-001",
    titulo="Tempo automático de data/hora está ligado",
    categoria="modelagem",
    severidade="alta",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time",
    termos_consulta=[
        "auto date/time",
        "hidden auto date/time tables",
        "disable auto date time",
        "model size date columns",
    ],
    recomendacao_padrao=(
        "Desligue o Tempo automático de data/hora e use uma tabela de data própria, "
        "marcada como tabela de data. Cada coluna de data do modelo gera uma tabela "
        "oculta, que é uma tabela calculada e aumenta o tamanho do modelo e o tempo "
        "de atualização. Como a opção se aplica a todas as colunas de data ou a "
        "nenhuma, não é possível desligá-la caso a caso. Mantenha-a ligada apenas em "
        "modelos exploratórios, com necessidades simples de tempo em períodos de "
        "calendário."
    ),
)
def tempo_automatico_ligado(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela de data gerada pelo produto.

    É a única regra que olha fora do escopo: estas tabelas são o achado dela, e
    insumo de nenhuma outra.
    """
    for t in modelo.tabelas:
        if not tabela_automatica_de_data(t):
            continue
        marcas = anotacoes(t.bruto)
        annotation = next(m for m in ANOTACOES_DATA_AUTOMATICA if m in marcas)
        yield Achado(
            id_regra="MOD-001",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={"annotation": annotation, "colunas": len(t.colunas)},
            ),
            mensagem=(
                f"A tabela oculta '{t.nome}' foi gerada pelo Tempo automático de "
                "data/hora, não pelo autor do modelo."
            ),
        )


@regra(
    id="MOD-002",
    titulo="Relacionamento com filtro bidirecional",
    categoria="modelagem",
    severidade="alta",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering",
    termos_consulta=[
        "bi-directional relationship",
        "filter both directions",
        "CROSSFILTER function",
        "relationship query performance",
    ],
    recomendacao_padrao=(
        "Minimize o uso de relacionamentos bidirecionais: eles exigem mais "
        "processamento, podem degradar o desempenho das consultas e tornam o "
        "comportamento dos filtros confuso para quem usa o relatório. Há dois "
        "cenários em que a propagação nos dois sentidos é legítima — a tabela-ponte "
        "de uma relação muitos-para-muitos entre dimensões, e a análise de uma "
        "dimensão no contexto de outra —, e nos dois a documentação prefere ativar "
        "o filtro bidirecional dentro da medida, com a função CROSSFILTER, em vez de "
        "na propriedade do relacionamento. Para limitar as opções de um segmentador "
        "ao que tem dados, prefira um filtro de visual sobre a medida."
    ),
)
def relacionamento_bidirecional(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por relacionamento bidirecional, exceto um-para-um.

    Num um-para-um a bidirecionalidade é imposta pelo produto — "it isn't
    possible to configure otherwise" —, então o achado pertence a MOD-007.
    """
    for r in relacionamentos_em_escopo(modelo):
        if r.direcao_filtro != "ambos_sentidos" or um_para_um(r):
            continue
        yield Achado(
            id_regra="MOD-002",
            evidencia=Evidencia(
                tipo_objeto="relacionamento",
                objeto=_nome_do_relacionamento(r),
                tabela=r.tabela_origem,
                detalhe={
                    "crossFilteringBehavior": "bothDirections",
                    "cardinalidade": f"{r.cardinalidade_origem}-para-{r.cardinalidade_destino}",
                },
            ),
            mensagem=(
                f"O relacionamento {_nome_do_relacionamento(r)} filtra nos dois "
                "sentidos."
            ),
        )


@regra(
    id="MOD-003",
    titulo="Tabela sem relacionamento com o resto do modelo",
    categoria="modelagem",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    termos_consulta=[
        "star schema model relationships",
        "dimension table fact table",
        "table not related",
        "filter propagation",
    ],
    recomendacao_padrao=(
        "Verifique se a tabela precisa de um relacionamento. Um modelo bem desenhado "
        "entrega o número certo de tabelas com os relacionamentos devidos no lugar: "
        "sem relacionamento, a tabela não filtra nem é filtrada pelas demais, e um "
        "visual que combine os campos dela com os de outra tabela não produz o "
        "resultado esperado. Se a tabela existe apenas para apoiar a integração de "
        "outras consultas, desabilite a carga dela no Power Query."
    ),
    nota_de_verificacao=(
        "Âncora geral, não artigo dedicado — é a mais fraca do conjunto. Daí a "
        "severidade baixa. Reavaliar na Fase 3, com o trecho recuperado em mãos."
    ),
)
def tabela_sem_relacionamento(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela em escopo ausente de todos os relacionamentos.

    Olha **todos** os relacionamentos, não só os em escopo: uma tabela ligada
    apenas a uma tabela de data automática está relacionada, ainda que a outra
    ponta não seja auditável.
    """
    relacionadas: set[str] = set()
    for r in modelo.relacionamentos:
        relacionadas.add(r.tabela_origem)
        relacionadas.add(r.tabela_destino)

    for t in tabelas_em_escopo(modelo):
        if t.nome in relacionadas:
            continue
        yield Achado(
            id_regra="MOD-003",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={"colunas": len(t.colunas), "medidas": len(t.medidas)},
            ),
            mensagem=(
                f"A tabela '{t.nome}' não participa de nenhum relacionamento do "
                "modelo."
            ),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_modelagem.py -v`
Expected: PASS, 10 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/modelagem.py tests/test_rules_modelagem.py
git commit -m "feat(rules): MOD-001, MOD-002 e MOD-003

MOD-002 ignora um-para-um, porque nesse caso a bidirecionalidade e
imposta pelo produto e a recomendacao seria impossivel de cumprir.
MOD-003 olha todos os relacionamentos, nao so os em escopo: tabela
ligada a uma tabela de data automatica esta relacionada."
```

---

### Task 7: MOD-005 — dimensão de data não marcada

**Files:**
- Modify: `core/rules/modelagem.py`
- Test: `tests/test_rules_modelagem.py`

**Interfaces:**
- Consumes: `escopo.dimensao_de_data`, `escopo.tabela_por_nome`.
- Produces: função `dimensao_de_data_nao_marcada`, registrada como `MOD-005`.

- [ ] **Step 1: Write the failing test**

Acrescentar a `tests/test_rules_modelagem.py` (e o import `dimensao_de_data_nao_marcada`):

```python
def test_mod005_marca_dimensao_de_data_sem_data_category(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    achados = list(dimensao_de_data_nao_marcada(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimCalendar"]
    assert achados[0].id_regra == "MOD-005"
    assert achados[0].evidencia.detalhe["dataCategory"] is None


def test_mod005_nao_marca_dimensao_de_data_ja_marcada(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela("DimCalendar", colunas=[coluna("Data", tipo_dado="dateTime")], data_category="Time"),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []


def test_mod005_ignora_tabelas_de_data_automaticas(ler):
    """Review Focus 1: em P8 isso valeria 3 achados inventados.

    `DimPromotion[StartDate] → LocalDateTable_x[Date]` é `dateTime → dateTime` e
    a tabela automática não tem `dataCategory`. Sem o filtro de escopo, MOD-005
    marcaria exatamente os objetos que MOD-001 já aponta — e pediria ao autor
    para marcar como tabela de data algo que ele não criou.
    """
    modelo = ler(
        tabelas=[
            tabela("DimPromotion", colunas=[coluna("StartDate", tipo_dado="dateTime")]),
            tabela("LocalDateTable_x", colunas=[coluna("Date", tipo_dado="dateTime")],
                   annotations={"__PBI_LocalDateTable": "true"}),
        ],
        relacionamentos=[relacionamento("DimPromotion", "StartDate", "LocalDateTable_x", "Date")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []


def test_mod005_ignora_relacionamento_que_nao_e_entre_datas(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    assert list(dimensao_de_data_nao_marcada(modelo)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_modelagem.py -k mod005 -v`
Expected: FAIL com `ImportError: cannot import name 'dimensao_de_data_nao_marcada'`.

- [ ] **Step 3: Write minimal implementation**

Acrescentar a `core/rules/modelagem.py` (e os imports `dimensao_de_data`, `tabela_por_nome` de `escopo`):

```python
@regra(
    id="MOD-005",
    titulo="Dimensão de data não está marcada como tabela de data",
    categoria="modelagem",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-date-tables",
    termos_consulta=[
        "mark as date table",
        "set and use date tables",
        "date table validation unique contiguous",
        "classic time intelligence functions",
    ],
    recomendacao_padrao=(
        "Marque a tabela como tabela de data (Mark as date table) e indique a coluna "
        "de data. Com as funções clássicas de inteligência temporal, a marcação é "
        "obrigatória; ela também é necessária quando os relacionamentos com a tabela "
        "de data usam colunas de outro tipo, como chaves substitutas inteiras no "
        "formato aaaammdd. Ao marcar, o Power BI remove as tabelas de data "
        "automáticas que havia criado — então visuais e expressões apoiados nelas "
        "precisam ser revisados. A coluna de data precisa ter valores únicos, sem "
        "nulos, contíguos e com o mesmo horário em todos os valores, e ser do tipo "
        "Data ou Data/hora. Se o modelo usa a inteligência temporal baseada em "
        "calendário, a marcação pode não ser necessária."
    ),
    nota_de_verificacao=(
        "A detecção assume que a marcação aparece no TMSL como dataCategory=\"Time\" "
        "na tabela, consistente com Table.DataCategory do TOM e com o P8, onde "
        "nenhuma tabela está marcada e nenhuma tem dataCategory. Pendente de "
        "confirmação empírica: marcar a DimCalendar no Desktop, salvar o PBIP e "
        "comparar o model.bim."
    ),
)
def dimensao_de_data_nao_marcada(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por dimensão de data em escopo sem `dataCategory: "Time"`.

    A dimensão é identificada estruturalmente (`escopo.dimensao_de_data`), e não
    por nome: é o lado "um" de um relacionamento entre duas colunas `dateTime`.
    """
    for nome in sorted(dimensao_de_data(modelo)):
        t = tabela_por_nome(modelo, nome)
        if t is None or t.data_category == "Time":
            continue
        yield Achado(
            id_regra="MOD-005",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=t.nome,
                tabela=t.nome,
                detalhe={
                    "dataCategory": t.data_category,
                    "colunas_de_data": [
                        c.nome for c in t.colunas if c.tipo_dado == "dateTime"
                    ],
                },
            ),
            mensagem=(
                f"A tabela '{t.nome}' funciona como dimensão de data do modelo, mas "
                "não está marcada como tabela de data."
            ),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_modelagem.py -v`
Expected: PASS, 14 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/modelagem.py tests/test_rules_modelagem.py
git commit -m "feat(rules): MOD-005, dimensao de data nao marcada

A dimensao e identificada estruturalmente, nao por nome: lado um de um
relacionamento dateTime para dateTime, considerando so relacionamentos
em escopo. Sem esse filtro a regra marcaria as tabelas de data
automaticas do P8 e pediria ao autor para marcar o que ele nao criou."
```

---

### Task 8: MOD-006 e MOD-007 — as duas regras de cardinalidade

**Files:**
- Modify: `core/rules/modelagem.py`
- Test: `tests/test_rules_modelagem.py`

**Interfaces:**
- Consumes: `escopo.{lado_um, lado_muitos, um_para_um, relacionamentos_em_escopo}`.
- Produces: funções `dimensao_em_floco_de_neve` e `relacionamento_um_para_um`, registradas como `MOD-006` e `MOD-007`.

- [ ] **Step 1: Write the failing test**

Acrescentar a `tests/test_rules_modelagem.py` (e os imports das duas funções):

```python
def test_mod006_marca_a_dimensao_intermediaria_da_cadeia(ler):
    """A cadeia do P8: FactOnlineSales → DimProduct → DimProductSubcategory."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("ProductKey", tipo_dado="int64")]),
            tabela("DimProduct", colunas=[coluna("ProductKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "ProductKey", "DimProduct", "ProductKey"),
            relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey"),
        ],
    )

    achados = list(dimensao_em_floco_de_neve(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimProduct"]
    assert achados[0].id_regra == "MOD-006"
    assert achados[0].evidencia.detalhe["aponta_para"] == ["DimProductSubcategory"]


def test_mod006_nao_marca_estrela_simples(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey"),
            relacionamento("FactOnlineSales", "CustomerKey", "DimCustomer", "CustomerKey"),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod006_nao_confunde_um_para_um_com_floco_de_neve(ler):
    """Review Focus 2: num um-para-um nenhuma ponta é lado "muitos".

    No P8, `DimGeography → DimCustomer` é um-para-um. Presumir que o lado `from`
    é sempre "muitos" faria a `DimCustomer` aparecer como intermediária de uma
    cadeia que não existe.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("FactOnlineSales", "CustomerKey", "DimCustomer", "CustomerKey"),
            relacionamento("DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                           cardinalidade_origem="one"),
        ],
    )

    assert list(dimensao_em_floco_de_neve(modelo)) == []


def test_mod007_marca_relacionamento_um_para_um(ler):
    modelo = ler(
        tabelas=[
            tabela("DimGeography", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
            tabela("DimCustomer", colunas=[coluna("CustomerKey", tipo_dado="int64")]),
        ],
        relacionamentos=[
            relacionamento("DimGeography", "CustomerKey", "DimCustomer", "CustomerKey",
                           bidirecional=True, cardinalidade_origem="one"),
        ],
    )

    achados = list(relacionamento_um_para_um(modelo))

    assert len(achados) == 1
    assert achados[0].id_regra == "MOD-007"
    assert achados[0].evidencia.tipo_objeto == "relacionamento"
    assert achados[0].evidencia.detalhe["cardinalidade"] == "um-para-um"


def test_mod007_nao_marca_muitos_para_um(ler):
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("StoreKey", tipo_dado="int64")]),
            tabela("DimStore", colunas=[coluna("StoreKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "StoreKey", "DimStore", "StoreKey")],
    )

    assert list(relacionamento_um_para_um(modelo)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_modelagem.py -k "mod006 or mod007" -v`
Expected: FAIL com `ImportError: cannot import name 'dimensao_em_floco_de_neve'`.

- [ ] **Step 3: Write minimal implementation**

Acrescentar a `core/rules/modelagem.py` (e os imports `lado_muitos`, `lado_um`):

```python
@regra(
    id="MOD-006",
    titulo="Dimensão em floco de neve",
    categoria="modelagem",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/star-schema",
    termos_consulta=[
        "snowflake dimension",
        "normalized dimension tables",
        "denormalize into single table",
        "relationship filter propagation chain",
    ],
    recomendacao_padrao=(
        "Avalie consolidar as tabelas da dimensão numa só. Em geral os benefícios de "
        "uma única tabela superam os de várias: o modelo carrega menos tabelas, o "
        "que é melhor em armazenamento e desempenho; as cadeias de propagação de "
        "filtro ficam mais curtas; o painel de dados apresenta menos tabelas a quem "
        "cria o relatório; e passa a ser possível criar uma hierarquia que atravesse "
        "os níveis da dimensão, o que não se faz com colunas de tabelas diferentes. "
        "O floco de neve pode ser escolha deliberada, por exemplo quando a origem "
        "dos dados já é normalizada — o custo é o acima."
    ),
)
def dimensao_em_floco_de_neve(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por tabela que é lado "um" de um relacionamento e lado
    "muitos" de outro: a intermediária de uma cadeia dimensão-para-dimensão.

    Os lados saem da cardinalidade, nunca de `from`/`to`. Num um-para-um
    nenhuma das pontas é lado "muitos", então ele não forma cadeia.
    """
    relacionamentos = relacionamentos_em_escopo(modelo)
    um: set[str] = set()
    muitos: set[str] = set()
    for r in relacionamentos:
        um |= lado_um(r)
        muitos |= lado_muitos(r)

    for nome in sorted(um & muitos):
        aponta_para = sorted(
            {
                destino
                for r in relacionamentos
                if nome in lado_muitos(r)
                for destino in lado_um(r)
            }
        )
        recebe_de = sorted(
            {
                origem
                for r in relacionamentos
                if nome in lado_um(r)
                for origem in lado_muitos(r)
            }
        )
        yield Achado(
            id_regra="MOD-006",
            evidencia=Evidencia(
                tipo_objeto="tabela",
                objeto=nome,
                tabela=nome,
                detalhe={"aponta_para": aponta_para, "recebe_de": recebe_de},
            ),
            mensagem=(
                f"A tabela '{nome}' é filtrada por {', '.join(recebe_de)} e filtra "
                f"{', '.join(aponta_para)}: é o elo intermediário de uma dimensão "
                "em floco de neve."
            ),
        )


@regra(
    id="MOD-007",
    titulo="Relacionamento um-para-um",
    categoria="modelagem",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/relationships-one-to-one",
    termos_consulta=[
        "one-to-one relationship guidance",
        "row data spans across tables",
        "merge queries consolidate tables",
        "degenerate dimension",
    ],
    recomendacao_padrao=(
        "Quando os dados de uma mesma entidade estão repartidos em duas tabelas, "
        "evite o relacionamento um-para-um e consolide as duas numa só: mescle as "
        "consultas no Power Query com junção externa à esquerda, desabilite a carga "
        "da segunda consulta, substitua os valores ausentes por um valor explícito e "
        "crie as hierarquias cabíveis. Manter as duas tabelas gera excesso de tabelas "
        "no painel de dados, dificulta encontrar campos relacionados, impede "
        "hierarquias entre níveis e produz resultados inesperados quando as linhas "
        "não casam exatamente. Se quiser preservar a organização dos campos, use "
        "pastas de exibição em vez de tabelas separadas. Há um cenário legítimo: a "
        "dimensão degenerada, derivada de uma tabela de fatos para separar as colunas "
        "usadas em filtro e agrupamento das usadas em soma."
    ),
    nota_de_verificacao=(
        "Todo relacionamento um-para-um é obrigatoriamente bidirecional — não é "
        "possível configurar de outro jeito —, por isso MOD-002 o exclui e o achado "
        "pertence a esta regra."
    ),
)
def relacionamento_um_para_um(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por relacionamento com cardinalidade "um" nas duas pontas."""
    for r in relacionamentos_em_escopo(modelo):
        if not um_para_um(r):
            continue
        yield Achado(
            id_regra="MOD-007",
            evidencia=Evidencia(
                tipo_objeto="relacionamento",
                objeto=_nome_do_relacionamento(r),
                tabela=r.tabela_origem,
                detalhe={
                    "cardinalidade": "um-para-um",
                    "crossFilteringBehavior": r.bruto.get("crossFilteringBehavior"),
                },
            ),
            mensagem=(
                f"O relacionamento {_nome_do_relacionamento(r)} é um-para-um: as "
                "duas tabelas descrevem a mesma entidade."
            ),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_modelagem.py -v`
Expected: PASS, 19 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/modelagem.py tests/test_rules_modelagem.py
git commit -m "feat(rules): MOD-006 floco de neve e MOD-007 um-para-um

As duas leem a cardinalidade, nunca presumem que o lado from e o
muitos. Num um-para-um nenhuma ponta e lado muitos, logo ele nao forma
cadeia de floco de neve: e achado proprio, com a recomendacao que a
documentacao de fato da, que e consolidar as duas tabelas."
```

---

### Task 9: PERF-001 e PERF-003

**Files:**
- Create: `core/rules/performance.py`
- Test: `tests/test_rules_performance.py`

**Interfaces:**
- Consumes: `escopo.{tabelas_em_escopo, coluna_gerada_por_analise, dimensao_de_data}`.
- Produces: funções `coluna_calculada_em_dax` e `ponto_flutuante_somado`, registradas como `PERF-001` e `PERF-003`.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_performance.py`:

```python
"""As regras de performance estática.

PERF-001 tem a exclusão mais importante do conjunto: a documentação que a
sustenta recomenda explicitamente colunas calculadas numa tabela de data em DAX.
Seis dos sete achados que a regra produzia no P8 eram padrão recomendado.
"""

from core.rules.performance import coluna_calculada_em_dax, ponto_flutuante_somado
from conftest import coluna, relacionamento, tabela


def test_perf001_marca_coluna_calculada_em_dax(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimEmployee",
                colunas=[
                    coluna("Base", tipo_dado="decimal", resumir_por="sum"),
                    coluna("Salário", tipo="calculated", tipo_dado="decimal",
                           expressao="[Base] * 1.1", resumir_por="sum"),
                ],
            )
        ]
    )

    achados = list(coluna_calculada_em_dax(modelo))

    assert [a.evidencia.objeto for a in achados] == ["DimEmployee[Salário]"]
    assert achados[0].id_regra == "PERF-001"
    assert achados[0].evidencia.tipo_objeto == "coluna"
    assert achados[0].evidencia.tabela == "DimEmployee"
    assert achados[0].evidencia.trecho == "[Base] * 1.1"


def test_perf001_ignora_coluna_da_dimensao_de_data(ler):
    """A página de tempo automático recomenda exatamente isto.

    "You can then add calculated columns to support the known time filtering and
    grouping requirements." Marcar essas colunas seria produzir um achado que a
    fonte citada refuta.
    """
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela(
                "DimCalendar",
                colunas=[
                    coluna("Data", tipo_dado="dateTime"),
                    coluna("Ano", tipo="calculated", expressao="YEAR([Data])"),
                    coluna("Trimestre", tipo="calculated", expressao='"T" & QUARTER([Data])'),
                ],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf001_ignora_coluna_de_agrupamento_ou_cluster(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "DimCustomer",
                colunas=[
                    coluna("Faixa de Renda", tipo="calculated", expressao="SWITCH(...)",
                           annotations={"GroupingDesignState": "{}"}),
                ],
            )
        ]
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf001_ignora_coluna_de_tabela_calculada(ler):
    """`calculatedTableColumn` é coluna de tabela calculada, não coluna em DAX."""
    modelo = ler(
        tabelas=[
            tabela(
                "Tabela",
                colunas=[
                    coluna("Coluna", tipo="calculatedTableColumn", tipo_dado="int64"),
                    coluna("Normal", tipo_dado="string"),
                ],
            )
        ]
    )

    assert list(coluna_calculada_em_dax(modelo)) == []


def test_perf003_marca_ponto_flutuante_somado(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "Previsões",
                colunas=[
                    coluna("Previsao", tipo_dado="double", resumir_por="sum"),
                    coluna("Fator", tipo_dado="double", resumir_por="none"),
                    coluna("Valor", tipo_dado="decimal", resumir_por="sum"),
                ],
            )
        ]
    )

    achados = list(ponto_flutuante_somado(modelo))

    assert [a.evidencia.objeto for a in achados] == ["Previsões[Previsao]"]
    assert achados[0].id_regra == "PERF-003"
    assert achados[0].evidencia.detalhe == {"dataType": "double", "summarizeBy": "sum"}


def test_perf003_ignora_tabela_fora_de_escopo(ler):
    modelo = ler(
        tabelas=[
            tabela(
                "ClusterMappingTable",
                colunas=[coluna("Previsao", tipo_dado="double", resumir_por="sum")],
                annotations={"ClusterMappingTable": "1"},
            )
        ]
    )

    assert list(ponto_flutuante_somado(modelo)) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_performance.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.performance'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/performance.py`:

```python
"""Regras de performance estática.

Estática porque lê o modelo, não a execução: nada de VertiPaq, DAX Studio ou
XMLA (F23, Trabalhos Futuros). O que se afirma aqui é o que o `model.bim`
sustenta.
"""

from collections.abc import Iterator

from core.model import ModeloSemantico
from core.rules.base import Achado, Evidencia
from core.rules.escopo import (
    coluna_gerada_por_analise,
    dimensao_de_data,
    tabelas_em_escopo,
)
from core.rules.registry import regra


@regra(
    id="PERF-001",
    titulo="Coluna calculada em DAX",
    categoria="performance",
    severidade="media",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction",
    termos_consulta=[
        "preference for custom columns",
        "calculated column versus Power Query computed column",
        "VertiPaq compression calculated columns",
        "data refresh time model size",
    ],
    recomendacao_padrao=(
        "Prefira criar a coluna no Power Query, ou na origem dos dados. O mecanismo "
        "VertiPaq armazena a coluna calculada em DAX como qualquer outra, mas em "
        "estruturas internas que normalmente comprimem menos, e que são construídas "
        "depois de carregadas todas as consultas do Power Query — o que estende o "
        "tempo de atualização. Quando a origem é um banco, o cálculo pode ir para a "
        "consulta SQL ou ser materializado como coluna na origem. Há exceções "
        "legítimas: a coluna calculada em DAX é a melhor escolha quando a fórmula "
        "avalia medidas ou exige funcionalidade que só existe em DAX, como as funções "
        "de hierarquia pai-filho."
    ),
)
def coluna_calculada_em_dax(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por coluna com `type: calculated`.

    Duas exclusões, ambas pelo princípio de auditar o que o autor escreveu: as
    colunas de agrupamento e cluster, cujo DAX é escrito pela interface, e as
    colunas da dimensão de data — a documentação recomenda acrescentá-las a uma
    tabela de data construída em DAX.
    """
    dimensoes_de_data = dimensao_de_data(modelo)

    for t in tabelas_em_escopo(modelo):
        if t.nome in dimensoes_de_data:
            continue
        for c in t.colunas:
            if c.tipo != "calculated" or coluna_gerada_por_analise(c):
                continue
            yield Achado(
                id_regra="PERF-001",
                evidencia=Evidencia(
                    tipo_objeto="coluna",
                    objeto=f"{t.nome}[{c.nome}]",
                    tabela=t.nome,
                    trecho=c.expressao,
                    detalhe={"type": c.tipo, "dataType": c.tipo_dado},
                ),
                mensagem=(
                    f"A coluna '{c.nome}' da tabela '{t.nome}' é calculada em DAX."
                ),
            )


@regra(
    id="PERF-003",
    titulo="Coluna de ponto flutuante somada",
    categoria="performance",
    severidade="baixa",
    url_canonica="https://learn.microsoft.com/en-us/power-bi/connect-data/desktop-data-types",
    termos_consulta=[
        "decimal number floating point imprecision",
        "fixed decimal number data type",
        "accuracy of number type calculations",
        "sum unexpected results",
    ],
    recomendacao_padrao=(
        "Avalie trocar o tipo da coluna de Número decimal para Número decimal fixo ou "
        "Número inteiro. O Número decimal é armazenado como ponto flutuante conforme o "
        "padrão IEEE 754, isto é, de forma aproximada, com precisão de até 15 dígitos. "
        "Raramente, somar os valores de uma coluna desse tipo devolve resultado "
        "inesperado; o caso mais provável é a coluna ter muitos valores positivos e "
        "negativos, porque o resultado passa a depender da distribuição das linhas. "
        "Comparações de igualdade também podem surpreender, o que fica evidente em "
        "expressões com RANKX. O Número decimal fixo tem precisão maior, com quatro "
        "dígitos fixos à direita do separador decimal."
    ),
)
def ponto_flutuante_somado(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por coluna `double` com agregação implícita de soma."""
    for t in tabelas_em_escopo(modelo):
        for c in t.colunas:
            if c.tipo_dado != "double" or c.resumir_por != "sum":
                continue
            yield Achado(
                id_regra="PERF-003",
                evidencia=Evidencia(
                    tipo_objeto="coluna",
                    objeto=f"{t.nome}[{c.nome}]",
                    tabela=t.nome,
                    detalhe={"dataType": "double", "summarizeBy": "sum"},
                ),
                mensagem=(
                    f"A coluna '{c.nome}' da tabela '{t.nome}' é de ponto flutuante e "
                    "é somada por padrão."
                ),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_performance.py -v`
Expected: PASS, 6 testes.

- [ ] **Step 5: Commit**

```bash
git add core/rules/performance.py tests/test_rules_performance.py
git commit -m "feat(rules): PERF-001 e PERF-003

PERF-001 exclui a dimensao de data: a pagina de tempo automatico
recomenda explicitamente acrescentar colunas calculadas a uma tabela de
data em DAX, e seis dos sete achados da regra no P8 eram esse padrao
recomendado. As duas recomendacoes trazem as excecoes da propria fonte."
```

---

### Task 10: Carga das regras e catálogo

**Files:**
- Create: `core/rules/todas.py`
- Create: `core/rules/catalogo.py`
- Test: `tests/test_rules_catalogo.py`

**Interfaces:**
- Consumes: `REGISTRO`, os módulos `modelagem` e `performance`, `runner.avaliar`.
- Produces: `core.rules.todas.REGISTRO` (global, já populado); `core.rules.catalogo.{IDS_ESPERADOS, como_markdown() -> str, main() -> None}`.

- [ ] **Step 1: Write the failing test**

Criar `tests/test_rules_catalogo.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules_catalogo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'core.rules.catalogo'`.

- [ ] **Step 3: Write minimal implementation**

Criar `core/rules/todas.py`:

```python
"""Carrega todas as regras, populando o registro global.

Importar este módulo é o que faz as regras existirem para o `runner`. Sem ele o
`REGISTRO` fica vazio — e isso é deliberado, para que os testes do motor usem
registros isolados sem depender da ordem de importação.
"""

from core.rules import modelagem, performance  # noqa: F401 — o import registra
from core.rules.registry import REGISTRO

__all__ = ["REGISTRO"]
```

Criar `core/rules/catalogo.py`:

```python
"""O catálogo de regras, em Markdown.

`python -m core.rules.catalogo` imprime a tabela que vai ao capítulo de
metodologia. Gerar em vez de manter à mão elimina a divergência entre o que o
código faz e o que a monografia diz que ele faz.

As URLs canónicas daqui são também as páginas que a base RAG precisa conter
(G-8, semana 5): o catálogo de regras alimenta o catálogo de fontes.
"""

from core.rules.todas import REGISTRO

IDS_ESPERADOS = [
    "MOD-001",
    "MOD-002",
    "MOD-003",
    "MOD-005",
    "MOD-006",
    "MOD-007",
    "PERF-001",
    "PERF-003",
]
"""As regras desta etapa. Um teste compara com o registro: regra acrescentada
sem atualizar esta lista falha a suíte, de propósito."""

CABECALHO = (
    "| ID | Regra | Categoria | Severidade | Fonte |\n"
    "|---|---|---|---|---|"
)


def como_markdown() -> str:
    """O catálogo como tabela Markdown, uma linha por regra."""
    linhas = [CABECALHO]
    for meta in REGISTRO.metas():
        nota = " (nota)" if meta.nota_de_verificacao else ""
        linhas.append(
            f"| {meta.id} | {meta.titulo}{nota} | {meta.categoria} | "
            f"{meta.severidade} | <{meta.url_canonica}> |"
        )
    linhas.append("")
    linhas.append(f"{len(REGISTRO)} regras. (nota) = tem nota de verificação.")
    return "\n".join(linhas)


def main() -> None:
    print(como_markdown())
    for meta in REGISTRO.metas():
        if meta.nota_de_verificacao:
            print(f"\n**{meta.id} — nota de verificação:** {meta.nota_de_verificacao}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules_catalogo.py -v`
Expected: PASS, 5 testes.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: PASS. Soma esperada: 17 (Tasks 1 e anteriores) + 11 + 4 + 16 + 4 + 19 + 6 + 5 = 82 testes, com os 4 do P8 pulados se `data/` não existir.

- [ ] **Step 6: Commit**

```bash
git add core/rules/todas.py core/rules/catalogo.py tests/test_rules_catalogo.py
git commit -m "feat(rules): carga das regras e catalogo em markdown

python -m core.rules.catalogo imprime a tabela que vai ao capitulo de
metodologia, gerada em vez de mantida a mao. O teste de completude faz
valer a decisao D-7, e as URLs canonicas alimentam o sources.yaml da
semana 5."
```

---

### Task 11: Regressão contra o PBIP real (P8)

**Files:**
- Modify: `tests/test_pbip_real.py`

**Interfaces:**
- Consumes: `core.rules.todas.REGISTRO`, `core.rules.runner.avaliar`, e a fixture `modelo` que já existe no arquivo.
- Produces: nada para tarefas seguintes.

- [ ] **Step 1: Write the failing test**

Acrescentar a `tests/test_pbip_real.py`, junto aos imports:

```python
from collections import Counter

from core.rules.runner import avaliar
from core.rules.todas import REGISTRO
```

E ao fim do arquivo:

```python
ESPERADO_P8 = {
    "MOD-001": 4,  # 1 DateTableTemplate + 3 LocalDateTable
    "MOD-002": 3,  # 4 bidirecionais, menos o um-para-um que MOD-007 assume
    "MOD-003": 2,  # DimEmployee e Tabela de Regressão Linear
    "MOD-005": 1,  # DimCalendar, dimensão de data sem dataCategory
    "MOD-006": 2,  # DimProduct e DimProductSubcategory
    "MOD-007": 1,  # DimGeography → DimCustomer
    "PERF-001": 1,  # DimEmployee[Salário]
    "PERF-003": 1,  # Tabela de Regressão Linear[Previsao]
}


@pytest.fixture(scope="module")
def resultado(modelo):
    return avaliar(modelo, registro=REGISTRO)


def test_as_oito_regras_rodam_sem_falhar_no_pbip_real(resultado):
    assert resultado.regras_com_falha == []
    assert resultado.regras_executadas == 8


def test_as_contagens_por_regra_no_p8(resultado):
    """Trava o rendimento medido em 06/10/2026.

    Se uma mudança futura fizer PERF-001 saltar de 1 para 35, ou MOD-005 de 1
    para 4, as exclusões de escopo quebraram — e é aqui que isso aparece.
    """
    assert Counter(a.id_regra for a in resultado.achados) == Counter(ESPERADO_P8)
    assert len(resultado.achados) == 15


def test_os_objetos_apontados_sao_os_esperados(resultado):
    por_regra: dict[str, list[str]] = {}
    for a in resultado.achados:
        por_regra.setdefault(a.id_regra, []).append(a.evidencia.objeto)

    assert por_regra["MOD-005"] == ["DimCalendar"]
    assert sorted(por_regra["MOD-006"]) == ["DimProduct", "DimProductSubcategory"]
    assert por_regra["PERF-001"] == ["DimEmployee[Salário]"]
    assert por_regra["PERF-003"] == ["Tabela de Regressão Linear[Previsao]"]
    assert "DimGeography[CustomerKey]" in por_regra["MOD-007"][0]
    assert sorted(por_regra["MOD-003"]) == ["DimEmployee", "Tabela de Regressão Linear"]


def test_a_cadeia_causal_do_estudo_de_caso_aparece_nos_achados(resultado):
    """A DimCalendar não marcada é a causa de uma das tabelas automáticas."""

    def objetos_de(id_regra: str) -> set[str]:
        return {a.evidencia.objeto for a in resultado.achados if a.id_regra == id_regra}

    automaticas = objetos_de("MOD-001")

    assert objetos_de("MOD-005") == {"DimCalendar"}
    assert len(automaticas) == 4
    assert all(n.startswith(("DateTableTemplate_", "LocalDateTable_")) for n in automaticas)


def test_a_saida_vem_ordenada_por_severidade(resultado):
    severidades = [REGISTRO.meta(a.id_regra).severidade for a in resultado.achados]
    ordem = {"alta": 0, "media": 1, "baixa": 2}

    assert severidades == sorted(severidades, key=lambda s: ordem[s])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pbip_real.py -v`
Expected: FAIL se `data/pbip/P8_contoso-vendas` existir. Se os testes aparecerem como SKIPPED, o PBIP não está na máquina — nesse caso **pare e avise**: esta tarefa não pode ser verificada sem ele, e as contagens são o critério de aceite nº 3.

- [ ] **Step 3: Rodar e conferir as contagens**

Run: `pytest tests/test_pbip_real.py -v`
Expected: PASS, 9 testes (4 antigos + 5 novos).

Se alguma contagem divergir, **não ajuste o número esperado**. Investigue a regra: as contagens de `ESPERADO_P8` foram medidas no `model.bim` do P8 em 06/10/2026 e constam da spec, seção 4. Divergência significa que a implementação não corresponde ao que foi medido — ou que o `model.bim` em `data/` mudou, o que precisa ser registrado antes de qualquer coisa.

- [ ] **Step 4: Commit**

```bash
git add tests/test_pbip_real.py
git commit -m "test(fase2): regressao das oito regras contra o PBIP real

Trava as 15 ocorrencias medidas no P8 em 06/10/2026, regra por regra e
objeto por objeto, mais a ordenacao por severidade. Se as exclusoes de
escopo quebrarem, PERF-001 salta de 1 para 35 e o teste acusa."
```

---

### Task 12: Documentação

**Files:**
- Modify: `docs/project/progress-log.md`
- Modify: `README.md`

`docs/project/backlog.md` e `docs/project/riscos.md` **já foram atualizados** em 06/10/2026, no commit do design (`c214376`): o critério de âncora verificada, as candidatas registradas e a revisão do R-12 estão lá. Não repita esse conteúdo.

**Interfaces:**
- Consumes: o resultado de todas as tarefas anteriores.
- Produces: nada.

- [ ] **Step 1: Conferir os números que vão para a documentação**

Run: `pytest -q`
Run: `python -m core.rules.catalogo`

Anote o total de testes e confira que o catálogo imprime as 8 regras. Os números da documentação são os que saírem daqui, não os deste plano.

- [ ] **Step 2: Acrescentar a entrada no `progress-log.md`**

Acrescentar ao fim do arquivo, com o total real de testes no lugar de `<N>`:

```markdown
## 06/10/2026 — Fase 2, semana 4 — motor de regras e as oito regras estruturais

Segundo bloco de código de produto, em TDD. **<N> testes passando.**

**O trabalho que mais rendeu não foi o código.** Antes de implementar, cada regra
teve a âncora conferida no Microsoft Learn. Isso eliminou três das oito regras
propostas e mudou uma quarta:

- **PERF-004** (tabela calculada em DAX) caiu porque a página que a sustentaria
  **recomenda** tabelas de data em `CALENDAR`/`CALENDARAUTO`. Em P8 seu único
  achado era a `DimCalendar`: 100% do que a regra produzia seria refutado pela
  fonte citada.
- **PERF-002** (coluna-chave agregável) caiu por falta de passagem citável. A
  frase próxima no Learn é contextual a outro exemplo, e a origem da regra era o
  BPA do Tabular Editor, recusado em 22/09 por licença (R-10). Os 5 objetos que
  ela apontava voltam no backlog como candidata "coluna sem uso".
- **MOD-004** (relacionamento entre tipos diferentes) caiu sem âncora e com
  dúvida sobre o produto permitir criar a condição.
- **PERF-001** passou a excluir a dimensão de data: 6 dos seus 7 achados em P8
  eram as colunas de calendário da `DimCalendar`, que a documentação recomenda
  acrescentar.

Entraram três regras com passagem verbatim: **MOD-005** (dimensão de data não
marcada), **MOD-006** (dimensão em floco de neve) e **MOD-007** (relacionamento
um-para-um). A regra passou a constar do `backlog.md`: sem passagem citável, a
regra não entra.

**MOD-007 nasceu de um detalhe de cardinalidade.** O P8 tem um relacionamento com
`fromCardinality: "one"` explícito — `DimGeography[CustomerKey] →
DimCustomer[CustomerKey]` é um-para-um. Disso vieram duas correções: ele não é elo
de floco de neve, porque num um-para-um nenhuma ponta é lado "muitos"; e MOD-002
não pode marcá-lo, porque a documentação diz que todo um-para-um é
obrigatoriamente bidirecional — o achado teria recomendação impossível de
cumprir. O problema real é o um-para-um, e MOD-007 o afirma com a recomendação
que a documentação de fato dá.

**O que foi entregue:**
- `core/rules/base.py` — `RegraMeta`, `Evidencia`, `Achado`. O `RegraMeta` se
  recusa a existir sem URL canónica, termos de consulta e recomendação padrão
  com texto real. O achado carrega só a ocorrência: o catálogo é fonte única.
- `core/rules/registry.py` — decorador `@regra` e registro; ID duplicado é erro
  na importação.
- `core/rules/escopo.py` — as exclusões, sob um princípio: auditar o que o autor
  escreveu. Tabelas de data automáticas, tabelas só de medidas, parâmetros
  hipotéticos, tabelas de cluster e colunas de agrupamento ficam fora, cada uma
  por predicado em TMSL e nenhuma por nome de objeto.
- `core/rules/modelagem.py` e `performance.py` — as oito regras.
- `core/rules/runner.py` — ordem estável (severidade, ID, objeto) e isolamento
  de erro por regra, com `regras_com_falha` no resultado.
- `core/rules/catalogo.py` — `python -m core.rules.catalogo` imprime a tabela de
  regras da monografia. As URLs canónicas são também as fontes que a RAG precisa
  conter (G-8).

**Validação contra o P8:** 15 achados, com as contagens travadas em teste —
MOD-001: 4, MOD-002: 3, MOD-003: 2, MOD-005: 1, MOD-006: 2, MOD-007: 1,
PERF-001: 1, PERF-003: 1. As regras encadeiam uma causa, e não só listam
sintomas: a `DimCalendar` nunca foi marcada como tabela de data, então o Power BI
gerou uma tabela de data local para a própria `DimCalendar[Data]`.

**Correção no modelo interno:** o parser passou a normalizar a cardinalidade do
relacionamento (`one`/`many` → `um`/`muitos`), que antes misturava os dois
vocabulários, e a expor `type`, `summarizeBy`, `dataCategory` e `source.type`.

- **Pendência:** confirmar empiricamente que a marcação de tabela de data aparece
  como `dataCategory: "Time"` no TMSL — marcar a `DimCalendar` no Desktop, salvar
  o PBIP e comparar o `model.bim`. A regra está no catálogo com nota de
  verificação até lá.
- **Atenção ao R-12:** o conjunto rende 15 achados no P8, um modelo visivelmente
  problemático. O gatilho da semana 4 é "menos de ~40 achados em P1–P7". Rodar as
  oito regras sobre P1–P7 assim que os PBIP existirem deixou de ser tarefa da
  semana 8.
- **Próximo passo:** as regras de DAX por padrão textual (grupo 2 do critério de
  detectabilidade), sobre o motor já provado.
```

- [ ] **Step 3: Atualizar o `README.md`**

Na tabela de estado, trocar a linha da Fase 2 por:

```markdown
| **Fase 2 — Leitura do PBIP e regras** | Semanas 3–4 | **Em andamento** — ingestão, parser e motor de regras com 8 regras estruturais (06/10/2026) |
```

E substituir o parágrafo "Já implementado: …" por:

```markdown
Já implementado: ingestão de PBIP (pasta ou `.zip`) com validação de estrutura, parser do `model.bim` para um modelo interno normalizado, e o motor de regras determinísticas com as 8 primeiras regras estruturais — 15 achados no PBIP real usado como estudo de caso. <N> testes passando.

Cada regra declara a página do Microsoft Learn que a sustenta, e `python -m core.rules.catalogo` imprime o catálogo. Regra sem essa âncora não entra no registro: a verificação das fontes antes de escrever código eliminou três das oito regras originalmente propostas, uma delas porque a página que a sustentaria recomendava justamente o que a regra marcaria como defeito.
```

- [ ] **Step 4: Rodar a suíte uma última vez**

Run: `pytest -q`
Expected: PASS. Conferir que o `<N>` escrito nos dois arquivos é o número real.

- [ ] **Step 5: Commit**

```bash
git add docs/project/progress-log.md README.md
git commit -m "docs(fase2): registra o motor de regras e as oito regras

O progress-log guarda o que a verificacao de ancoras custou e rendeu:
tres regras eliminadas, uma corrigida, tres novas com passagem verbatim,
e MOD-007 nascida de um fromCardinality one no P8."
```
