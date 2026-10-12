# Correção da MOD-003 e da PERF-001 — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tirar da MOD-003 os grupos de cálculo e os parâmetros de campo, estreitar a exclusão da PERF-001 à tabela de data calculada em DAX e medir de novo contra o mesmo gabarito, num arquivo separado do resultado oficial.

**Architecture:** três predicados estruturais novos em `core/rules/escopo.py` (a casa única das exclusões), consumidos por `fora_de_escopo`, `dax_escrito_pela_ferramenta` e pela PERF-001. O comando `python -m gabarito medir` ganha `--rotulo`. O conjunto da recuperação é regerado porque deriva dos achados.

**Tech Stack:** Python 3.11, Pydantic 2, pytest.

**Spec:** `docs/superpowers/specs/2026-10-12-correcao-mod003-perf001-design.md`

## Global Constraints

- Tudo em português do Brasil: código, nomes, testes, mensagens, commits.
- Nenhuma exclusão por nome de objeto: só sinais estruturais do TMSL (`calculationGroup`, `extendedProperties[].name == "ParameterMetadata"` com `value.kind == 2`, partição `tipo_origem == "calculated"`).
- Grupo de cálculo: fora de `tabelas_em_escopo`, **dentro** de `tabelas_com_dax_do_autor`. Parâmetro de campo: fora dos dois.
- DAX-001 não muda.
- `eval/results/regras-2026-10-12.json` (resultado oficial, tag `regras-gt`) **não pode ser sobrescrito**; a medição nova vai para `regras-<data>-pos-correcao.json`.
- `eval/ground_truth.csv` não muda nesta etapa.
- Saída de console em ASCII.
- Testes: `.\.venv\Scripts\python.exe -m pytest -q` na raiz; os de `data/` são pulados sem a pasta.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push autorizado na branch `fase3-correcao-regras`.

## Review Focus

- **`extendedProperties` ou `value` malformados** (`null`, lista com item que não é dicionário, `value` string) — o predicado devolve `False`, sem `TypeError` derrubando `fora_de_escopo` e com ele todas as regras (teste na Tarefa 1).
- **`calculationGroup: null`** num `model.bim` editado à mão — não é grupo de cálculo (teste na Tarefa 1).
- **Parâmetro hipotético com `ParameterMetadata` sem `kind`** (o `Parâmetro` do P8) — não vira parâmetro de campo; continua fora de escopo pelo `GENERATESERIES` e continua com o DAX tratado como da ferramenta (teste na Tarefa 1).
- **Dimensão de data calculada com `ADDCOLUMNS(CALENDAR(...))`** — continua excluída da PERF-001, porque o critério é a partição ser calculada, não a primeira função (teste na Tarefa 2).
- **`--rotulo` com separador de caminho** (`../fora`) — recusado com código 1, nada gravado fora de `eval/results/` (teste na Tarefa 3).

---

### Task 1: MOD-003 — grupo de cálculo e parâmetro de campo fora de escopo

**Files:**
- Modify: `core/rules/escopo.py` (constantes no topo; predicados novos antes de `fora_de_escopo`; `fora_de_escopo`; `dax_escrito_pela_ferramenta`)
- Modify: `core/rules/modelagem.py` (`nota_de_verificacao` da MOD-003)
- Test: `tests/test_rules_escopo.py`, `tests/test_rules_modelagem.py` (acrescentar)

**Interfaces:**
- Consumes: `Tabela` (`core.model`), com `bruto: dict` e `colunas` (cada `Coluna` com `bruto: dict`).
- Produces: `grupo_de_calculo(t: Tabela) -> bool`; `tabela_de_parametro_de_campo(t: Tabela) -> bool`; constantes `PROPRIEDADE_GRUPO_DE_CALCULO = "calculationGroup"`, `METADADO_DE_PARAMETRO = "ParameterMetadata"`, `TIPO_PARAMETRO_DE_CAMPO = 2`.

- [ ] **Step 1: Escrever os testes de escopo que falham**

Em `tests/test_rules_escopo.py`, acrescentar `grupo_de_calculo` e `tabela_de_parametro_de_campo` ao `from core.rules.escopo import (...)` (ordem alfabética) e, ao fim do arquivo:

