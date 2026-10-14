# Avaliação da geração e consolidação — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ferramenta `python -m avaliacao_geracao auditar|gerar|importar|medir|consolidar` para rodar a auditoria completa de P1–P7, anotar a rubrica humana das explicações numa planilha cega, medir as taxas com Wilson e kappa, e consolidar todos os resultados da monografia num arquivo só.

**Architecture:** Pacote `avaliacao_geracao/` no molde do `gabarito/`: `estatistica.py` (Wilson, kappa), `rodada.py` (auditoria avaliada, id e impressão digital), `planilha.py` (gerar, ler, validar, CSV), `metricas.py` (taxas, recortes, descarte, humano × automático), `consolidacao.py` (fonte única), `__main__.py` (CLI). Os JSONs da rodada e a planilha ficam fora do git (texto do Learn); o CSV oficial e os resultados entram.

**Tech Stack:** Python 3.11, Pydantic 2, openpyxl 3.1.5, pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-avaliacao-da-geracao-design.md`

## Global Constraints

- Todo o projeto em português: código, nomes, mensagens, commits.
- Vereditos: exatamente `sim`, `não`, `indeterminado`; justificativa obrigatória quando algum item é `não`.
- A planilha **não** mostra `cita_ancora`, divergências de fidelidade, `do_cache`, tempos nem tokens.
- `eval/geracao/` e a planilha ficam fora do git; entram `eval/rubrica_geracao.csv` e `eval/results/*.json`.
- Toda falha de comando vira mensagem (ASCII no console) e código 1; nunca traceback.
- `auditar` usa o cache (`ClienteComCache`) e respeita a ADR-003 (Ollama fora do ar aborta).
- Nenhuma dependência nova.
- Python pelo venv: `.\.venv\Scripts\python.exe -m pytest ...`; suíte completa ~7 min, no fim das tarefas que mexem em mais de um módulo.
- Commits com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push na `fase5-avaliacao` a cada tarefa.

## Review Focus

1. **Expressão DAX ou texto do LLM começando com `=`** na planilha: viraria fórmula do Excel — toda célula de leitura é gravada como texto (`data_type = "s"`), como no gabarito. Teste na Task 3.
2. **Rodada refeita depois da anotação com algum texto diferente** (resposta fora do cache): a importação precisa recusar a linha pela impressão digital, nunca ligar o veredito a outro texto. Teste na Task 3.
3. **Achado sem trecho âncora no contexto** (contexto reduzido ao limite, ou JSON antigo) ao montar a referência da regra: a célula diz "trecho âncora ausente" em vez de quebrar. Teste na Task 3.
4. **Recorte sem nenhum sim/não** (regra com todos os vereditos indeterminados): principal e Wilson são `None`, não divisão por zero. Teste na Task 4.
5. **Tabela 2×2 degenerada** (todos concordam numa só casa, `pe == 1`): kappa `None`, não divisão por zero. Teste na Task 1.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `avaliacao_geracao/__init__.py` | Pacote; `ErroDeAvaliacao` |
| `avaliacao_geracao/estatistica.py` | `wilson`, `kappa` |
| `avaliacao_geracao/rodada.py` | `PASTA_RODADA`, `id_do_achado`, `impressao`, `auditar`, `carregar_rodada` |
| `avaliacao_geracao/planilha.py` | `gerar_planilha`, `ler_planilha`, `validar`, `gravar_csv`, `ler_csv` |
| `avaliacao_geracao/metricas.py` | `medir` |
| `avaliacao_geracao/consolidacao.py` | `consolidar` |
| `avaliacao_geracao/__main__.py` | CLI |
| `.gitignore` | `eval/geracao/` |
| `tests/test_avaliacao_*.py` | Testes |

---

### Task 1: Estatística (Wilson e kappa)

**Files:**
- Create: `avaliacao_geracao/__init__.py`, `avaliacao_geracao/estatistica.py`
- Test: `tests/test_avaliacao_estatistica.py`

**Interfaces:**
- Produces: `ErroDeAvaliacao(Exception)` em `avaliacao_geracao/__init__.py`; `wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float] | None`; `kappa(a: int, b: int, c: int, d: int) -> float | None` — tabela automático (linhas sim/não) × humano (colunas sim/não): `a` = ambos sim, `b` = auto sim e humano não, `c` = auto não e humano sim, `d` = ambos não.

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_estatistica.py`:

```python
"""Wilson e kappa contra valores de referência."""

import pytest

from avaliacao_geracao.estatistica import kappa, wilson


@pytest.mark.parametrize("sucessos,total,esperado", [
    (52, 56, (0.8302, 0.9719)),
    (46, 52, (0.7703, 0.9460)),
    (0, 10, (0.0, 0.2775)),
    (10, 10, (0.7225, 1.0)),
])
def test_wilson_contra_referencia(sucessos, total, esperado):
    baixo, alto = wilson(sucessos, total)
    assert (round(baixo, 4), round(alto, 4)) == esperado


def test_wilson_sem_denominador_e_none():
    assert wilson(0, 0) is None


def test_kappa_exemplo_classico():
    """20 ambos sim, 5 e 10 em desacordo, 15 ambos não: concordância 0,7, acaso 0,5."""
    assert kappa(20, 5, 10, 15) == pytest.approx(0.4)


def test_kappa_concordancia_perfeita_e_degenerada():
    assert kappa(10, 0, 0, 5) == pytest.approx(1.0)
    assert kappa(10, 0, 0, 0) is None  # Review Focus 5: acaso = 1
    assert kappa(0, 0, 0, 0) is None
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_estatistica.py -q`
Expected: FAIL — `ModuleNotFoundError: avaliacao_geracao`.

- [ ] **Step 2: Implementar**

`avaliacao_geracao/__init__.py`:

```python
"""Avaliação da geração com rubrica humana e consolidação dos resultados (Fase 5).

Desenho: `docs/superpowers/specs/2026-10-13-avaliacao-da-geracao-design.md`.
"""


class ErroDeAvaliacao(Exception):
    """A avaliação não pode seguir sem produzir um número enganoso."""
```

`avaliacao_geracao/estatistica.py`:

```python
"""Intervalo de Wilson (Wilson, 1927) e kappa de Cohen (Cohen, 1960).

Wilson e não o intervalo normal: com n pequeno e taxas perto de 1 — o caso das
regras por projeto — o intervalo normal sai de [0, 1] e fica estreito demais.
"""

from math import sqrt


def wilson(sucessos: int, total: int, z: float = 1.96) -> tuple[float, float] | None:
    if total == 0:
        return None
    p = sucessos / total
    denominador = 1 + z * z / total
    centro = (p + z * z / (2 * total)) / denominador
    margem = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominador
    return max(0.0, centro - margem), min(1.0, centro + margem)


def kappa(a: int, b: int, c: int, d: int) -> float | None:
    """Automático (linhas) × humano (colunas): `a` ambos sim, `b` automático sim e
    humano não, `c` automático não e humano sim, `d` ambos não. `None` quando não
    há linhas ou quando o acaso explica tudo (`pe == 1`)."""
    n = a + b + c + d
    if n == 0:
        return None
    observada = (a + d) / n
    acaso = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    if acaso == 1:
        return None
    return (observada - acaso) / (1 - acaso)
```

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_estatistica.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add avaliacao_geracao/__init__.py avaliacao_geracao/estatistica.py tests/test_avaliacao_estatistica.py
git commit -m "feat(avaliacao): intervalo de Wilson e kappa de Cohen"
git push
```

---

### Task 2: A rodada avaliada (`rodada.py`)

**Files:**
- Create: `avaliacao_geracao/rodada.py`
- Modify: `.gitignore`
- Test: `tests/test_avaliacao_rodada.py`

**Interfaces:**
- Consumes: `run_audit`, `ResultadoAuditoria` (`core.auditoria`); `ler_resultado`, `ErroDeLeitura` (`core.apresentacao`); `AchadoEnriquecido`.
- Produces:
  - `PASTA_RODADA: Path` (= `RAIZ_REPO / "eval" / "geracao" / "auditorias"`), `PASTA_PBIP: Path` (= `RAIZ_REPO / "data" / "pbip"`), `PADRAO_PROJETOS = re.compile(r"^P[1-7]_")`
  - `id_do_achado(projeto: str, item: AchadoEnriquecido) -> str` = `projeto|regra|objeto`
  - `impressao(item: AchadoEnriquecido) -> str | None` = sha256 hex de `explicacao + "\n" + recomendacao` (None sem geração)
  - `ItemDaRodada(projeto: str, item: AchadoEnriquecido)` (dataclass frozen)
  - `Rodada = dict[str, ItemDaRodada]` (chave = id)
  - `projetos_da_avaliacao(pasta: Path = PASTA_PBIP) -> list[Path]`
  - `ResumoDaRodada(projetos: int, achados: int, gerados: int, fora_do_cache: int)` (dataclass)
  - `auditar(pastas: list[Path], destino: Path, *, llm, base, **kwargs) -> ResumoDaRodada` (grava `<destino>/<projeto>.json`; `kwargs` vai para `run_audit`, para os testes passarem `registro` e `gabaritos`)
  - `carregar_rodada(pasta: Path = PASTA_RODADA) -> Rodada` (pasta vazia ou ausente, JSON ilegível ou id duplicado → `ErroDeAvaliacao`)

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_rodada.py`:

```python
"""Rodada avaliada: id estável, impressão digital, auditoria e leitura."""

import pytest

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.rodada import (
    auditar, carregar_rodada, id_do_achado, impressao, projetos_da_avaliacao,
)
from conftest import escrever_pbip, modelo_tmsl, tabela
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.analise.cache import ClienteComCache
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, contexto, gabarito, meta


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    return registro


def _gerado(explicacao="e", recomendacao="Use uma tabela de datas própria.") -> AchadoEnriquecido:
    return AchadoEnriquecido(
        achado=achado(objeto="T"), contexto=contexto(2),
        geracao=Geracao(explicacao=explicacao, recomendacao=recomendacao, citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m",
    )


def test_id_e_impressao():
    item = _gerado()
    assert id_do_achado("P1_X", item) == "P1_X|MOD-001|T"
    assert impressao(item) == impressao(_gerado()) and len(impressao(item)) == 64
    assert impressao(item) != impressao(_gerado(explicacao="outra"))
    assert impressao(AchadoEnriquecido.so_regras(achado())) is None


def test_projetos_da_avaliacao_so_p1_a_p7(tmp_path):
    for nome in ["P1_A", "P7_B", "P8_contoso", "P9_x", "outra"]:
        (tmp_path / nome).mkdir()
    (tmp_path / "P2_arquivo.txt").write_text("x", encoding="utf-8")
    assert [p.name for p in projetos_da_avaliacao(tmp_path)] == ["P1_A", "P7_B"]


def test_auditar_grava_um_json_por_projeto_e_conta_o_cache(tmp_path):
    pastas = [escrever_pbip(tmp_path / n, nome=n, model_bim=modelo_tmsl([tabela("T1"), tabela("T2")]))
              for n in ["P1_A", "P2_B"]]
    comum = dict(base=base_padrao(), registro=_registro(), gabaritos={"MOD-001": gabarito()})
    llm = ClienteComCache(LLMFalso(), tmp_path / "cache")
    primeiro = auditar(pastas, tmp_path / "rodada", llm=llm, **comum)
    assert (primeiro.projetos, primeiro.achados, primeiro.gerados, primeiro.fora_do_cache) == (2, 4, 4, 4)
    segundo = auditar(pastas, tmp_path / "rodada", llm=ClienteComCache(LLMFalso(), tmp_path / "cache"), **comum)
    assert segundo.fora_do_cache == 0
    rodada = carregar_rodada(tmp_path / "rodada")
    assert sorted(rodada) == ["P1_A|MOD-001|T1", "P1_A|MOD-001|T2", "P2_B|MOD-001|T1", "P2_B|MOD-001|T2"]
    assert rodada["P2_B|MOD-001|T1"].projeto == "P2_B"


def test_carregar_rodada_ausente_ou_ilegivel(tmp_path):
    with pytest.raises(ErroDeAvaliacao, match="nenhuma auditoria"):
        carregar_rodada(tmp_path / "nao-existe")
    (tmp_path / "P1_A.json").write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ErroDeAvaliacao, match="P1_A.json"):
        carregar_rodada(tmp_path)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_rodada.py -q`
Expected: FAIL — `ModuleNotFoundError: avaliacao_geracao.rodada`.

- [ ] **Step 2: Implementar**

`.gitignore`, depois de `eval/gabarito/`: acrescentar a linha `eval/geracao/`.

`avaliacao_geracao/rodada.py`:

```python
"""A rodada avaliada: a auditoria completa de P1–P7 cujas explicações são julgadas.

Fica fora do git (`eval/geracao/`): o contexto de cada achado traz seções do Learn,
cuja cópia é local e não redistribuível. O id do achado é estável entre rodadas, e a
impressão digital liga cada veredito ao texto que foi julgado.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from avaliacao_geracao import ErroDeAvaliacao
from core.analise.base import AchadoEnriquecido
from core.apresentacao import ErroDeLeitura, ler_resultado
from core.auditoria import run_audit
from rag.avaliacao import RAIZ_REPO

PASTA_RODADA = RAIZ_REPO / "eval" / "geracao" / "auditorias"
PASTA_PBIP = RAIZ_REPO / "data" / "pbip"
PADRAO_PROJETOS = re.compile(r"^P[1-7]_")


def id_do_achado(projeto: str, item: AchadoEnriquecido) -> str:
    return f"{projeto}|{item.achado.id_regra}|{item.achado.evidencia.objeto}"


def impressao(item: AchadoEnriquecido) -> str | None:
    if item.geracao is None:
        return None
    texto = f"{item.geracao.explicacao}\n{item.geracao.recomendacao}"
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ItemDaRodada:
    projeto: str
    item: AchadoEnriquecido


Rodada = dict[str, ItemDaRodada]


def projetos_da_avaliacao(pasta: Path = PASTA_PBIP) -> list[Path]:
    return sorted(p for p in pasta.iterdir() if p.is_dir() and PADRAO_PROJETOS.match(p.name))


@dataclass
class ResumoDaRodada:
    projetos: int
    achados: int
    gerados: int
    fora_do_cache: int
    """Respostas que não vieram do cache: o texto pode ter mudado desde a última rodada."""


def auditar(pastas: list[Path], destino: Path, *, llm, base, **kwargs) -> ResumoDaRodada:
    destino.mkdir(parents=True, exist_ok=True)
    resumo = ResumoDaRodada(projetos=0, achados=0, gerados=0, fora_do_cache=0)
    for pasta in pastas:
        resultado = run_audit(pasta, llm=llm, base=base, **kwargs)
        (destino / f"{resultado.projeto}.json").write_text(
            resultado.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        resumo.projetos += 1
        resumo.achados += len(resultado.achados)
        resumo.gerados += sum(1 for a in resultado.achados if a.situacao == "gerado")
        resumo.fora_do_cache += sum(1 for a in resultado.achados if a.segundos is not None and not a.do_cache)
    return resumo


def carregar_rodada(pasta: Path = PASTA_RODADA) -> Rodada:
    arquivos = sorted(pasta.glob("*.json")) if pasta.is_dir() else []
    if not arquivos:
        raise ErroDeAvaliacao(f"nenhuma auditoria em {pasta} — rode `python -m avaliacao_geracao auditar`")
    rodada: Rodada = {}
    for arquivo in arquivos:
        try:
            resultado = ler_resultado(arquivo.read_bytes())
        except (OSError, ErroDeLeitura) as erro:
            raise ErroDeAvaliacao(f"{arquivo.name}: {erro}") from erro
        for item in resultado.achados:
            chave = id_do_achado(resultado.projeto, item)
            if chave in rodada:
                raise ErroDeAvaliacao(f"id duplicado na rodada: {chave}")
            rodada[chave] = ItemDaRodada(resultado.projeto, item)
    return rodada
```

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_rodada.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add .gitignore avaliacao_geracao/rodada.py tests/test_avaliacao_rodada.py
git commit -m "feat(avaliacao): rodada avaliada com id estavel e impressao digital"
git push
```

---

### Task 3: Planilha cega, importação e CSV (`planilha.py`)

**Files:**
- Create: `avaliacao_geracao/planilha.py`
- Test: `tests/test_avaliacao_planilha.py`

**Interfaces:**
- Consumes: `Rodada`, `ItemDaRodada`, `impressao` (Task 2); `REGISTRO`.
- Produces:
  - `VEREDITOS = ("sim", "não", "indeterminado")`, `ITENS = ("pertinente", "fiel", "recomendacao_correta")`, `LIMITE_TRECHO = 3000`, `PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "rubrica-geracao-P1-P7.xlsx"`, `CSV_OFICIAL = RAIZ_REPO / "eval" / "rubrica_geracao.csv"`
  - `LinhaRubrica(BaseModel)`: `id: str`, `impressao: str`, `pertinente`, `fiel`, `recomendacao_correta`, `justificativa`, `observacao` (todos `str | None = None`)
  - `Problema(BaseModel)`: `linha: int | None`, `id: str`, `motivo: str`
  - `gerar_planilha(rodada: Rodada, destino: Path, *, forcar: bool = False, registro=None) -> int` (número de linhas)
  - `ler_planilha(caminho: Path) -> list[tuple[int, LinhaRubrica]]`
  - `validar(lidas, rodada: Rodada, parcial: bool) -> list[Problema]`
  - `gravar_csv(linhas: list[LinhaRubrica], caminho: Path) -> None`; `ler_csv(caminho: Path) -> list[LinhaRubrica]`

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_planilha.py`:

```python
"""Planilha cega da rubrica: o que mostra, o que esconde, e a importação."""

import pytest
from openpyxl import load_workbook

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.planilha import (
    LIMITE_TRECHO, LinhaRubrica, gerar_planilha, gravar_csv, ler_csv, ler_planilha, validar,
)
from avaliacao_geracao.rodada import ItemDaRodada, id_do_achado, impressao
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from fabricas_analise import achado, contexto, trecho_de_contexto


def _gerado(objeto="T", explicacao="A tabela automática aumenta o modelo.", ctx=None) -> AchadoEnriquecido:
    return AchadoEnriquecido(
        achado=achado(objeto=objeto), contexto=ctx or contexto(2),
        geracao=Geracao(explicacao=explicacao, recomendacao="Desative a opção.", citacoes=[1]),
        situacao="gerado", cita_ancora=False, fidelidade=Fidelidade(divergencias=["42"]), modelo="m",
        segundos=8.1, tokens_prompt=999, do_cache=True,
    )


def _rodada(*itens) -> dict:
    return {id_do_achado("P1_A", i): ItemDaRodada("P1_A", i) for i in itens}


def _celulas(caminho):
    aba = load_workbook(caminho)["Rubrica"]
    return aba, [[c.value for c in linha] for linha in aba.iter_rows()]


def test_planilha_mostra_o_texto_e_esconde_os_sinais_automaticos(tmp_path):
    descartado = AchadoEnriquecido(achado=achado(objeto="X"), contexto=contexto(1), situacao="sem_fundamentacao",
                                   motivo_descarte="json_invalido", modelo="m")
    destino = tmp_path / "r.xlsx"
    assert gerar_planilha(_rodada(_gerado(), descartado), destino) == 1
    aba, celulas = _celulas(destino)
    texto = " ".join(str(v) for linha in celulas for v in linha if v is not None)
    assert "P1_A|MOD-001|T" in texto and "A tabela automática aumenta o modelo." in texto
    assert "Desative a opção." in texto and "Disable the auto date/time option." in texto
    assert "https://learn.microsoft.com/x" in texto  # referência da regra
    for proibido in ["cita_ancora", "42", "999", "8.1", "do_cache", "P1_A|MOD-001|X"]:
        assert proibido not in texto
    assert aba.protection.sheet is True
    assert "Instruções" in load_workbook(destino).sheetnames


def test_texto_longo_cortado_e_formula_vira_texto(tmp_path):
    """Review Focus 1."""
    longo = trecho_de_contexto(1, texto="x" * (LIMITE_TRECHO + 500))
    item = _gerado(explicacao="=SUM(1)", ctx=[longo, trecho_de_contexto(2)])
    destino = tmp_path / "r.xlsx"
    gerar_planilha(_rodada(item), destino)
    aba = load_workbook(destino)["Rubrica"]
    valores = [c for linha in aba.iter_rows() for c in linha if c.value is not None]
    explicacao = next(c for c in valores if c.value == "=SUM(1)")
    assert explicacao.data_type == "s"
    assert any("[…]" in str(c.value) and "x" * LIMITE_TRECHO in str(c.value) for c in valores)
    assert not any("x" * (LIMITE_TRECHO + 1) in str(c.value) for c in valores)


def test_sem_trecho_ancora_diz_ausente(tmp_path):
    """Review Focus 3."""
    item = _gerado(ctx=[trecho_de_contexto(1, origem="busca"), trecho_de_contexto(2)])
    destino = tmp_path / "r.xlsx"
    gerar_planilha(_rodada(item), destino)
    _, celulas = _celulas(destino)
    assert any("trecho âncora ausente" in str(v) for linha in celulas for v in linha)


def test_nao_sobrescreve_sem_forcar(tmp_path):
    destino = tmp_path / "r.xlsx"
    gerar_planilha(_rodada(_gerado()), destino)
    with pytest.raises(ErroDeAvaliacao, match="já existe"):
        gerar_planilha(_rodada(_gerado()), destino)
    gerar_planilha(_rodada(_gerado()), destino, forcar=True)


def _anotar(destino, **valores):
    livro = load_workbook(destino)
    aba = livro["Rubrica"]
    cabecalho = [c.value for c in next(aba.iter_rows(min_row=1, max_row=1))]
    for nome, valor in valores.items():
        aba.cell(row=2, column=cabecalho.index(nome) + 1, value=valor)
    livro.save(destino)


def test_importacao_valida_e_ida_e_volta_do_csv(tmp_path):
    item = _gerado()
    rodada = _rodada(item)
    destino = tmp_path / "r.xlsx"
    gerar_planilha(rodada, destino)
    _anotar(destino, pertinente="sim", fiel="não", recomendacao_correta="indeterminado", justificativa="inventou 42")
    lidas = ler_planilha(destino)
    assert validar(lidas, rodada, parcial=False) == []
    linhas = [l for _, l in lidas]
    gravar_csv(linhas, tmp_path / "r.csv")
    assert ler_csv(tmp_path / "r.csv") == linhas
    assert linhas[0].impressao == impressao(item)


@pytest.mark.parametrize("valores,motivo", [
    (dict(pertinente="talvez", fiel="sim", recomendacao_correta="sim"), "fora da lista"),
    (dict(pertinente="não", fiel="sim", recomendacao_correta="sim"), "sem justificativa"),
    (dict(pertinente="sim"), "sem veredito"),
])
def test_importacao_recusa(tmp_path, valores, motivo):
    rodada = _rodada(_gerado())
    destino = tmp_path / "r.xlsx"
    gerar_planilha(rodada, destino)
    _anotar(destino, **valores)
    problemas = validar(ler_planilha(destino), rodada, parcial=False)
    assert any(motivo in p.motivo for p in problemas)


def test_parcial_aceita_linha_em_branco(tmp_path):
    rodada = _rodada(_gerado())
    destino = tmp_path / "r.xlsx"
    gerar_planilha(rodada, destino)
    assert validar(ler_planilha(destino), rodada, parcial=True) == []


def test_impressao_divergente_e_id_desconhecido_sao_recusados(tmp_path):
    """Review Focus 2: texto refeito fora do cache depois da anotação."""
    destino = tmp_path / "r.xlsx"
    gerar_planilha(_rodada(_gerado()), destino)
    _anotar(destino, pertinente="sim", fiel="sim", recomendacao_correta="sim")
    lidas = ler_planilha(destino)
    refeita = _rodada(_gerado(explicacao="Outro texto."))
    assert any("impressão digital" in p.motivo for p in validar(lidas, refeita, parcial=False))
    assert any("não existe na rodada" in p.motivo for p in validar(lidas, {}, parcial=False))


def test_id_duplicado_e_recusado():
    linha = LinhaRubrica(id="a", impressao="x", pertinente="sim", fiel="sim", recomendacao_correta="sim")
    problemas = validar([(2, linha), (3, linha)], {}, parcial=False)
    assert any("duplicado" in p.motivo for p in problemas)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_planilha.py -q`
Expected: FAIL — `ModuleNotFoundError: avaliacao_geracao.planilha`.

- [ ] **Step 2: Implementar**

`avaliacao_geracao/planilha.py`:

```python
"""A planilha cega da rubrica, a importação e o CSV oficial.

Mostra o que o LLM escreveu e o que ele citou, e a referência da regra; esconde
os sinais automáticos (citação da âncora, divergências, cache, tempos), para que a
comparação humano × automático meça alguma coisa.
"""

import csv
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, Protection
from openpyxl.worksheet.datavalidation import DataValidation
from pydantic import BaseModel

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.rodada import ItemDaRodada, Rodada, impressao
from core.rules.registry import Registro
from core.rules.todas import REGISTRO
from rag.avaliacao import RAIZ_REPO

VEREDITOS = ("sim", "não", "indeterminado")
ITENS = ("pertinente", "fiel", "recomendacao_correta")
LIMITE_TRECHO = 3000
PLANILHA = RAIZ_REPO / "eval" / "gabarito" / "rubrica-geracao-P1-P7.xlsx"
CSV_OFICIAL = RAIZ_REPO / "eval" / "rubrica_geracao.csv"

COLUNAS_LEITURA = (
    "id", "impressao", "projeto", "regra", "titulo_regra", "objeto", "mensagem",
    "explicacao", "recomendacao", "citacoes", "referencia_regra",
)
COLUNAS_ANOTACAO = (*ITENS, "justificativa", "observacao")
LARGURAS = {"id": 30, "impressao": 10, "projeto": 12, "regra": 9, "titulo_regra": 25, "objeto": 30,
            "mensagem": 40, "explicacao": 60, "recomendacao": 50, "citacoes": 80, "referencia_regra": 60,
            "pertinente": 13, "fiel": 13, "recomendacao_correta": 13, "justificativa": 40, "observacao": 30}

INSTRUCOES = [
    "Rubrica das explicações do LLM em P1–P7 — protocolo de anotação",
    "",
    "Uma linha por achado com explicação gerada. Julgue o que o LLM escreveu contra os trechos citados e a",
    "referência da regra (coluna referencia_regra).",
    "",
    "pertinente — pelo menos um trecho citado é de fato a passagem da documentação que sustenta o achado",
    "  (não basta existir entre os trechos fornecidos).",
    "fiel — o que a explicação afirma é sustentado pelos trechos citados ou pelos fatos do achado, sem nada",
    "  inventado (números, nomes, comportamentos).",
    "recomendacao_correta — a recomendação resolve o problema neste modelo, sem erro técnico.",
    "",
    "Vereditos: 'sim', 'não' ou 'indeterminado' (lista suspensa). Justificativa obrigatória quando algum item é 'não'.",
    "Trechos longos estão cortados em 3.000 caracteres ([…]); o link leva ao texto completo.",
    "A planilha não mostra o que a ferramenta concluiu sobre a própria citação, de propósito: o julgamento é cego.",
    "Para conferir o andamento: python -m avaliacao_geracao importar --parcial",
]


class LinhaRubrica(BaseModel):
    id: str
    impressao: str
    pertinente: str | None = None
    fiel: str | None = None
    recomendacao_correta: str | None = None
    justificativa: str | None = None
    observacao: str | None = None


class Problema(BaseModel):
    linha: int | None
    id: str
    motivo: str


def _cortar(texto: str) -> str:
    return texto if len(texto) <= LIMITE_TRECHO else texto[:LIMITE_TRECHO] + " […]"


def _citacoes(r: ItemDaRodada) -> str:
    por_numero = {t.numero: t for t in r.item.contexto}
    partes = []
    for n in r.item.geracao.citacoes:
        t = por_numero[n]
        partes.append(f"[{n}] {t.titulo} — {t.caminho}\n{t.url}#{t.ancora}\n{_cortar(t.texto)}")
    return "\n\n".join(partes)


def _referencia(r: ItemDaRodada, registro: Registro) -> str:
    url = registro.meta(r.item.achado.id_regra).url_canonica
    ancora = next((t for t in r.item.contexto if t.origem == "ancora"), None)
    texto = _cortar(ancora.texto) if ancora is not None else "(trecho âncora ausente no contexto deste achado)"
    return f"{url}\n\n{texto}"


def gerar_planilha(rodada: Rodada, destino: Path, *, forcar: bool = False, registro: Registro | None = None) -> int:
    if destino.exists() and not forcar:
        raise ErroDeAvaliacao(f"{destino} já existe e pode ter vereditos — apague, renomeie ou use --forcar")
    registro = REGISTRO if registro is None else registro
    itens = sorted(
        ((chave, r) for chave, r in rodada.items() if r.item.situacao == "gerado"),
        key=lambda par: (par[1].projeto, par[1].item.achado.id_regra, par[1].item.achado.evidencia.objeto),
    )
    livro = Workbook()
    instrucoes = livro.active
    instrucoes.title = "Instruções"
    for i, linha in enumerate(INSTRUCOES, start=1):
        instrucoes.cell(row=i, column=1, value=linha)
    aba = livro.create_sheet("Rubrica")
    cabecalho = [*COLUNAS_LEITURA, *COLUNAS_ANOTACAO]
    for coluna, nome in enumerate(cabecalho, start=1):
        aba.cell(row=1, column=coluna, value=nome).font = Font(bold=True)
        aba.column_dimensions[aba.cell(row=1, column=coluna).column_letter].width = LARGURAS[nome]
    for numero, (chave, r) in enumerate(itens, start=2):
        meta = registro.meta(r.item.achado.id_regra)
        valores = [
            chave, impressao(r.item), r.projeto, meta.id, meta.titulo, r.item.achado.evidencia.objeto,
            r.item.achado.mensagem, r.item.geracao.explicacao, r.item.geracao.recomendacao,
            _citacoes(r), _referencia(r, registro),
        ]
        for coluna, valor in enumerate(valores, start=1):
            celula = aba.cell(row=numero, column=coluna, value=ILLEGAL_CHARACTERS_RE.sub("", valor))
            celula.data_type = "s"  # Review Focus 1: texto começando com `=` não vira fórmula
            celula.alignment = Alignment(wrap_text=True, vertical="top")
        for coluna in range(len(COLUNAS_LEITURA) + 1, len(cabecalho) + 1):
            celula = aba.cell(row=numero, column=coluna)
            celula.protection = Protection(locked=False)
            celula.alignment = Alignment(wrap_text=True, vertical="top")
    if itens:
        validacao = DataValidation(type="list", formula1=f'"{",".join(VEREDITOS)}"', allow_blank=True)
        for nome in ITENS:
            letra = aba.cell(row=1, column=cabecalho.index(nome) + 1).column_letter
            validacao.add(f"{letra}2:{letra}{len(itens) + 1}")
        aba.add_data_validation(validacao)
    aba.freeze_panes = "B2"
    aba.auto_filter.ref = f"A1:{aba.cell(row=1, column=len(cabecalho)).column_letter}{max(len(itens), 1) + 1}"
    aba.protection.formatColumns = False
    aba.protection.formatRows = False
    aba.protection.autoFilter = False
    aba.protection.sheet = True
    destino.parent.mkdir(parents=True, exist_ok=True)
    livro.save(destino)
    return len(itens)


def _texto(valor) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def ler_planilha(caminho: Path) -> list[tuple[int, LinhaRubrica]]:
    livro = load_workbook(caminho, read_only=True)
    if "Rubrica" not in livro.sheetnames:
        livro.close()
        raise ErroDeAvaliacao("aba 'Rubrica' ausente na planilha — foi renomeada ou apagada?")
    linhas = list(livro["Rubrica"].iter_rows(values_only=True))
    livro.close()
    if not linhas:
        return []
    cabecalho = list(linhas[0])
    faltando = [n for n in ("id", "impressao", *COLUNAS_ANOTACAO) if n not in cabecalho]
    if faltando:
        raise ErroDeAvaliacao(f"coluna(s) ausente(s) no cabeçalho: {', '.join(faltando)}")
    pos = {n: cabecalho.index(n) for n in ("id", "impressao", *COLUNAS_ANOTACAO)}
    lidas = []
    for numero, valores in enumerate(linhas[1:], start=2):
        if valores[pos["id"]] is None:
            continue
        lidas.append((numero, LinhaRubrica(
            id=str(valores[pos["id"]]), impressao=str(valores[pos["impressao"]]),
            **{n: _texto(valores[pos[n]]) for n in COLUNAS_ANOTACAO},
        )))
    return lidas


def validar(lidas: list[tuple[int, LinhaRubrica]], rodada: Rodada, parcial: bool) -> list[Problema]:
    """Não normaliza: um veredito fora da lista é apontado, não corrigido em silêncio."""
    problemas: list[Problema] = []
    vistos: set[str] = set()
    for numero, linha in lidas:
        if linha.id in vistos:
            problemas.append(Problema(linha=numero, id=linha.id, motivo="id duplicado"))
        vistos.add(linha.id)
        if linha.id not in rodada:
            problemas.append(Problema(linha=numero, id=linha.id, motivo="id não existe na rodada em disco"))
        elif impressao(rodada[linha.id].item) != linha.impressao:
            problemas.append(Problema(
                linha=numero, id=linha.id,
                motivo="impressão digital divergente: o texto julgado não é o da rodada em disco",
            ))
        vereditos = [getattr(linha, n) for n in ITENS]
        if all(v is None for v in vereditos) and parcial:
            continue
        if any(v is None for v in vereditos):
            problemas.append(Problema(linha=numero, id=linha.id, motivo="sem veredito em algum item"))
        fora = [v for v in vereditos if v is not None and v not in VEREDITOS]
        if fora:
            problemas.append(Problema(linha=numero, id=linha.id, motivo=f"veredito fora da lista: {fora!r}"))
        if "não" in vereditos and linha.justificativa is None:
            problemas.append(Problema(linha=numero, id=linha.id, motivo="'não' sem justificativa"))
    return problemas


CAMPOS_CSV = ("id", "impressao", *COLUNAS_ANOTACAO)


def gravar_csv(linhas: list[LinhaRubrica], caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS_CSV, lineterminator="\n")
        escritor.writeheader()
        for linha in sorted(linhas, key=lambda l: l.id):
            escritor.writerow({c: getattr(linha, c) or "" for c in CAMPOS_CSV})


def ler_csv(caminho: Path) -> list[LinhaRubrica]:
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"{caminho} não existe — rode `python -m avaliacao_geracao importar`")
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            LinhaRubrica(**{c: (v or None) for c, v in linha.items()} | {"id": linha["id"], "impressao": linha["impressao"]})
            for linha in csv.DictReader(arquivo)
        ]
```

Ajuste no teste de ida e volta: `ler_csv` devolve na ordem do CSV (ordenado por id); com uma linha só, a ordem bate.

Ajuste: o teste `test_importacao_recusa` com `dict(pertinente="sim")` espera o motivo "sem veredito" — a mensagem é "sem veredito em algum item", que contém o texto.

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_planilha.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add avaliacao_geracao/planilha.py tests/test_avaliacao_planilha.py
git commit -m "feat(avaliacao): planilha cega da rubrica, importacao validada e CSV oficial"
git push
```

---

### Task 4: Métricas (`metricas.py`)

**Files:**
- Create: `avaliacao_geracao/metricas.py`
- Test: `tests/test_avaliacao_metricas.py`

**Interfaces:**
- Consumes: `wilson`, `kappa` (Task 1); `Rodada` (Task 2); `LinhaRubrica`, `ITENS` (Task 3).
- Produces: `taxa(sim: int, nao: int, ind: int) -> dict` com chaves `n` (`{"sim","nao","indeterminado"}`), `principal`, `piso`, `teto`, `wilson` (`[baixo, alto]` ou `None`); `medir(linhas: list[LinhaRubrica], rodada: Rodada, *, registro=None, commit: str | None = None) -> dict` com chaves `ambiente`, `itens` (por item: `total`, `por_regra`, `por_categoria`), `utilizavel` (mesmo formato), `descarte`, `concordancia` (`pertinente`, `fiel`: `tabela` `{a,b,c,d}`, `concordancia`, `kappa`, `n`).

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_metricas.py`:

```python
"""Métricas da rubrica: taxas, recortes, utilizável, descarte e humano × automático."""

import pytest

from avaliacao_geracao.metricas import medir, taxa
from avaliacao_geracao.planilha import LinhaRubrica
from avaliacao_geracao.rodada import ItemDaRodada, id_do_achado, impressao
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.rules.base import RegraMeta
from core.rules.registry import Registro
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto


def _registro() -> Registro:
    registro = Registro()
    for id_regra, categoria in [("MOD-001", "modelagem"), ("DAX-001", "dax")]:
        registro.registrar(RegraMeta(id=id_regra, titulo=id_regra, categoria=categoria, severidade="alta",
                                     url_canonica="https://learn.microsoft.com/x", termos_consulta=("t",),
                                     recomendacao_padrao=RECOMENDACAO_PADRAO), lambda m: [])
    return registro


def _gerado(id_regra, objeto, cita_ancora=True, divergencias=()) -> AchadoEnriquecido:
    return AchadoEnriquecido(
        achado=achado(id_regra, objeto=objeto), contexto=contexto(2),
        geracao=Geracao(explicacao=f"e {objeto}", recomendacao="r", citacoes=[1]),
        situacao="gerado", cita_ancora=cita_ancora, fidelidade=Fidelidade(divergencias=list(divergencias)), modelo="m",
    )


def _cenario():
    itens = [
        _gerado("MOD-001", "A", cita_ancora=True),
        _gerado("MOD-001", "B", cita_ancora=False, divergencias=["42"]),
        _gerado("DAX-001", "C", cita_ancora=True),
        AchadoEnriquecido(achado=achado("MOD-001", objeto="D"), contexto=contexto(1), situacao="sem_fundamentacao",
                          motivo_descarte="json_invalido", modelo="m"),
    ]
    rodada = {id_do_achado("P1", i): ItemDaRodada("P1", i) for i in itens}
    vereditos = {"A": ("sim", "sim", "sim"), "B": ("não", "não", "sim"), "C": ("sim", "sim", "indeterminado")}
    linhas = [
        LinhaRubrica(id=id_do_achado("P1", i), impressao=impressao(i), pertinente=v[0], fiel=v[1],
                     recomendacao_correta=v[2], justificativa="j" if "não" in v else None)
        for i in itens[:3] for v in [vereditos[i.achado.evidencia.objeto]]
    ]
    return linhas, rodada


def test_taxa_principal_piso_teto_wilson():
    t = taxa(sim=2, nao=1, ind=1)
    assert (t["principal"], t["piso"], t["teto"]) == pytest.approx((2 / 3, 2 / 4, 3 / 4))
    assert t["n"] == {"sim": 2, "nao": 1, "indeterminado": 1}
    assert t["wilson"][0] < 2 / 3 < t["wilson"][1]


def test_recorte_so_de_indeterminados_nao_divide_por_zero():
    """Review Focus 4."""
    t = taxa(sim=0, nao=0, ind=3)
    assert (t["principal"], t["wilson"]) == (None, None)
    assert (t["piso"], t["teto"]) == (0.0, 1.0)


def test_medir_itens_recortes_utilizavel():
    linhas, rodada = _cenario()
    r = medir(linhas, rodada, registro=_registro(), commit="abc1234")
    assert r["ambiente"]["commit"] == "abc1234" and r["ambiente"]["linhas"] == 3
    assert r["itens"]["pertinente"]["total"]["n"] == {"sim": 2, "nao": 1, "indeterminado": 0}
    assert r["itens"]["pertinente"]["por_regra"]["MOD-001"]["principal"] == 0.5
    assert r["itens"]["recomendacao_correta"]["por_categoria"]["dax"]["n"]["indeterminado"] == 1
    # A: utilizável; B: não; C: indeterminado
    assert r["utilizavel"]["total"]["n"] == {"sim": 1, "nao": 1, "indeterminado": 1}


def test_descarte_e_automatico():
    linhas, rodada = _cenario()
    d = medir(linhas, rodada, registro=_registro())["descarte"]
    assert (d["achados"], d["sem_fundamentacao"], d["por_motivo"]) == (4, 1, {"json_invalido": 1})


def test_concordancia_humano_automatico():
    linhas, rodada = _cenario()
    c = medir(linhas, rodada, registro=_registro())["concordancia"]
    # pertinente: A auto sim/humano sim; B auto não/humano não; C auto sim/humano sim
    assert c["pertinente"]["tabela"] == {"a": 2, "b": 0, "c": 0, "d": 1}
    assert c["pertinente"]["concordancia"] == 1.0 and c["pertinente"]["kappa"] == pytest.approx(1.0)
    # fiel: automático "sem divergência"; B tem divergência e humano disse não
    assert c["fiel"]["tabela"] == {"a": 2, "b": 0, "c": 0, "d": 1}
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_metricas.py -q`
Expected: FAIL — `ModuleNotFoundError: avaliacao_geracao.metricas`.

- [ ] **Step 2: Implementar**

`avaliacao_geracao/metricas.py`:

```python
"""Métricas da rubrica da geração (spec de 13/10/2026, seção 5).

Mesmo formato do gabarito: principal sem os indeterminados, piso e teto com eles
contra e a favor, e o intervalo de Wilson sobre a principal.
"""

from collections import Counter, defaultdict
from datetime import datetime

from avaliacao_geracao.estatistica import kappa, wilson
from avaliacao_geracao.planilha import ITENS, LinhaRubrica
from avaliacao_geracao.rodada import Rodada
from core.rules.registry import Registro
from core.rules.todas import REGISTRO


def _razao(numerador: int, denominador: int) -> float | None:
    return numerador / denominador if denominador else None


def taxa(sim: int, nao: int, ind: int) -> dict:
    intervalo = wilson(sim, sim + nao)
    return {
        "n": {"sim": sim, "nao": nao, "indeterminado": ind},
        "principal": _razao(sim, sim + nao),
        "piso": _razao(sim, sim + nao + ind),
        "teto": _razao(sim + ind, sim + nao + ind),
        "wilson": list(intervalo) if intervalo else None,
    }


def _contar(vereditos: list[str]) -> dict:
    c = Counter(vereditos)
    return taxa(c["sim"], c["não"], c["indeterminado"])


def _recortes(pares: list[tuple[str, str, str]]) -> dict:
    """`pares` = (regra, categoria, veredito)."""
    por_regra, por_categoria = defaultdict(list), defaultdict(list)
    for regra, categoria, veredito in pares:
        por_regra[regra].append(veredito)
        por_categoria[categoria].append(veredito)
    return {
        "total": _contar([v for _, _, v in pares]),
        "por_regra": {r: _contar(v) for r, v in sorted(por_regra.items())},
        "por_categoria": {c: _contar(v) for c, v in sorted(por_categoria.items())},
    }


def _utilizavel(linha: LinhaRubrica) -> str:
    vereditos = [getattr(linha, n) for n in ITENS]
    if "não" in vereditos:
        return "não"
    return "sim" if all(v == "sim" for v in vereditos) else "indeterminado"


def _concordancia(pares: list[tuple[bool, str]]) -> dict:
    """`pares` = (automático diz sim, veredito humano); indeterminados ficam de fora."""
    tabela = {"a": 0, "b": 0, "c": 0, "d": 0}
    for automatico, humano in pares:
        if humano == "indeterminado":
            continue
        casa = ("a" if humano == "sim" else "b") if automatico else ("c" if humano == "sim" else "d")
        tabela[casa] += 1
    n = sum(tabela.values())
    return {
        "tabela": tabela,
        "n": n,
        "concordancia": _razao(tabela["a"] + tabela["d"], n),
        "kappa": kappa(tabela["a"], tabela["b"], tabela["c"], tabela["d"]),
    }


def medir(linhas: list[LinhaRubrica], rodada: Rodada, *, registro: Registro | None = None,
          commit: str | None = None) -> dict:
    registro = REGISTRO if registro is None else registro
    julgadas = [(l, rodada[l.id].item) for l in linhas if all(getattr(l, n) for n in ITENS)]

    def chave(item):
        meta = registro.meta(item.achado.id_regra)
        return meta.id, meta.categoria

    itens = {
        n: _recortes([(*chave(item), getattr(l, n)) for l, item in julgadas]) for n in ITENS
    }
    todos = [r.item for r in rodada.values()]
    descartados = [i for i in todos if i.situacao == "sem_fundamentacao"]
    return {
        "ambiente": {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "commit": commit,
            "linhas": len(julgadas),
        },
        "itens": itens,
        "utilizavel": _recortes([(*chave(item), _utilizavel(l)) for l, item in julgadas]),
        "descarte": {
            "achados": len(todos),
            "sem_fundamentacao": len(descartados),
            "taxa": _razao(len(descartados), len(todos)),
            "por_motivo": dict(sorted(Counter(i.motivo_descarte for i in descartados).items())),
        },
        "concordancia": {
            "pertinente": _concordancia([(bool(item.cita_ancora), l.pertinente) for l, item in julgadas]),
            "fiel": _concordancia([(not item.fidelidade.divergencias, l.fiel) for l, item in julgadas]),
        },
    }
```

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_metricas.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add avaliacao_geracao/metricas.py tests/test_avaliacao_metricas.py
git commit -m "feat(avaliacao): metricas da rubrica com Wilson, descarte e concordancia humano x automatico"
git push
```

---

### Task 5: Consolidação (`consolidacao.py`)

**Files:**
- Create: `avaliacao_geracao/consolidacao.py`
- Test: `tests/test_avaliacao_consolidacao.py`

**Interfaces:**
- Consumes: `wilson` (Task 1).
- Produces: `PASTA_RESULTADOS: Path` (= `RAIZ_REPO / "eval" / "results"`); `ORIGENS: dict[str, str]`; `consolidar(pasta: Path = PASTA_RESULTADOS) -> dict` com chaves `regras`, `regras_pos_correcao`, `recuperacao`, `complementares`, `geracao`, cada uma com `origem`.

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_consolidacao.py`:

```python
"""Consolidado: fonte única das tabelas da monografia."""

import json

import pytest

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.consolidacao import ORIGENS, consolidar


def _matriz(vp, fp, fn):
    return {"matriz": {"vp": vp, "fp": fp, "fn": fn, "vn": 0, "ind_marcados": 0, "ind_nao_marcados": 0},
            "taxas": {"precisao": {"principal": vp / (vp + fp)}, "recall": {"principal": vp / (vp + fn)}}}


def _regras():
    return {"por_regra": {"MOD-001": _matriz(10, 0, 0)}, "por_categoria": {"modelagem": _matriz(46, 6, 6)},
            "total_micro": _matriz(46, 6, 6), "macro": {"precisao": 0.88}}


def _escrever(pasta, sem=None):
    conteudos = {
        "regras": _regras(),
        "regras_pos_correcao": _regras(),
        "recuperacao": {
            "decisao": {"vencedora": {"busca": "bm25"}, "justificativa": "j"},
            "resultados": [{"configuracao": {"busca": "densa"}, "macro": {"mrr": 0.1}},
                           {"configuracao": {"busca": "bm25"}, "macro": {"mrr": 0.9, "acerto": {"5": 1.0}}}],
        },
        "complementares": {"por_busca": {"bm25": {"macro": {"principal": 0.62}}}, "decisao": {"vencedora": "bm25"}},
    }
    for chave, nome in ORIGENS.items():
        if chave != sem:
            (pasta / nome).write_text(json.dumps(conteudos[chave]), encoding="utf-8")
    if sem != "geracao":
        (pasta / "geracao-2026-10-14.json").write_text(json.dumps({"itens": {"velho": 1}}), encoding="utf-8")
        (pasta / "geracao-2026-10-15.json").write_text(json.dumps({"itens": {"novo": 1}}), encoding="utf-8")


def test_consolida_com_wilson_e_origens(tmp_path):
    _escrever(tmp_path)
    c = consolidar(tmp_path)
    assert c["regras"]["origem"] == ORIGENS["regras"]
    assert [round(x, 4) for x in c["regras"]["total_micro"]["wilson"]["precisao"]] == [0.7703, 0.946]
    assert c["regras"]["por_regra"]["MOD-001"]["wilson"]["recall"][1] == 1.0
    assert c["recuperacao"]["macro"]["mrr"] == 0.9
    assert c["complementares"]["macro"] == {"bm25": {"principal": 0.62}}
    assert c["geracao"]["origem"] == "geracao-2026-10-15.json" and c["geracao"]["itens"] == {"novo": 1}


@pytest.mark.parametrize("sem", [*ORIGENS, "geracao"])
def test_origem_ausente_diz_qual(tmp_path, sem):
    _escrever(tmp_path, sem=sem)
    with pytest.raises(ErroDeAvaliacao, match="falta"):
        consolidar(tmp_path)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_consolidacao.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 2: Implementar**

`avaliacao_geracao/consolidacao.py`:

```python
"""Consolidado dos resultados: a fonte única das tabelas da monografia.

O resultado oficial da detecção é o da tag `regras-gt`; o arquivo de origem não
é alterado — o Wilson é acrescentado só aqui. A pós-correção vai junto, rotulada
como análise de erros.
"""

import copy
import json
from pathlib import Path

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.estatistica import wilson
from rag.avaliacao import RAIZ_REPO

PASTA_RESULTADOS = RAIZ_REPO / "eval" / "results"
ORIGENS = {
    "regras": "regras-2026-10-12.json",
    "regras_pos_correcao": "regras-2026-10-12-pos-correcao.json",
    "recuperacao": "recuperacao-2026-10-11.json",
    "complementares": "complementares-2026-10-12.json",
}


def _ler(pasta: Path, nome: str) -> dict:
    caminho = pasta / nome
    if not caminho.is_file():
        raise ErroDeAvaliacao(f"falta {nome} em {pasta}")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _wilson_da_matriz(bloco: dict) -> dict:
    m = bloco["matriz"]
    precisao = wilson(m["vp"], m["vp"] + m["fp"])
    recall = wilson(m["vp"], m["vp"] + m["fn"])
    return {"precisao": list(precisao) if precisao else None, "recall": list(recall) if recall else None}


def _com_wilson(regras: dict, origem: str, rotulo: str) -> dict:
    saida = copy.deepcopy(regras)
    for grupo in ("por_regra", "por_categoria"):
        for bloco in saida.get(grupo, {}).values():
            bloco["wilson"] = _wilson_da_matriz(bloco)
    if "total_micro" in saida:
        saida["total_micro"]["wilson"] = _wilson_da_matriz(saida["total_micro"])
    return {"origem": origem, "rotulo": rotulo, **saida}


def consolidar(pasta: Path = PASTA_RESULTADOS) -> dict:
    regras = _ler(pasta, ORIGENS["regras"])
    pos = _ler(pasta, ORIGENS["regras_pos_correcao"])
    recuperacao = _ler(pasta, ORIGENS["recuperacao"])
    complementares = _ler(pasta, ORIGENS["complementares"])
    geracoes = sorted(pasta.glob("geracao-*.json"))
    if not geracoes:
        raise ErroDeAvaliacao(f"falta geracao-<data>.json em {pasta} — rode `python -m avaliacao_geracao medir`")

    vencedora = recuperacao["decisao"]["vencedora"]
    escolhida = next((r for r in recuperacao["resultados"] if r["configuracao"] == vencedora), None)
    if escolhida is None:
        raise ErroDeAvaliacao(f"falta o resultado da configuração vencedora em {ORIGENS['recuperacao']}")
    return {
        "regras": _com_wilson(regras, ORIGENS["regras"], "resultado oficial (tag regras-gt)"),
        "regras_pos_correcao": _com_wilson(pos, ORIGENS["regras_pos_correcao"], "análise de erros"),
        "recuperacao": {
            "origem": ORIGENS["recuperacao"], "configuracao": vencedora, "macro": escolhida["macro"],
            "justificativa": recuperacao["decisao"].get("justificativa"),
        },
        "complementares": {
            "origem": ORIGENS["complementares"],
            "macro": {busca: v["macro"] for busca, v in complementares["por_busca"].items()},
            "decisao": complementares["decisao"],
        },
        "geracao": {"origem": geracoes[-1].name, **json.loads(geracoes[-1].read_text(encoding="utf-8"))},
    }
```

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_consolidacao.py -q` → PASS.

- [ ] **Step 4: Commit**

```bash
git add avaliacao_geracao/consolidacao.py tests/test_avaliacao_consolidacao.py
git commit -m "feat(avaliacao): consolidado dos resultados com Wilson nas regras"
git push
```

---

### Task 6: CLI (`python -m avaliacao_geracao`)

**Files:**
- Create: `avaliacao_geracao/__main__.py`
- Test: `tests/test_avaliacao_comando.py`

**Interfaces:**
- Consumes: tudo das Tasks 2–5; `ClienteOllama`, `MODELO_PADRAO`, `ClienteComCache`, `PASTA_CACHE`, `BaseRag`, erros da auditoria.
- Produces: `main(argv: list[str] | None = None) -> int` com subcomandos `auditar`, `gerar [--forcar]`, `importar [--parcial]`, `medir`, `consolidar`. Pontos de troca dos testes (atributos do módulo): `PASTA_RODADA`, `PASTA_PBIP`, `PLANILHA`, `CSV_OFICIAL`, `PASTA_RESULTADOS`, `criar_llm()`, `carregar_base()`, `commit_atual()`.

- [ ] **Step 1: Testes que falham**

`tests/test_avaliacao_comando.py`:

```python
"""CLI da avaliação: fluxo completo com LLM falso e mensagens em vez de traceback."""

import json

import pytest
from openpyxl import load_workbook

import avaliacao_geracao.__main__ as comando
from conftest import escrever_pbip, modelo_tmsl, tabela
from core import auditoria
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    monkeypatch.setattr(auditoria, "REGISTRO", registro)
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {"MOD-001": gabarito()})
    for nome in ["PASTA_RODADA", "PLANILHA", "CSV_OFICIAL", "PASTA_RESULTADOS"]:
        destino = {"PASTA_RODADA": tmp_path / "rodada", "PLANILHA": tmp_path / "r.xlsx",
                   "CSV_OFICIAL": tmp_path / "r.csv", "PASTA_RESULTADOS": tmp_path / "results"}[nome]
        monkeypatch.setattr(comando, nome, destino)
    pbip = tmp_path / "pbip"
    escrever_pbip(pbip / "P1_A", nome="P1_A", model_bim=modelo_tmsl([tabela("T1"), tabela("T2")]))
    monkeypatch.setattr(comando, "PASTA_PBIP", pbip)
    monkeypatch.setattr(comando, "criar_llm", lambda: LLMFalso())
    monkeypatch.setattr(comando, "carregar_base", base_padrao)
    monkeypatch.setattr(comando, "commit_atual", lambda: "abc1234")
    monkeypatch.setattr(comando, "REGISTRO_DA_PLANILHA", registro)
    return tmp_path


def _anotar_tudo(caminho):
    livro = load_workbook(caminho)
    aba = livro["Rubrica"]
    cabecalho = [c.value for c in next(aba.iter_rows(min_row=1, max_row=1))]
    for linha in range(2, aba.max_row + 1):
        for nome in ["pertinente", "fiel", "recomendacao_correta"]:
            aba.cell(row=linha, column=cabecalho.index(nome) + 1, value="sim")
    livro.save(caminho)


def test_fluxo_completo(ambiente, capsys):
    assert comando.main(["auditar"]) == 0
    assert "fora do cache: 2" in capsys.readouterr().out
    assert comando.main(["gerar"]) == 0
    assert comando.main(["gerar"]) == 1  # não sobrescreve
    assert comando.main(["importar"]) == 1  # sem vereditos
    assert comando.main(["importar", "--parcial"]) == 0
    _anotar_tudo(ambiente / "r.xlsx")
    assert comando.main(["importar"]) == 0
    assert comando.main(["medir"]) == 0
    geracao = next((ambiente / "results").glob("geracao-*.json"))
    assert json.loads(geracao.read_text(encoding="utf-8"))["utilizavel"]["total"]["principal"] == 1.0
    capsys.readouterr().out.encode("ascii")


def test_auditar_com_ollama_fora_do_ar_sai_com_mensagem(ambiente, monkeypatch, capsys):
    monkeypatch.setattr(comando, "criar_llm", lambda: LLMFalso(falha_no_aquecimento=True))
    assert comando.main(["auditar"]) == 1
    assert "aquecimento" in capsys.readouterr().err


def test_medir_sem_csv_e_consolidar_sem_origem_saem_com_mensagem(ambiente, capsys):
    assert comando.main(["medir"]) == 1
    assert comando.main(["consolidar"]) == 1
    assert "erro:" in capsys.readouterr().err
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_comando.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 2: Implementar**

`avaliacao_geracao/__main__.py`:

```python
"""`python -m avaliacao_geracao auditar|gerar|importar|medir|consolidar`."""

import argparse
import json
import subprocess
import sys
from datetime import date

from avaliacao_geracao import ErroDeAvaliacao
from avaliacao_geracao.consolidacao import PASTA_RESULTADOS, consolidar
from avaliacao_geracao.metricas import medir
from avaliacao_geracao.planilha import CSV_OFICIAL, PLANILHA, gerar_planilha, gravar_csv, ler_csv, ler_planilha, validar
from avaliacao_geracao.rodada import PASTA_PBIP, PASTA_RODADA, auditar, carregar_rodada, projetos_da_avaliacao
from core.analise.cache import PASTA_CACHE, ClienteComCache
from core.analise.contexto import ErroDeContexto
from core.analise.llm import MODELO_PADRAO, ClienteOllama
from core.auditoria import ErroDeAuditoria
from core.ingest import ErroEstruturaPbip
from core.rules.todas import REGISTRO
from rag.avaliacao import RAIZ_REPO
from rag.indice import BaseRag, ErroDeIndice

REGISTRO_DA_PLANILHA = REGISTRO


def _ascii(texto: str) -> str:
    return texto.encode("ascii", "replace").decode("ascii")


def criar_llm():
    return ClienteComCache(ClienteOllama(MODELO_PADRAO), PASTA_CACHE)


def carregar_base():
    return BaseRag.carregar()


def commit_atual() -> str | None:
    try:
        saida = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ_REPO,
                               capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return saida.stdout.strip() or None


def _gravar_json(dados: dict, prefixo: str) -> str:
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_RESULTADOS / f"{prefixo}-{date.today().isoformat()}.json"
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return str(destino)


def _auditar() -> int:
    pastas = projetos_da_avaliacao(PASTA_PBIP)
    resumo = auditar(pastas, PASTA_RODADA, llm=criar_llm(), base=carregar_base())
    print(_ascii(f"Projetos: {resumo.projetos} | achados: {resumo.achados} | gerados: {resumo.gerados} "
                 f"| fora do cache: {resumo.fora_do_cache}"))
    if resumo.fora_do_cache:
        print("Aviso: respostas fora do cache podem ter mudado o texto de uma rodada anterior.")
    return 0


def _gerar(forcar: bool) -> int:
    linhas = gerar_planilha(carregar_rodada(PASTA_RODADA), PLANILHA, forcar=forcar, registro=REGISTRO_DA_PLANILHA)
    print(_ascii(f"Planilha com {linhas} linha(s): {PLANILHA}"))
    return 0


def _importar(parcial: bool) -> int:
    rodada = carregar_rodada(PASTA_RODADA)
    lidas = ler_planilha(PLANILHA)
    problemas = validar(lidas, rodada, parcial)
    if problemas:
        for p in problemas:
            print(_ascii(f"linha {p.linha} ({p.id}): {p.motivo}"), file=sys.stderr)
        print(_ascii(f"erro: {len(problemas)} problema(s); nada gravado"), file=sys.stderr)
        return 1
    completas = [l for _, l in lidas if l.pertinente and l.fiel and l.recomendacao_correta]
    gravar_csv(completas, CSV_OFICIAL)
    print(_ascii(f"Importadas {len(completas)} de {len(lidas)} linha(s) em {CSV_OFICIAL}"))
    return 0


def _medir() -> int:
    resultado = medir(ler_csv(CSV_OFICIAL), carregar_rodada(PASTA_RODADA), commit=commit_atual())
    print(_ascii(f"Resultado em {_gravar_json(resultado, 'geracao')}"))
    return 0


def _consolidar() -> int:
    print(_ascii(f"Consolidado em {_gravar_json(consolidar(PASTA_RESULTADOS), 'consolidado')}"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m avaliacao_geracao")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("auditar", help="auditoria completa de P1-P7, com cache")
    gerar = sub.add_parser("gerar", help="gera a planilha cega da rubrica")
    gerar.add_argument("--forcar", action="store_true")
    importar = sub.add_parser("importar", help="valida a planilha e grava o CSV oficial")
    importar.add_argument("--parcial", action="store_true")
    sub.add_parser("medir", help="mede a rubrica")
    sub.add_parser("consolidar", help="junta todos os resultados")
    args = parser.parse_args(argv)
    try:
        if args.comando == "auditar":
            return _auditar()
        if args.comando == "gerar":
            return _gerar(args.forcar)
        if args.comando == "importar":
            return _importar(args.parcial)
        if args.comando == "medir":
            return _medir()
        return _consolidar()
    except (ErroDeAvaliacao, ErroDeAuditoria, ErroDeContexto, ErroDeIndice, ErroEstruturaPbip) as erro:
        print(_ascii(f"erro: {erro}"), file=sys.stderr)
        return 1
    except (ValueError, OSError) as erro:
        print(_ascii(f"erro: {type(erro).__name__}: {erro}"), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

Nota: os comandos leem `PASTA_RODADA`, `PLANILHA`, `CSV_OFICIAL`, `PASTA_RESULTADOS` e `PASTA_PBIP` **deste módulo** (importados por nome), para os testes trocarem tudo num lugar só. `consolidar(PASTA_RESULTADOS)` recebe a pasta explicitamente pelo mesmo motivo.

- [ ] **Step 3: Rodar** — `.\.venv\Scripts\python.exe -m pytest tests/test_avaliacao_comando.py -q` → PASS.

- [ ] **Step 4: Suíte inteira** — `.\.venv\Scripts\python.exe -m pytest -q` → tudo passa.

- [ ] **Step 5: Commit**

```bash
git add avaliacao_geracao/__main__.py tests/test_avaliacao_comando.py
git commit -m "feat(avaliacao): CLI auditar, gerar, importar, medir e consolidar"
git push
```

---

### Task 7: Rodada real e planilha para o Fred

**Files:**
- Modify: `docs/project/progress-log.md`, `docs/project/status.md`

- [ ] **Step 1: Rodada** — com o Ollama no ar e `HF_HUB_OFFLINE=1`:

```powershell
.\.venv\Scripts\python.exe -m avaliacao_geracao auditar
.\.venv\Scripts\python.exe -m avaliacao_geracao auditar
```

Expected: a primeira com "achados: 61" (os 61 da só regras em P1–P7) e o tempo de ~10 min; a segunda com "fora do cache: 0" em segundos — prova de que a rodada é reproduzível. Anotar gerados, descartados e tempo.

- [ ] **Step 2: Planilha** — `.\.venv\Scripts\python.exe -m avaliacao_geracao gerar`. Abrir e conferir: uma linha por achado gerado, aba "Instruções", colunas de anotação com lista, nada de sinal automático.

- [ ] **Step 3: Registrar** — progress-log com os números da rodada e "**Próximo passo:** o Fred anota `eval/gabarito/rubrica-geracao-P1-P7.xlsx` (~3,5–4 h; `importar --parcial` para conferir); depois `importar`, `medir`, `consolidar`". Status: Fase 5 em andamento.

- [ ] **Step 4: Commit**

```bash
git add docs/project
git commit -m "docs: rodada da avaliacao da geracao em P1-P7 e planilha da rubrica prontas"
git push
```

**Aqui a execução para:** a anotação é do Fred. A Task 8 roda depois dela.

---

### Task 8 (depois da anotação): importar, medir, consolidar e registrar

- [ ] **Step 1:** `.\.venv\Scripts\python.exe -m avaliacao_geracao importar` → código 0, 61 − descartados linhas.
- [ ] **Step 2:** `.\.venv\Scripts\python.exe -m avaliacao_geracao medir` e `... consolidar` → `eval/results/geracao-<data>.json` e `consolidado-<data>.json`.
- [ ] **Step 3:** Registrar no progress-log a tabela dos três itens e do "utilizável" (principal, piso, teto, Wilson), o descarte, as duas concordâncias com kappa, e os "não" mais frequentes por regra; atualizar `status.md` (seção 3 e próximos passos) e oferecer a atualização da página do orientador.
- [ ] **Step 4: Commit**

```bash
git add eval/rubrica_geracao.csv eval/results docs/project
git commit -m "eval: rubrica da geracao medida e resultados consolidados"
git push
```