```python
def _grupo_de_calculo(nome: str, valor=None) -> dict:
    t = tabela(nome, colunas=[coluna(nome)])
    t["calculationGroup"] = valor if valor is not None else {
        "calculationItems": [
            {"name": "YTD", "expression": "CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))"}
        ]
    }
    return t


def _parametro_de_campo(nome: str, propriedades) -> dict:
    campos = coluna("Parameter Fields", tipo="calculatedTableColumn")
    campos["extendedProperties"] = propriedades
    return tabela(
        nome,
        colunas=[coluna(nome, tipo="calculatedTableColumn"), campos],
        particoes=[particao(tipo="calculated", expressao="{ (\"Area\", NAMEOF('Area'[Area]), 0) }")],
    )


METADADO_DE_CAMPO = [{"name": "ParameterMetadata", "type": "json", "value": {"kind": 2, "version": 3}}]


def test_grupo_de_calculo_fica_fora_de_escopo_mas_o_dax_e_do_autor(ler):
    """Como `Date Role` e `Time Intelligence` do P1: sem relacionamento por natureza,
    mas o DAX dos itens de cálculo é escrito pelo autor."""
    t = ler(tabelas=[_grupo_de_calculo("Time Intelligence")]).tabelas[0]
    assert grupo_de_calculo(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is False


def test_calculation_group_nulo_nao_e_grupo_de_calculo(ler):
    t = tabela("Editada", colunas=[coluna("A")])
    t["calculationGroup"] = None
    assert grupo_de_calculo(ler(tabelas=[t]).tabelas[0]) is False


def test_parametro_de_campo_fica_fora_de_escopo_e_o_dax_e_da_ferramenta(ler):
    """Como os dois `Toggle…` do P2: as tuplas NAMEOF são escritas pelo Desktop."""
    t = ler(tabelas=[_parametro_de_campo("Toggle", METADADO_DE_CAMPO)]).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is True
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is True


def test_parametro_hipotetico_com_metadado_sem_kind_nao_e_parametro_de_campo(ler):
    """O `Parâmetro` do P8 tem ParameterMetadata `{"version": 0}`: é parâmetro
    hipotético, já excluído pelo GENERATESERIES."""
    coluna_parametro = coluna("Parâmetro", tipo="calculatedTableColumn", tipo_dado="double")
    coluna_parametro["extendedProperties"] = [{"name": "ParameterMetadata", "type": "json", "value": {"version": 0}}]
    t = ler(
        tabelas=[
            tabela(
                "Parâmetro",
                colunas=[coluna_parametro],
                particoes=[particao(tipo="calculated", expressao="GENERATESERIES(0, 1, 0.05)")],
            )
        ]
    ).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is False
    assert fora_de_escopo(t) is True
    assert dax_escrito_pela_ferramenta(t) is True


@pytest.mark.parametrize(
    "propriedades",
    [
        None,
        [],
        ["ParameterMetadata"],
        [{"name": "ParameterMetadata", "value": "kind=2"}],
        [{"name": "ParameterMetadata", "value": {"kind": 1}}],
        [{"name": "Outra", "value": {"kind": 2}}],
    ],
)
def test_extended_properties_malformadas_ou_de_outro_tipo_nao_sao_parametro_de_campo(ler, propriedades):
    t = ler(tabelas=[_parametro_de_campo("Tabela", propriedades)]).tabelas[0]
    assert tabela_de_parametro_de_campo(t) is False


def test_tabela_comum_nao_e_grupo_nem_parametro(ler):
    t = ler(tabelas=[tabela("DimProduto", colunas=[coluna("Nome")])]).tabelas[0]
    assert grupo_de_calculo(t) is False
    assert tabela_de_parametro_de_campo(t) is False
    assert fora_de_escopo(t) is False
```

Se `pytest` ainda não estiver importado em `tests/test_rules_escopo.py`, acrescentar `import pytest` no topo.

- [ ] **Step 2: Escrever o teste da MOD-003 que falha**

Em `tests/test_rules_modelagem.py`, ao fim do arquivo:

```python
def test_mod003_ignora_grupo_de_calculo_e_parametro_de_campo_mas_marca_tabela_comum(ler):
    """Os 4 falsos positivos estruturais do gabarito (P1 e P2); a tabela comum isolada
    continua sendo achado."""
    grupo = tabela("Time Intelligence", colunas=[coluna("Time Intelligence")])
    grupo["calculationGroup"] = {"calculationItems": [{"name": "YTD", "expression": "SELECTEDMEASURE()"}]}
    campos = coluna("Parameter Fields", tipo="calculatedTableColumn")
    campos["extendedProperties"] = [{"name": "ParameterMetadata", "type": "json", "value": {"kind": 2, "version": 3}}]
    parametro = tabela(
        "Toggle for breakdown",
        colunas=[coluna("Breakdown by", tipo="calculatedTableColumn"), campos],
        particoes=[particao(tipo="calculated", expressao="{ (\"Area\", NAMEOF('Area'[Area]), 0) }")],
    )
    modelo = ler(tabelas=[grupo, parametro, tabela("Supply Analytics", colunas=[coluna("Valor", tipo_dado="double")])])

    assert [a.evidencia.objeto for a in tabela_sem_relacionamento(modelo)] == ["Supply Analytics"]
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rules_escopo.py tests/test_rules_modelagem.py -q`
Expected: erro de coleta em `test_rules_escopo.py` — `ImportError: cannot import name 'grupo_de_calculo'`; rodando só `tests/test_rules_modelagem.py`, o teste novo falha com a lista contendo também `Time Intelligence` e `Toggle for breakdown`.

- [ ] **Step 4: Implementar em `core/rules/escopo.py`**

Abaixo de `FUNCAO_TABELA_DE_DATA` e da docstring dela, acrescentar:

```python
PROPRIEDADE_GRUPO_DE_CALCULO = "calculationGroup"
METADADO_DE_PARAMETRO = "ParameterMetadata"
TIPO_PARAMETRO_DE_CAMPO = 2
"""O `kind` do `ParameterMetadata` que o Desktop grava no parâmetro de campo. O
parâmetro hipotético também tem `ParameterMetadata`, mas sem `kind`."""
```

Logo antes de `def fora_de_escopo`, acrescentar:

```python
def grupo_de_calculo(t: Tabela) -> bool:
    """Grupo de cálculo: a tabela carrega a propriedade `calculationGroup`.

    Não tem relacionamento por natureza — os itens de cálculo modificam medidas,
    não filtram tabelas. O DAX dos itens é do autor.
    """
    return isinstance(t.bruto.get(PROPRIEDADE_GRUPO_DE_CALCULO), dict)


def tabela_de_parametro_de_campo(t: Tabela) -> bool:
    """Parâmetro de campo: uma coluna com `ParameterMetadata` de `kind` 2.

    Não tem relacionamento por natureza, e a expressão da tabela (tuplas com
    `NAMEOF`) é escrita pelo Desktop. A leitura tolera `extendedProperties`
    malformadas pelo mesmo motivo de `anotacoes`: o predicado roda dentro de
    `fora_de_escopo`, e uma exceção aqui derrubaria todas as regras.
    """
    for c in t.colunas:
        for propriedade in c.bruto.get("extendedProperties") or []:
            if not isinstance(propriedade, dict) or propriedade.get("name") != METADADO_DE_PARAMETRO:
                continue
            valor = propriedade.get("value")
            if isinstance(valor, dict) and valor.get("kind") == TIPO_PARAMETRO_DE_CAMPO:
                return True
    return False
```

Trocar `fora_de_escopo` por:

```python
def fora_de_escopo(t: Tabela) -> bool:
    return (
        tabela_automatica_de_data(t)
        or tabela_apenas_de_medidas(t)
        or tabela_de_parametro_hipotetico(t)
        or tabela_gerada_por_analise(t)
        or grupo_de_calculo(t)
        or tabela_de_parametro_de_campo(t)
    )
```

Em `dax_escrito_pela_ferramenta`, trocar o `return (...)` por:

```python
    return (
        tabela_automatica_de_data(t)
        or tabela_gerada_por_analise(t)
        or tabela_de_parametro_hipotetico(t)
        or tabela_de_parametro_de_campo(t)
    )
```

E, na docstring dela, trocar o item "o DAX é da ferramenta" por:

```
    - **o DAX é da ferramenta** — tabela de data automática, tabela de cluster, a
      tabela de parâmetro hipotético, cuja medida o Desktop escreve junto com
      a tabela (`% Previsao = SELECTEDVALUE(...)`), e o parâmetro de campo, cujas
      tuplas `NAMEOF` o Desktop escreve;
    - **padrão legítimo do autor** — a tabela que só carrega medidas e o grupo de
      cálculo, excluídos apenas por não terem relacionamento por natureza.
```

(substituindo também o item "padrão legítimo do autor" antigo, que mencionava só a tabela de medidas). Na docstring do módulo, trocar a frase "a tabela que só carrega medidas e a tabela de parâmetro hipotético não têm relacionamento por natureza." por "a tabela que só carrega medidas, a de parâmetro hipotético, o parâmetro de campo e o grupo de cálculo não têm relacionamento por natureza."

- [ ] **Step 5: Declarar a limitação na MOD-003 (`core/rules/modelagem.py`)**

Trocar o `nota_de_verificacao` da MOD-003 por:

```python
    nota_de_verificacao=(
        "Âncora geral, não artigo dedicado — é a mais fraca do conjunto. Daí a "
        "severidade baixa. Reavaliar na Fase 3, com o trecho recuperado em mãos. "
        "Pelo gabarito de P1–P7 (12/10/2026), grupo de cálculo e parâmetro de campo "
        "passaram a ficar fora de escopo. Limitação declarada: tabela digitada à mão "
        "só para a apresentação (um logotipo, uma legenda de ícones) continua sendo "
        "marcada — nenhum sinal estrutural a separa de uma dimensão digitada e "
        "esquecida sem relacionamento."
    ),
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rules_escopo.py tests/test_rules_modelagem.py -q`
Expected: todos passam (os 6 testes novos de escopo, contando os 6 parametrizados como 6, e o novo da MOD-003).

- [ ] **Step 7: Suíte e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: só podem falhar `tests/test_rag_avaliacao_real.py` (o conjunto da recuperação muda com os achados — Tarefa 4). Qualquer outra falha é defeito desta tarefa.

```bash
git add core/rules/escopo.py core/rules/modelagem.py tests/test_rules_escopo.py tests/test_rules_modelagem.py
git commit -m "fix(regras): grupo de calculo e parametro de campo fora de escopo (MOD-003)"
```

---

### Task 2: PERF-001 — exclusão só da dimensão de data calculada em DAX

**Files:**
- Modify: `core/rules/escopo.py` (predicado novo `tabela_calculada_em_dax`)
- Modify: `core/rules/performance.py` (`coluna_calculada_em_dax` e `recomendacao_padrao` da PERF-001; import)
- Test: `tests/test_rules_performance.py`, `tests/test_rules_escopo.py`

**Interfaces:**
- Consumes: `dimensao_de_data(modelo) -> set[str]`, `tabelas_em_escopo`, `coluna_gerada_por_analise` (existentes); `Particao.tipo_origem`.
- Produces: `tabela_calculada_em_dax(t: Tabela) -> bool`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_rules_performance.py`, **substituir** `test_perf001_ignora_coluna_da_dimensao_de_data` inteiro por:

```python
def test_perf001_marca_coluna_de_dimensao_de_data_importada(ler):
    """Corrigido em 12/10/2026, pelo gabarito de P1–P7.

    A exceção da documentação vale para a tabela de data **gerada em DAX**: "When
    your data source already defines a date dimension table, use this table […].
    Otherwise, you can generate date tables […] by using the DAX CALENDAR or
    CALENDARAUTO functions. You can then add calculated columns" (auto-date-time).
    Na dimensão importada pelo Power Query, a coluna derivada é caso de Power Query.
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
                particoes=[particao(tipo="m", expressao='let Fonte = Excel.Workbook(File.Contents("d.xlsx")) in Fonte')],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Data")],
    )

    assert [a.evidencia.objeto for a in coluna_calculada_em_dax(modelo)] == ["DimCalendar[Ano]", "DimCalendar[Trimestre]"]


def test_perf001_ignora_coluna_da_dimensao_de_data_calculada_em_dax(ler):
    """A página de tempo automático recomenda exatamente isto para a tabela gerada
    em DAX — inclusive envolvida em ADDCOLUMNS: o critério é a partição ser
    calculada, não a primeira função."""
    modelo = ler(
        tabelas=[
            tabela("FactOnlineSales", colunas=[coluna("DateKey", tipo_dado="dateTime")]),
            tabela(
                "DimCalendar",
                colunas=[
                    coluna("Date", tipo_dado="dateTime"),
                    coluna("Ano", tipo="calculated", expressao="YEAR([Date])"),
                ],
                particoes=[
                    particao(tipo="calculated", expressao='ADDCOLUMNS(CALENDAR(DATE(2020,1,1), DATE(2024,12,31)), "Mes", MONTH([Date]))')
                ],
            ),
        ],
        relacionamentos=[relacionamento("FactOnlineSales", "DateKey", "DimCalendar", "Date")],
    )

    assert list(coluna_calculada_em_dax(modelo)) == []
```

Em `tests/test_rules_escopo.py`, acrescentar `tabela_calculada_em_dax` ao import e, ao fim:

```python
def test_tabela_calculada_em_dax_olha_o_tipo_da_particao(ler):
    modelo = ler(
        tabelas=[
            tabela("Calculada", particoes=[particao(tipo="calculated", expressao="CALENDARAUTO()")]),
            tabela("Importada", particoes=[particao(tipo="m")]),
            tabela("SemParticao"),
        ]
    )
    assert [tabela_calculada_em_dax(t) for t in modelo.tabelas] == [True, False, False]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rules_performance.py tests/test_rules_escopo.py -q`
Expected: erro de coleta em `test_rules_escopo.py` (`cannot import name 'tabela_calculada_em_dax'`); em `test_rules_performance.py`, `test_perf001_marca_coluna_de_dimensao_de_data_importada` falha com lista vazia.

- [ ] **Step 3: Implementar**

Em `core/rules/escopo.py`, logo antes de `def grupo_de_calculo`:

```python
def tabela_calculada_em_dax(t: Tabela) -> bool:
    """A tabela é gerada por expressão DAX (partição `calculated`)."""
    return any(p.tipo_origem == "calculated" for p in t.particoes)
```

Em `core/rules/performance.py`, acrescentar `tabela_calculada_em_dax` ao `from core.rules.escopo import (...)` e trocar a docstring e o laço de `coluna_calculada_em_dax` por:

```python
def coluna_calculada_em_dax(modelo: ModeloSemantico) -> Iterator[Achado]:
    """Uma ocorrência por coluna com `type: calculated`.

    Duas exclusões. As colunas de agrupamento e cluster, cujo DAX é escrito pela
    interface. E as colunas da dimensão de data **calculada em DAX**: as páginas de
    tempo automático e de tabelas de data recomendam gerar a tabela com CALENDAR ou
    CALENDARAUTO e então acrescentar colunas calculadas. Dimensão de data importada
    pelo Power Query não tem essa exceção — quando a origem já tem a tabela de data,
    a recomendação é usá-la (corrigido em 12/10/2026, pelo gabarito de P1–P7).
    """
    dimensoes_de_data = dimensao_de_data(modelo)

    for t in tabelas_em_escopo(modelo):
        if t.nome in dimensoes_de_data and tabela_calculada_em_dax(t):
            continue
```

(o restante do laço — o `for c in t.colunas:` e o `yield` — fica igual).

No `recomendacao_padrao` da PERF-001, trocar o trecho final `"de hierarquia pai-filho."` por:

```python
        "de hierarquia pai-filho, ou quando estende uma tabela de data gerada em DAX "
        "com CALENDAR ou CALENDARAUTO."
```

Na docstring do módulo `tests/test_rules_performance.py`, trocar "recomenda explicitamente colunas calculadas numa tabela de data em DAX." por "recomenda explicitamente colunas calculadas numa tabela de data **gerada em DAX** — e só nela."

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rules_performance.py tests/test_rules_escopo.py tests/test_pbip_real.py -q`
Expected: todos passam. O `test_pbip_real.py` (P8) não muda: a dimensão de data do P8 é calculada em DAX. `test_perf001_ignora_dimensao_de_data_com_chave_inteira` continua passando (tem partição `CALENDAR`).

- [ ] **Step 5: Suíte e commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: só `tests/test_rag_avaliacao_real.py` pode falhar (Tarefa 4).

```bash
git add core/rules/escopo.py core/rules/performance.py tests/test_rules_performance.py tests/test_rules_escopo.py
git commit -m "fix(regras): PERF-001 exclui so a dimensao de data calculada em DAX"
```

---

### Task 3: `python -m gabarito medir --rotulo`

**Files:**
- Modify: `gabarito/__main__.py`
- Test: `tests/test_gabarito_comando.py`

**Interfaces:**
- Consumes: `main(argv)`, `_medir()`, `PASTA_RESULTADOS` (existentes).
- Produces: subcomando `medir [--rotulo ROTULO]`; constante `ROTULO_VALIDO` (regex `[a-z0-9][a-z0-9-]*`); arquivo `regras-<data>-<rotulo>.json`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_gabarito_comando.py`, acrescentar `from datetime import date` aos imports e, ao fim:

```python
def test_medir_com_rotulo_grava_ao_lado_sem_sobrescrever(ambiente):
    comando.main(["gerar"])
    _preencher_tudo(ambiente / "gabarito" / "anotacao.xlsx")
    comando.main(["importar"])
    assert comando.main(["medir"]) == 0
    assert comando.main(["medir", "--rotulo", "pos-correcao"]) == 0
    hoje = date.today().isoformat()
    nomes = sorted(p.name for p in (ambiente / "results").glob("regras-*.json"))
    assert nomes == [f"regras-{hoje}-pos-correcao.json", f"regras-{hoje}.json"]


@pytest.mark.parametrize("rotulo", ["../fora", "Pos", "a b", "-x", ""])
def test_medir_recusa_rotulo_invalido_sem_gravar(ambiente, capsys, rotulo):
    comando.main(["gerar"])
    _preencher_tudo(ambiente / "gabarito" / "anotacao.xlsx")
    comando.main(["importar"])
    assert comando.main(["medir", "--rotulo", rotulo]) == 1
    assert "rotulo" in capsys.readouterr().err
    assert not (ambiente / "results").exists() or list((ambiente / "results").iterdir()) == []
    assert not (ambiente / "fora.json").exists()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_comando.py -q`
Expected: os 6 testes novos falham — o argparse recusa `--rotulo` (`SystemExit: 2`).

- [ ] **Step 3: Implementar em `gabarito/__main__.py`**

Acrescentar `import re` aos imports e, depois de `PASTA_RESULTADOS`:

```python
ROTULO_VALIDO = re.compile(r"[a-z0-9][a-z0-9-]*")
"""Sufixo do arquivo de resultado: minúsculas, dígitos e hífen. Nada de separador
de caminho — o rótulo vira parte de um nome de arquivo."""
```

Trocar `_medir` por:

```python
def _medir(rotulo: str | None = None) -> int:
    if rotulo is not None and not ROTULO_VALIDO.fullmatch(rotulo):
        print(_ascii(f"erro: rotulo invalido {rotulo!r} - use minusculas, digitos e hifen"), file=sys.stderr)
        return 1
    if not ARQUIVO_CSV.is_file():
        print(f"erro: {ARQUIVO_CSV.name} ausente - rode `python -m gabarito importar`", file=sys.stderr)
        return 1
    resultado = medir(ler_csv(ARQUIVO_CSV), achados_dos_projetos(PASTA_PBIP))
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    sufixo = f"-{rotulo}" if rotulo else ""
    destino = PASTA_RESULTADOS / f"regras-{date.today().isoformat()}{sufixo}.json"
    destino.write_text(resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(formatar(resultado))
    print(_ascii(f"Resultado em {destino}"))
    return 0
```

Em `main`, trocar `sub.add_parser("medir", help="precisao e recall por regra")` por:

```python
    medir_ = sub.add_parser("medir", help="precisao e recall por regra")
    medir_.add_argument(
        "--rotulo", help="sufixo do arquivo de resultado, para nao sobrescrever a medicao do dia (ex.: pos-correcao)"
    )
```

e `return _medir()` por `return _medir(args.rotulo)`.

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gabarito_comando.py -q`
Expected: 14 passed (8 anteriores + 6 novos).

- [ ] **Step 5: Commit**

```bash
git add gabarito/__main__.py tests/test_gabarito_comando.py
git commit -m "feat(gabarito): medir --rotulo, sem sobrescrever o resultado oficial"
```

---

### Task 4: Regerar o conjunto da recuperação

**Files:**
- Modify: `eval/recuperacao/consultas.yaml` (regerado, nunca editado à mão)
- Modify: `tests/test_rag_avaliacao_real.py` (contagens)

- [ ] **Step 1: Ver a falha**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_avaliacao_real.py -q`
Expected: `test_consultas_versionadas_sao_o_que_o_gerador_produz` falha ("consultas.yaml divergiu").

- [ ] **Step 2: Regerar e conferir o diff**

Run: `.\.venv\Scripts\python.exe -m rag.avaliacao gerar` e depois `git diff --stat eval/recuperacao/consultas.yaml` e `git diff eval/recuperacao/consultas.yaml`.
Expected: saem as 4 consultas de achado da MOD-003 (`Date Role`, `Time Intelligence`, `Toggle for breakdown`, `Toggle for variance to plan`) e entram 12 da PERF-001 (P1 `Date[Mth]`, `Date[Mth of year]`, `Date[Year]`; P2 `Date[Month]`; P3 `Date[Month increment number]`; P4 as 7 colunas de `Date`). Os 9 gabaritos não mudam. Total: 70 consultas (9 de regra + 61 de achado). Se o diff tiver qualquer outra mudança, parar: é efeito não previsto das Tarefas 1–2.

- [ ] **Step 3: Atualizar as contagens do teste**

Em `tests/test_rag_avaliacao_real.py`, em `test_contagem_do_conjunto_versionado`, trocar as duas ocorrências de `62` por `70`, e acrescentar acima do primeiro `assert` de contagem o comentário:

```python
    # 62 até a tag `regras-gt`; 70 depois da correção da MOD-003 (−4) e da PERF-001 (+12).
```

- [ ] **Step 4: Rodar e ver passar; suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: tudo passa.

- [ ] **Step 5: Commit**

```bash
git add eval/recuperacao/consultas.yaml tests/test_rag_avaliacao_real.py
git commit -m "eval: conjunto da recuperacao regerado apos a correcao das regras"
```

---

### Task 5: Medir de novo e registrar

**Files:**
- Create: `eval/results/regras-<data>-pos-correcao.json` (gerado)
- Modify: `docs/project/progress-log.md`, `docs/project/riscos.md`, `docs/project/status.md`

- [ ] **Step 1: Medir com rótulo**

Run: `.\.venv\Scripts\python.exe -m gabarito medir --rotulo pos-correcao`
Expected: grava `eval/results/regras-<data>-pos-correcao.json`. `git status` **não** mostra `eval/results/regras-2026-10-12.json` modificado. MOD-003: VP 1, FP 2 (`Logo`, `Indicators`), precisão 0,33. PERF-001: FN 0; as outras 6 colunas de data aparecem como FP ou indeterminado conforme o veredito do Fred — anotar os números exatos.

- [ ] **Step 2: Registrar**

- `docs/project/progress-log.md`: entrada nova ao fim, `## <data> — Correção da MOD-003 e da PERF-001 (análise de erros)`, com: as duas correções e a base documental; a tabela por regra **lado a lado** (oficial na tag `regras-gt` × pós-correção) para MOD-003, PERF-001 e o total; a limitação declarada (`Logo`, `Indicators`); a frase "a medição pós-correção foi motivada pelo conjunto de teste e não substitui o resultado oficial"; o conjunto da recuperação regerado (62 → 70) e a recuperação não remedida; suíte; e `**Próximo passo:**` "merge do PR #6 e do PR desta branch; depois o subprojeto 2 (busca combinada)".
- `docs/project/riscos.md`: na linha do R-03, acrescentar ao fim da coluna de mitigação: "Em 12/10/2026 o gabarito mediu as regras na tag `regras-gt`: só a MOD-003 ficou abaixo de 0,7 (0,14). A correção pós-tag (grupo de cálculo e parâmetro de campo fora de escopo) leva a <número>, ainda abaixo, pela limitação declarada das tabelas digitadas à mão — análise de erros, não resultado." e atualizar a linha "Última atualização".
- `docs/project/status.md`: na linha da Fase 3, trocar "gabarito das regras com planilha gerada (350 candidatos em P1–P7), anotação em andamento" por "gabarito das regras anotado e medido (precisão 0,88 na tag `regras-gt`); correção da MOD-003 e da PERF-001 como análise de erros".

- [ ] **Step 3: Commit e push**

```bash
git add eval/results docs/project/progress-log.md docs/project/riscos.md docs/project/status.md
git commit -m "eval: medicao pos-correcao da MOD-003 e da PERF-001 (analise de erros)"
git push
```
