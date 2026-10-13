# Interface Streamlit — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar à auditoria uma interface Streamlit para um analista de BI: nova auditoria (completa ou só regras) com progresso por achado, abertura de resultado salvo, painel do que foi examinado, filtros, tabela e detalhe do achado com avisos de confiança e tradução sob demanda dos trechos citados.

**Architecture:** O pipeline (`core/auditoria.py`) ganha o modo só regras, o callback de progresso e nomes de arquivo com hora. A interface fica em três módulos: `app/consulta.py` (puro: avisos, linhas, filtros, resumos, painel), `app/execucao.py` (sem Streamlit: roda, grava, lê, traduz e converte erro em mensagem) e `app/streamlit_app.py` (só renderização e estado da sessão). Execução síncrona com barra de progresso.

**Tech Stack:** Python 3.11, Pydantic 2, Streamlit 1.64.0 (`streamlit.testing.v1.AppTest` nos testes), pytest, Ollama local via `core.analise.llm`.

**Spec:** `docs/superpowers/specs/2026-10-13-interface-streamlit-design.md`

## Global Constraints

- Todo o projeto em português: código, nomes de função e de teste, docstrings, mensagens, commits.
- Textos da interface em português do Brasil; toda falha vira mensagem na tela, nunca traceback.
- Falha do Ollama numa auditoria **completa** continua abortando (`ErroDeAuditoria`, ADR-003); o modo só regras é sempre escolha explícita, nunca degradação automática.
- JSONs gravados antes desta mudança (formato de 11/10/2026, sem `modo`) continuam abrindo como resultado `completo`.
- A tradução é só de exibição: nada traduzido é gravado no resultado; o original continua visível ao lado.
- Dependência nova: `streamlit==1.64.0` (seção "Fase 4 - interface" do `requirements.txt`). Jinja2 e Playwright não entram.
- Rodar Python sempre pelo venv: `.\.venv\Scripts\python.exe -m pytest ...`.
- A suíte completa leva ~7 min; durante as tarefas rode só os arquivos de teste tocados, e a suíte inteira no fim de cada tarefa que mexe em `core/`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push na branch `fase4-interface` a cada tarefa (autorizado).

## Review Focus

1. **Exceção não prevista durante a auditoria na interface** (bug em regra, `KeyError` qualquer): a interface não pode ficar com os controles travados (`executando` preso em `True`) nem mostrar traceback — espera-se mensagem "erro inesperado" e controles de volta. Teste na Task 8.
2. **Nome de arquivo enviado com caminho** (`../../x.zip`, `C:\x\y.zip`): o `.zip` precisa ser gravado dentro da pasta temporária, com só o nome final. Teste na Task 7.
3. **Seleção da tabela que sobra depois de filtrar** (linha 5 selecionada, filtro deixa 2 linhas) e **resultado com zero achados**: o detalhe não pode estourar índice — cai no primeiro achado visível, ou em nenhum. Teste na Task 6.
4. **JSON aberto que não é desta ferramenta** (JSON válido de outro formato, bytes que não são UTF-8, resultado com regra que esta versão não conhece): mensagem clara, e o resultado aberto antes continua na tela. Testes nas Tasks 7 e 8.
5. **Trecho longo demais para traduzir** (o Ollama recusa por contexto, `ContextoExcedido`): mensagem local no trecho, o detalhe segue. Teste na Task 7.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `core/analise/base.py` (modificar) | Situação `so_regras`, `modelo: str \| None`, validador dos três estados, `AchadoEnriquecido.so_regras()` |
| `core/auditoria.py` (modificar) | `modo`, `modelo_llm: str \| None`, validador de modo; `run_audit` com só regras e `ao_progredir`; `resumir` e `gravar` cientes do modo; `--so-regras` |
| `core/analise/traducao.py` (criar) | `traduzir_trecho`, `ErroDeTraducao` |
| `rag/catalogo.py` (modificar) | `url_em_portugues` |
| `app/__init__.py` (criar) | Pacote |
| `app/consulta.py` (criar) | Avisos, linhas, filtros, opções de filtro, resumo, painel examinado, escolha do achado |
| `app/execucao.py` (criar) | `executar`, `salvar_envio`, `listar_salvos`, `ler_resultado`, `traduzir`, `ErroParaUsuario` |
| `app/streamlit_app.py` (criar) | Renderização e estado da sessão |
| `tests/fixtures/resultado-formato-2026-10-11.json` (criar) | JSON no formato antigo, para a compatibilidade |
| `tests/test_analise_base.py`, `tests/test_auditoria.py` (modificar) | Contrato e pipeline |
| `tests/test_analise_traducao.py`, `tests/test_rag_catalogo.py` (criar/modificar) | Tradução e link em pt-BR |
| `tests/test_app_consulta.py`, `tests/test_app_execucao.py`, `tests/test_app_interface.py` (criar) | Interface |

---

### Task 1: Situação `so_regras` no contrato e compatibilidade com o formato antigo

**Files:**
- Modify: `core/analise/base.py` (tipo `Situacao`, campo `modelo`, validador `_situacao_coerente`, novo classmethod)
- Modify: `core/auditoria.py` (classe `ResultadoAuditoria`)
- Create: `tests/fixtures/resultado-formato-2026-10-11.json`
- Test: `tests/test_analise_base.py`, `tests/test_auditoria.py`

**Interfaces:**
- Produces: `Situacao = Literal["gerado", "sem_fundamentacao", "so_regras"]`; `AchadoEnriquecido.modelo: str | None`; `AchadoEnriquecido.so_regras(achado: Achado) -> AchadoEnriquecido`; `ModoAuditoria = Literal["completo", "so_regras"]` em `core/auditoria.py`; `ResultadoAuditoria.modo: ModoAuditoria = "completo"`; `ResultadoAuditoria.modelo_llm: str | None`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `tests/test_analise_base.py`:

```python
def test_so_regras_coerente_e_aceito():
    item = AchadoEnriquecido.so_regras(achado())
    assert (item.situacao, item.contexto, item.modelo) == ("so_regras", [], None)


def test_so_regras_nao_pode_ter_contexto_nem_geracao():
    base = dict(achado=achado(), situacao="so_regras", modelo=None)
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(**base, contexto=contexto(1))
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(
            **base, contexto=[], geracao=Geracao(explicacao="e", recomendacao="r", citacoes=[1])
        )
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(**base, contexto=[], segundos=1.0)


def test_so_regras_nao_pode_ter_modelo_e_os_outros_precisam():
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(achado=achado(), contexto=[], situacao="so_regras", modelo="m")
    with pytest.raises(ValidationError, match="coerente"):
        _gerado(modelo=None)
    with pytest.raises(ValidationError, match="coerente"):
        _descartado(modelo=None)


def test_recomendacao_final_em_so_regras_e_a_padrao():
    item = AchadoEnriquecido.so_regras(achado())
    assert item.recomendacao_final(meta()) == meta().recomendacao_padrao
```

Acrescentar ao fim de `tests/test_auditoria.py` (e `from pathlib import Path` no topo, junto dos imports):

```python
FIXTURE_FORMATO_ANTIGO = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def test_json_no_formato_de_11_10_abre_como_completo():
    resultado = ResultadoAuditoria.model_validate_json(FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8"))
    assert (resultado.modo, resultado.modelo_llm) == ("completo", "qwen2.5:7b-instruct-q4_K_M")
    assert [a.situacao for a in resultado.achados] == ["gerado", "sem_fundamentacao"]


def _resultado(**extra) -> ResultadoAuditoria:
    from core.analise.base import AchadoEnriquecido
    from core.rules.runner import ResultadoRegras
    from fabricas_analise import achado as fabrica_achado

    campos = dict(
        projeto="P", modo="so_regras", modelo_llm=None, gerado_em="2026-10-13T15:30:00",
        regras=ResultadoRegras(regras_executadas=1),
        achados=[AchadoEnriquecido.so_regras(fabrica_achado())], segundos_total=0.1,
    )
    campos.update(extra)
    return ResultadoAuditoria(**campos)


def test_resultado_so_regras_coerente_e_aceito():
    assert _resultado().modo == "so_regras"


def test_resultado_com_modo_e_modelo_que_nao_batem_e_recusado():
    with pytest.raises(ValueError, match="incoerente"):
        _resultado(modelo_llm="m")
    with pytest.raises(ValueError, match="incoerente"):
        _resultado(modo="completo")
```

- [ ] **Step 2: Criar a fixture no formato antigo**

`tests/fixtures/resultado-formato-2026-10-11.json` — exatamente os campos que `gravar()` escrevia em 11/10 (sem `modo`):

```json
{
  "projeto": "Formato-antigo",
  "modelo_llm": "qwen2.5:7b-instruct-q4_K_M",
  "gerado_em": "2026-10-11T21:40:12",
  "regras": {
    "achados": [],
    "regras_com_falha": [],
    "regras_executadas": 9,
    "lacunas_de_expressao": [],
    "expressoes_analisadas": 105,
    "falha_na_varredura": null
  },
  "achados": [
    {
      "achado": {
        "id_regra": "MOD-001",
        "evidencia": {"tipo_objeto": "tabela", "objeto": "LocalDateTable_1", "tabela": "LocalDateTable_1", "trecho": null, "detalhe": {}},
        "mensagem": "A tabela oculta 'LocalDateTable_1' foi gerada pelo Tempo automático de data/hora."
      },
      "contexto": [
        {"numero": 1, "id_pagina": "learn:power-bi/guidance/auto-date-time", "url": "https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time", "titulo": "Auto date/time guidance in Power BI Desktop", "ancora": "recommendations", "caminho": "Recommendations", "texto": "Keep the Auto date/time option enabled only when you work with calendar time periods.", "origem": "ancora"}
      ],
      "geracao": {"explicacao": "A tabela automática aumenta o modelo.", "recomendacao": "Desative a opção Auto date/time.", "citacoes": [1]},
      "situacao": "gerado",
      "motivo_descarte": null,
      "cita_ancora": true,
      "fidelidade": {"divergencias": []},
      "modelo": "qwen2.5:7b-instruct-q4_K_M",
      "segundos": 8.1,
      "tokens_prompt": 1200,
      "reducoes_de_contexto": 0
    },
    {
      "achado": {
        "id_regra": "MOD-001",
        "evidencia": {"tipo_objeto": "tabela", "objeto": "LocalDateTable_2", "tabela": "LocalDateTable_2", "trecho": null, "detalhe": {}},
        "mensagem": "A tabela oculta 'LocalDateTable_2' foi gerada pelo Tempo automático de data/hora."
      },
      "contexto": [
        {"numero": 1, "id_pagina": "learn:power-bi/guidance/auto-date-time", "url": "https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time", "titulo": "Auto date/time guidance in Power BI Desktop", "ancora": "recommendations", "caminho": "Recommendations", "texto": "Keep the Auto date/time option enabled only when you work with calendar time periods.", "origem": "ancora"}
      ],
      "geracao": null,
      "situacao": "sem_fundamentacao",
      "motivo_descarte": "json_invalido",
      "cita_ancora": null,
      "fidelidade": null,
      "modelo": "qwen2.5:7b-instruct-q4_K_M",
      "segundos": 7.9,
      "tokens_prompt": 1180,
      "reducoes_de_contexto": 0
    }
  ],
  "segundos_total": 20.3
}
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py tests/test_auditoria.py -q`
Expected: FAIL — `AttributeError: so_regras` e `ResultadoAuditoria` sem `modo`.

- [ ] **Step 4: Implementar em `core/analise/base.py`**

Trocar o `Situacao`:

```python
Situacao = Literal["gerado", "sem_fundamentacao", "so_regras"]
```

No `AchadoEnriquecido`, trocar `modelo: str` por:

```python
    modelo: str | None
    """`None` só em `so_regras`, quando nenhum LLM foi chamado."""
```

Substituir o validador inteiro e acrescentar o classmethod logo depois dele:

```python
    @model_validator(mode="after")
    def _situacao_coerente(self) -> "AchadoEnriquecido":
        if self.situacao == "so_regras":
            # Auditoria sem LLM: só a detecção, sem nada que pareça geração.
            coerentes = (
                not self.contexto
                and self.geracao is None
                and self.motivo_descarte is None
                and self.cita_ancora is None
                and self.fidelidade is None
                and self.modelo is None
                and self.segundos is None
                and self.tokens_prompt is None
            )
        else:
            gerado = self.situacao == "gerado"
            coerentes = (
                (self.geracao is not None) == gerado
                and (self.motivo_descarte is None) == gerado
                and (self.cita_ancora is not None) == gerado
                and (self.fidelidade is not None) == gerado
                and self.modelo is not None
            )
        if not coerentes:
            raise ValueError(
                f"achado enriquecido incoerente: situação {self.situacao} com geração, motivo, "
                "cita_ancora, fidelidade e modelo que não batem"
            )
        return self

    @classmethod
    def so_regras(cls, achado: Achado) -> "AchadoEnriquecido":
        """O achado de uma auditoria sem LLM, escolhida pelo usuário: a recomendação
        que sai é a padrão do catálogo, e o resultado é rotulado assim (spec de 13/10)."""
        return cls(achado=achado, contexto=[], situacao="so_regras", modelo=None)
```

- [ ] **Step 5: Implementar em `core/auditoria.py`**

Imports: trocar `from pydantic import BaseModel` por `from pydantic import BaseModel, model_validator` e acrescentar `from typing import Literal`. Logo antes de `class ResultadoAuditoria`:

```python
ModoAuditoria = Literal["completo", "so_regras"]
```

Substituir a classe:

```python
class ResultadoAuditoria(BaseModel):
    projeto: str
    modo: ModoAuditoria = "completo"
    """O padrão lê como completos os JSONs gravados antes de existir o modo só regras."""
    modelo_llm: str | None
    gerado_em: str
    regras: ResultadoRegras
    """Sem os achados, que estão enriquecidos em `achados`: falhas de regra,
    lacunas de DAX e cobertura continuam visíveis."""
    achados: list[AchadoEnriquecido]
    segundos_total: float

    @model_validator(mode="after")
    def _modo_coerente(self) -> "ResultadoAuditoria":
        so_regras = self.modo == "so_regras"
        coerente = (self.modelo_llm is None) == so_regras and all(
            (a.situacao == "so_regras") == so_regras for a in self.achados
        )
        if not coerente:
            raise ValueError(
                f"resultado incoerente: modo {self.modo} com modelo_llm e situações dos achados que não batem"
            )
        return self
```

- [ ] **Step 6: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py tests/test_auditoria.py tests/test_analise_enriquecimento.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/analise/base.py core/auditoria.py tests/fixtures/resultado-formato-2026-10-11.json tests/test_analise_base.py tests/test_auditoria.py
git commit -m "feat(analise): situacao so_regras no contrato e compatibilidade com o JSON de 11/10"
git push
```

---

### Task 2: `run_audit` com modo só regras e progresso por achado

**Files:**
- Modify: `core/auditoria.py` (`run_audit`)
- Test: `tests/test_auditoria.py`

**Interfaces:**
- Consumes: `AchadoEnriquecido.so_regras` (Task 1).
- Produces: `run_audit(pasta_pbip, *, llm: LLMClient | None, base: BaseRag | None, registro=None, gabaritos=None, ao_progredir: Callable[[int, int, Achado], None] | None = None) -> ResultadoAuditoria`. `llm` e `base` ambos `None` = só regras; só um `None` = `ValueError`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_auditoria.py`:

```python
def test_so_regras_nao_toca_base_nem_llm_nem_gabaritos(tmp_path, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("o modo só regras não pode carregar gabaritos")

    monkeypatch.setattr(auditoria, "carregar_gabaritos", proibido)
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    assert (resultado.modo, resultado.modelo_llm) == ("so_regras", None)
    assert [a.situacao for a in resultado.achados] == ["so_regras", "so_regras"]
    assert all(a.contexto == [] for a in resultado.achados)


def test_modo_ambiguo_e_erro_de_programacao(tmp_path):
    with pytest.raises(ValueError, match="ambíguo"):
        run_audit(_pbip(tmp_path), llm=LLMFalso(), base=None, registro=_registro())
    with pytest.raises(ValueError, match="ambíguo"):
        run_audit(_pbip(tmp_path), llm=None, base=base_padrao(), registro=_registro())


@pytest.mark.parametrize("modo", ["completo", "so_regras"])
def test_progresso_chamado_uma_vez_por_achado(tmp_path, modo):
    chamadas = []
    completo = modo == "completo"
    run_audit(
        _pbip(tmp_path), llm=LLMFalso() if completo else None, base=base_padrao() if completo else None,
        registro=_registro(), gabaritos={"MOD-001": gabarito()},
        ao_progredir=lambda feito, total, a: chamadas.append((feito, total, a.evidencia.objeto)),
    )
    assert chamadas == [(1, 2, "LocalDateTable_1"), (2, 2, "LocalDateTable_2")]


def test_progresso_sem_achados_nao_e_chamado(tmp_path):
    chamadas = []
    run_audit(_pbip(tmp_path, tabelas=()), llm=None, base=None, registro=_registro(),
              ao_progredir=lambda *a: chamadas.append(a))
    assert chamadas == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: FAIL — `run_audit() got an unexpected keyword argument 'ao_progredir'` e `AttributeError: 'NoneType' object has no attribute 'nome'`.

- [ ] **Step 3: Implementar**

Em `core/auditoria.py`, acrescentar `from collections.abc import Callable` e `from core.rules.base import Achado` aos imports, e substituir `run_audit` inteira:

```python
def run_audit(
    pasta_pbip: str | Path,
    *,
    llm: LLMClient | None,
    base: BaseRag | None,
    registro: Registro | None = None,
    gabaritos: dict[str, Gabarito] | None = None,
    ao_progredir: Callable[[int, int, Achado], None] | None = None,
) -> ResultadoAuditoria:
    """`llm` e `base` juntos: auditoria completa. Os dois `None`: só regras, sem
    índice nem LLM, escolhida pelo usuário — nunca como queda por falha (ADR-003).
    `ao_progredir(feito, total, achado)` é chamado depois de cada achado tratado."""
    if (llm is None) != (base is None):
        raise ValueError("modo ambíguo: passe llm e base juntos (completo) ou nenhum dos dois (só regras)")
    so_regras = llm is None
    inicio = time.perf_counter()
    registro = REGISTRO if registro is None else registro
    if not so_regras:
        gabaritos = carregar_gabaritos() if gabaritos is None else gabaritos
        # Partida: nenhuma chamada ao LLM se alguma regra não tiver âncora.
        verificar_ancoras(registro.ids(), gabaritos, base)

    projeto = abrir_pbip(pasta_pbip)
    resultado = avaliar(ler_modelo(projeto.model_bim), registro)
    if resultado.achados and not so_regras:
        try:
            llm.aquecer()
        except ErroDeLLM as erro:
            # Abortar aqui, e não marcar cada achado com `erro_llm`: um relatório
            # com tudo "sem fundamentação" pareceria resultado, e é falha de ambiente.
            raise ErroDeAuditoria(f"o LLM não respondeu no aquecimento: {erro}") from erro

    enriquecidos: list[AchadoEnriquecido] = []
    total = len(resultado.achados)
    for feito, a in enumerate(resultado.achados, start=1):
        if so_regras:
            enriquecidos.append(AchadoEnriquecido.so_regras(a))
        else:
            enriquecidos.append(
                enriquecer(a, registro.meta(a.id_regra), base=base, gabarito=gabaritos[a.id_regra], llm=llm)
            )
        if ao_progredir is not None:
            ao_progredir(feito, total, a)
    return ResultadoAuditoria(
        projeto=nome_do_projeto(pasta_pbip),
        modo="so_regras" if so_regras else "completo",
        modelo_llm=None if so_regras else llm.nome,
        gerado_em=datetime.now().isoformat(timespec="seconds"),
        regras=resultado.model_copy(update={"achados": []}),
        achados=enriquecidos,
        segundos_total=round(time.perf_counter() - inicio, 1),
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: PASS (inclusive os testes antigos do modo completo).

- [ ] **Step 5: Commit**

```bash
git add core/auditoria.py tests/test_auditoria.py
git commit -m "feat(auditoria): modo so regras e progresso por achado no run_audit"
git push
```

---

### Task 3: CLI `--so-regras`, resumo do modo e nome do arquivo com hora

**Files:**
- Modify: `core/auditoria.py` (`resumir`, `gravar`, `main`)
- Test: `tests/test_auditoria.py` (inclui ajustar `test_gravar_usa_projeto_e_data_e_relê_igual`)

**Interfaces:**
- Consumes: `run_audit` (Task 2).
- Produces: `gravar(resultado, pasta=None) -> Path` com nome `<projeto>-<AAAA-MM-DDTHHMM>[-so-regras].json`; `python -m core.auditoria <pasta> --so-regras`.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_auditoria.py`, substituir `test_gravar_usa_projeto_e_data_e_relê_igual` por:

```python
def test_gravar_usa_projeto_data_e_hora_e_relê_igual(tmp_path):
    resultado, _ = _auditar(tmp_path)
    caminho = gravar(resultado, tmp_path / "saida")
    carimbo = resultado.gerado_em[:16].replace(":", "")
    assert caminho.name == f"Minimal-{carimbo}.json"
    assert ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8")) == resultado


def test_gravar_so_regras_leva_sufixo(tmp_path):
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    assert gravar(resultado, tmp_path / "saida").name.endswith("-so-regras.json")


def test_duas_auditorias_no_mesmo_dia_nao_se_sobrescrevem(tmp_path):
    resultado, _ = _auditar(tmp_path)
    outra = resultado.model_copy(update={"gerado_em": resultado.gerado_em[:11] + "23:59:00"})
    if outra.gerado_em[:16] == resultado.gerado_em[:16]:
        outra = resultado.model_copy(update={"gerado_em": resultado.gerado_em[:11] + "00:00:00"})
    assert gravar(resultado, tmp_path / "saida") != gravar(outra, tmp_path / "saida")


def test_resumo_so_regras_diz_o_modo_e_nao_fala_de_geracao(tmp_path):
    resultado = run_audit(_pbip(tmp_path), llm=None, base=None, registro=_registro())
    texto = resumir(resultado)
    assert "so regras" in texto
    assert "Achados: 2" in texto
    assert "gerados" not in texto
    texto.encode("ascii")


def test_comando_so_regras_nao_carrega_a_base(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)

    def proibido():
        raise AssertionError("--so-regras não pode carregar a base")

    monkeypatch.setattr(auditoria.BaseRag, "carregar", staticmethod(proibido))
    assert auditoria.main([str(_pbip(tmp_path)), "--so-regras"]) == 0
    assert len(list((tmp_path / "saida").glob("Minimal-*-so-regras.json"))) == 1
    assert "so regras" in capsys.readouterr().out
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: FAIL — nome do arquivo sem hora, `unrecognized arguments: --so-regras`, resumo sem o modo.

- [ ] **Step 3: Implementar**

Em `resumir`, logo depois de `achados = resultado.achados`:

```python
    if resultado.modo == "so_regras":
        return _ascii("\n".join([
            f"Projeto {resultado.projeto} - modo so regras (sem LLM)",
            f"Achados: {len(achados)}",
            f"Tempo total: {resultado.segundos_total:.1f}s",
        ]))
```

Em `gravar`, trocar a linha do `caminho`:

```python
    # Hora no nome: quem audita, corrige e audita de novo no mesmo dia não perde
    # o resultado anterior.
    carimbo = resultado.gerado_em[:16].replace(":", "")
    sufixo = "-so-regras" if resultado.modo == "so_regras" else ""
    caminho = pasta / f"{resultado.projeto}-{carimbo}{sufixo}.json"
```

Em `main`, depois do `--modelo`:

```python
    parser.add_argument(
        "--so-regras", action="store_true",
        help="só a detecção, sem índice nem LLM; a recomendação é a padrão da regra",
    )
```

e trocar a chamada dentro do `try`:

```python
        if args.so_regras:
            resultado = run_audit(args.pasta_pbip, llm=None, base=None)
        else:
            resultado = run_audit(args.pasta_pbip, llm=ClienteOllama(args.modelo), base=BaseRag.carregar())
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_auditoria.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte inteira (mexeu em `core/`)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: tudo passa (705 + os novos), 1 pulado. Se algum teste fora de `test_auditoria.py` depender do nome antigo do arquivo, ajustar o teste para o formato novo.

- [ ] **Step 6: Commit**

```bash
git add core/auditoria.py tests/test_auditoria.py
git commit -m "feat(auditoria): --so-regras na CLI e hora no nome do resultado gravado"
git push
```

---

### Task 4: Link em português (`url_em_portugues`)

**Files:**
- Modify: `rag/catalogo.py`
- Test: `tests/test_rag_catalogo.py`

**Interfaces:**
- Produces: `url_em_portugues(url: str, caminho: Path = ARQUIVO_FONTES) -> str | None`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar a `tests/test_rag_catalogo.py`:

```python
from rag.catalogo import url_em_portugues


def test_url_em_portugues_ignora_fragmento_barra_e_caixa():
    esperado = "https://learn.microsoft.com/pt-br/power-bi/guidance/auto-date-time"
    assert url_em_portugues("https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time") == esperado
    assert url_em_portugues("https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time#recommendations") == esperado
    assert url_em_portugues("https://learn.microsoft.com/en-us/Power-BI/guidance/auto-date-time/") == esperado


def test_url_fora_do_catalogo_nao_tem_portugues():
    assert url_em_portugues("https://www.sqlbi.com/articles/qualquer") is None


def test_url_em_portugues_le_o_arquivo_indicado(tmp_path):
    arquivo = tmp_path / "sources.yaml"
    arquivo.write_text(
        "- url: https://learn.microsoft.com/en-us/x\n  url_pt_br: https://learn.microsoft.com/pt-br/x\n"
        "- url: https://learn.microsoft.com/en-us/y\n  url_pt_br: null\n",
        encoding="utf-8",
    )
    assert url_em_portugues("https://learn.microsoft.com/en-us/x", arquivo) == "https://learn.microsoft.com/pt-br/x"
    assert url_em_portugues("https://learn.microsoft.com/en-us/y", arquivo) is None
```

(Se o arquivo de teste já importa de `rag.catalogo` num bloco, acrescentar `url_em_portugues` a esse import em vez de um import novo.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: FAIL — `ImportError: cannot import name 'url_em_portugues'`.

- [ ] **Step 3: Implementar**

Em `rag/catalogo.py`, acrescentar `from functools import lru_cache` aos imports e, logo depois de `ler_leituras_sqlbi`:

```python
@lru_cache(maxsize=4)
def _portugues_por_url(caminho: Path) -> dict[str, str]:
    fontes = _ler_yaml(caminho) or []
    return {
        normalizar_url(f["url"]): f["url_pt_br"]
        for f in fontes
        if isinstance(f, dict) and f.get("url") and f.get("url_pt_br")
    }


def url_em_portugues(url: str, caminho: Path = ARQUIVO_FONTES) -> str | None:
    """A versão pt-BR de uma página do Learn, para o leitor da interface e do
    relatório. Sem o fragmento: as âncoras das páginas traduzidas mudam com o
    idioma. O texto indexado continua em inglês (ADR-002)."""
    return _portugues_por_url(caminho).get(normalizar_url(url))
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rag_catalogo.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rag/catalogo.py tests/test_rag_catalogo.py
git commit -m "feat(rag): url_em_portugues resolve a pagina pt-BR pelo catalogo"
git push
```

---

### Task 5: Tradução sob demanda (`core/analise/traducao.py`)

**Files:**
- Create: `core/analise/traducao.py`
- Test: `tests/test_analise_traducao.py`

**Interfaces:**
- Consumes: `LLMClient`, `RespostaLLM` (`core/analise/llm.py`); `LLMFalso` (`tests/fabricas_analise.py`).
- Produces: `traduzir_trecho(texto: str, llm: LLMClient) -> str`; `ErroDeTraducao(Exception)`; `ESQUEMA_TRADUCAO`.

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_analise_traducao.py`:

```python
"""Tradução de um trecho citado: só de exibição, nunca gravada."""

import json

import pytest

from core.analise.llm import ContextoExcedido
from core.analise.traducao import ESQUEMA_TRADUCAO, ErroDeTraducao, traduzir_trecho
from fabricas_analise import LLMFalso


def test_traduz_e_manda_o_texto_e_o_esquema():
    llm = LLMFalso(json.dumps({"traducao": "  Desative a opção Auto date/time.  "}, ensure_ascii=False))
    assert traduzir_trecho("Disable the Auto date/time option.", llm) == "Desative a opção Auto date/time."
    mensagens = llm.chamadas[0]
    assert mensagens[0]["role"] == "system" and "DAX" in mensagens[0]["content"]
    assert mensagens[1] == {"role": "user", "content": "Disable the Auto date/time option."}


def test_esquema_pede_um_campo_so():
    assert ESQUEMA_TRADUCAO["required"] == ["traducao"]


@pytest.mark.parametrize("texto", ["não é json", "[1, 2]", json.dumps({"traducao": "   "}), json.dumps({"outro": "x"})])
def test_resposta_ruim_vira_erro_de_traducao(texto):
    with pytest.raises(ErroDeTraducao):
        traduzir_trecho("x", LLMFalso(texto))


def test_erro_do_llm_passa_adiante():
    with pytest.raises(ContextoExcedido):
        traduzir_trecho("x", LLMFalso(ContextoExcedido("longo demais")))
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_traducao.py -q`
Expected: FAIL — `ModuleNotFoundError: core.analise.traducao`.

- [ ] **Step 3: Implementar**

`core/analise/traducao.py`:

```python
"""Tradução sob demanda de um trecho citado (spec de 13/10/2026, seção 2.5).

Só de exibição: a validação da citação já foi feita sobre o original, e nada
traduzido é gravado no resultado. A interface mostra a tradução ao lado do
original, com o rótulo de tradução automática.
"""

import json

from core.analise.llm import LLMClient

ESQUEMA_TRADUCAO = {
    "type": "object",
    "properties": {"traducao": {"type": "string"}},
    "required": ["traducao"],
}

SISTEMA_TRADUCAO = """Você traduz trechos da documentação oficial do Power BI do inglês para o português do Brasil.
Traduza fielmente, sem resumir, sem explicar e sem acrescentar nada.
Mantenha em inglês os nomes de funções DAX e M, de propriedades e de opções do Power BI, e todo trecho de código.
Responda em JSON com o campo "traducao"."""


class ErroDeTraducao(Exception):
    """O LLM respondeu, mas não com uma tradução utilizável."""


def traduzir_trecho(texto: str, llm: LLMClient) -> str:
    """Erros do próprio LLM (`ErroDeLLM`, inclusive `ContextoExcedido`) passam
    adiante: quem chama decide a mensagem."""
    mensagens = [{"role": "system", "content": SISTEMA_TRADUCAO}, {"role": "user", "content": texto}]
    resposta = llm.gerar(mensagens, ESQUEMA_TRADUCAO)
    try:
        bruto = json.loads(resposta.texto)
    except json.JSONDecodeError as erro:
        raise ErroDeTraducao("o LLM não devolveu JSON válido") from erro
    traducao = bruto.get("traducao") if isinstance(bruto, dict) else None
    if not isinstance(traducao, str) or not traducao.strip():
        raise ErroDeTraducao("o LLM devolveu uma tradução vazia")
    return traducao.strip()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_traducao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/analise/traducao.py tests/test_analise_traducao.py
git commit -m "feat(analise): traducao sob demanda de trecho citado"
git push
```

---

### Task 6: Consultas da interface (`app/consulta.py`)

**Files:**
- Create: `app/__init__.py` (vazio), `app/consulta.py`
- Test: `tests/test_app_consulta.py`

**Interfaces:**
- Consumes: `ResultadoAuditoria`, `AchadoEnriquecido`, `Registro`, `ORDEM_SEVERIDADE`.
- Produces:
  - `Aviso(titulo: str, explicacao: str)` (dataclass frozen); `avisos(item: AchadoEnriquecido) -> list[Aviso]`
  - `Linha(indice: int, severidade: str, regra: str, titulo: str, categoria: str, objeto: str, tabela: str, aviso: bool)`; `linhas(resultado, registro) -> list[Linha]` ordenadas por severidade, regra, objeto; `indice` é a posição em `resultado.achados`
  - `Filtro(severidades, categorias, regras, tabelas: frozenset[str] = frozenset(), so_com_aviso: bool = False)`; `filtrar(linhas, filtro) -> list[Linha]` (conjunto vazio = sem restrição)
  - `opcoes_de_filtro(linhas) -> dict[str, list[str]]` com chaves `severidades`, `categorias`, `regras`, `tabelas`
  - `Resumo(total, por_severidade: dict[str, int], por_categoria: dict[str, int], com_aviso: int)`; `resumir(linhas) -> Resumo`
  - `Examinado(regras: str, expressoes: str, falhas: list[str], lacunas: list[str])`; `examinado(resultado) -> Examinado`
  - `escolher(visiveis: list[Linha], selecionadas: list[int]) -> Linha | None`
  - `SEM_TABELA = "—"`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_app_consulta.py`:

```python
"""Consultas puras da interface: avisos, tabela, filtros, resumo e painel."""

from app import consulta
from app.consulta import Filtro
from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.auditoria import ResultadoAuditoria
from core.rules.base import RegraMeta
from core.rules.expressoes import LacunaDax
from core.rules.registry import Registro
from core.rules.runner import FalhaDeRegra, ResultadoRegras
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto


def _meta(id_regra: str, severidade: str, categoria: str) -> RegraMeta:
    return RegraMeta(
        id=id_regra, titulo=f"Título {id_regra}", categoria=categoria, severidade=severidade,
        url_canonica="https://learn.microsoft.com/x", termos_consulta=("t",),
        recomendacao_padrao=RECOMENDACAO_PADRAO,
    )


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(_meta("MOD-001", "media", "modelagem"), lambda m: [])
    registro.registrar(_meta("DAX-001", "alta", "dax"), lambda m: [])
    registro.registrar(_meta("PERF-001", "baixa", "performance"), lambda m: [])
    return registro


def _gerado(a, **extra) -> AchadoEnriquecido:
    campos = dict(
        achado=a, contexto=contexto(2),
        geracao=Geracao(explicacao="e", recomendacao="Use DIVIDE no lugar do operador.", citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m", segundos=1.0,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _descartado(a, motivo="json_invalido") -> AchadoEnriquecido:
    return AchadoEnriquecido(achado=a, contexto=contexto(1), situacao="sem_fundamentacao",
                             motivo_descarte=motivo, modelo="m")


def _resultado(achados, regras=None) -> ResultadoAuditoria:
    return ResultadoAuditoria(
        projeto="P", modelo_llm="m", gerado_em="2026-10-13T15:30:00",
        regras=regras or ResultadoRegras(regras_executadas=3, expressoes_analisadas=10),
        achados=achados, segundos_total=1.0,
    )


# --- avisos ---

def test_gerado_limpo_nao_tem_aviso():
    assert consulta.avisos(_gerado(achado())) == []


def test_cada_gatilho_gera_seu_aviso():
    titulos = lambda item: [a.titulo for a in consulta.avisos(item)]
    assert titulos(_descartado(achado())) == ["Sem fundamentação — recomendação padrão da regra"]
    assert "não devolveu JSON válido" in consulta.avisos(_descartado(achado()))[0].explicacao
    assert titulos(_gerado(achado(), fidelidade=Fidelidade(divergencias=["42", "Vendas"]))) == ["Divergência de fidelidade"]
    assert "42, Vendas" in consulta.avisos(_gerado(achado(), fidelidade=Fidelidade(divergencias=["42", "Vendas"])))[0].explicacao
    assert titulos(_gerado(achado(), cita_ancora=False)) == ["Não cita a seção âncora da regra"]
    assert titulos(_gerado(achado(), reducoes_de_contexto=2)) == ["Contexto reduzido para caber"]
    assert titulos(AchadoEnriquecido.so_regras(achado())) == ["Só regras — sem explicação do LLM"]


def test_todo_motivo_de_descarte_tem_frase():
    for motivo in ["json_invalido", "campo_vazio", "citacoes_fora_do_limite", "citacao_inexistente",
                   "erro_llm", "contexto_excedido"]:
        assert consulta.avisos(_descartado(achado(), motivo))[0].explicacao


# --- linhas, filtros, resumo ---

def _tres():
    return _resultado([
        _gerado(achado("MOD-001", objeto="B")),
        _gerado(achado("DAX-001", objeto="Medida", tipo_objeto="medida"), cita_ancora=False),
        _gerado(achado("MOD-001", objeto="A")),
    ])


def test_linhas_ordenadas_por_severidade_regra_e_objeto_com_indice_original():
    ls = consulta.linhas(_tres(), _registro())
    assert [(l.regra, l.objeto, l.indice) for l in ls] == [("DAX-001", "Medida", 1), ("MOD-001", "A", 2), ("MOD-001", "B", 0)]
    assert (ls[0].severidade, ls[0].categoria, ls[0].titulo, ls[0].aviso) == ("alta", "dax", "Título DAX-001", True)


def test_linha_sem_tabela_usa_o_travessao():
    a = achado()
    a.evidencia.tabela = None
    assert consulta.linhas(_resultado([_gerado(a)]), _registro())[0].tabela == consulta.SEM_TABELA


def test_filtro_vazio_nao_restringe_e_filtros_se_combinam():
    ls = consulta.linhas(_tres(), _registro())
    assert consulta.filtrar(ls, Filtro()) == ls
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(regras=frozenset({"MOD-001"})))] == ["A", "B"]
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(so_com_aviso=True))] == ["Medida"]
    assert consulta.filtrar(ls, Filtro(severidades=frozenset({"alta"}), categorias=frozenset({"modelagem"}))) == []
    assert [l.objeto for l in consulta.filtrar(ls, Filtro(tabelas=frozenset({"A"})))] == ["A"]


def test_opcoes_de_filtro_em_ordem_de_severidade():
    opcoes = consulta.opcoes_de_filtro(consulta.linhas(_tres(), _registro()))
    assert opcoes["severidades"] == ["alta", "media"]
    assert opcoes["regras"] == ["DAX-001", "MOD-001"]
    assert opcoes["categorias"] == ["dax", "modelagem"]


def test_resumo_conta_severidade_categoria_e_aviso():
    r = consulta.resumir(consulta.linhas(_tres(), _registro()))
    assert (r.total, r.com_aviso) == (3, 1)
    assert r.por_severidade == {"alta": 1, "media": 2, "baixa": 0}
    assert r.por_categoria == {"dax": 1, "modelagem": 2}


# --- painel "o que foi examinado" ---

def test_examinado_sem_problema():
    e = consulta.examinado(_resultado([]))
    assert (e.regras, e.expressoes, e.falhas, e.lacunas) == (
        "3 de 3 regras executadas", "10 de 10 expressões DAX analisadas", [], [])


def test_examinado_com_falha_de_regra_e_lacuna():
    regras = ResultadoRegras(
        regras_executadas=2, regras_com_falha=[FalhaDeRegra(id_regra="MOD-003", erro="KeyError: 'x'")],
        expressoes_analisadas=9,
        lacunas_de_expressao=[LacunaDax(sitio="medida", objeto="[Total]", tabela="Vendas", posicao=12,
                                        trecho="SUM(", motivo="parêntese sem par")],
    )
    e = consulta.examinado(_resultado([], regras))
    assert e.regras == "2 de 3 regras executadas"
    assert e.falhas == ["MOD-003: KeyError: 'x'"]
    assert e.expressoes == "9 de 10 expressões DAX analisadas"
    assert e.lacunas == ["[Total] (medida, posição 12): parêntese sem par"]


def test_examinado_com_varredura_falha_e_sem_dax():
    falhou = consulta.examinado(_resultado([], ResultadoRegras(regras_executadas=3, falha_na_varredura="boom")))
    assert falhou.expressoes == "A varredura de DAX falhou (boom): as regras de texto não rodaram."
    sem_dax = consulta.examinado(_resultado([], ResultadoRegras(regras_executadas=3)))
    assert sem_dax.expressoes == "Nenhuma expressão DAX em escopo."


# --- escolha do achado do detalhe (Review Focus 3) ---

def test_escolher_cai_no_primeiro_quando_a_selecao_nao_cabe():
    ls = consulta.linhas(_tres(), _registro())
    assert consulta.escolher(ls, [2]) == ls[2]
    assert consulta.escolher(ls, []) == ls[0]
    assert consulta.escolher(ls[:2], [5]) == ls[0]
    assert consulta.escolher([], [0]) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_consulta.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 3: Implementar**

`app/__init__.py`: arquivo vazio.

`app/consulta.py`:

```python
"""Consultas sobre um resultado de auditoria para a interface — sem Streamlit.

Tudo aqui é puro e testável: avisos de confiança de um achado, linhas da tabela,
filtros, resumo e o painel "o que foi examinado". Desenho:
`docs/superpowers/specs/2026-10-13-interface-streamlit-design.md`, seção 3.
"""

from collections import Counter
from dataclasses import dataclass

from core.analise.base import AchadoEnriquecido
from core.auditoria import ResultadoAuditoria
from core.rules.base import ORDEM_SEVERIDADE
from core.rules.registry import Registro

SEM_TABELA = "—"

MOTIVOS = {
    "json_invalido": "o LLM não devolveu JSON válido",
    "campo_vazio": "o LLM devolveu explicação ou recomendação vazia",
    "citacoes_fora_do_limite": "o LLM citou trechos demais, nenhum, ou repetidos",
    "citacao_inexistente": "o LLM citou um trecho que não estava no contexto",
    "erro_llm": "o LLM não respondeu",
    "contexto_excedido": "nem o trecho âncora coube no contexto do modelo",
}


@dataclass(frozen=True)
class Aviso:
    titulo: str
    explicacao: str


def avisos(item: AchadoEnriquecido) -> list[Aviso]:
    """Sinais de confiança que o analista precisa ver no achado (seção 3.3)."""
    if item.situacao == "so_regras":
        return [Aviso(
            "Só regras — sem explicação do LLM",
            "A auditoria rodou sem o LLM: a recomendação é a padrão da regra e não há trechos citados.",
        )]
    lista = []
    if item.situacao == "sem_fundamentacao":
        lista.append(Aviso(
            "Sem fundamentação — recomendação padrão da regra",
            f"A resposta do LLM foi descartada ({MOTIVOS[item.motivo_descarte]}); "
            "o texto mostrado é a recomendação padrão do catálogo de regras.",
        ))
    if item.fidelidade is not None and item.fidelidade.divergencias:
        lista.append(Aviso(
            "Divergência de fidelidade",
            "A resposta menciona termos que não aparecem no achado nem nos trechos: "
            f"{', '.join(item.fidelidade.divergencias)}. Confira antes de agir.",
        ))
    if item.cita_ancora is False:
        lista.append(Aviso(
            "Não cita a seção âncora da regra",
            "A explicação se apoia em outros trechos, não na passagem da documentação que sustenta a regra.",
        ))
    if item.reducoes_de_contexto:
        lista.append(Aviso(
            "Contexto reduzido para caber",
            f"{item.reducoes_de_contexto} trecho(s) complementar(es) saíram para o prompt caber no contexto do modelo.",
        ))
    return lista


@dataclass(frozen=True)
class Linha:
    indice: int
    """Posição do achado em `resultado.achados`."""
    severidade: str
    regra: str
    titulo: str
    categoria: str
    objeto: str
    tabela: str
    aviso: bool


def linhas(resultado: ResultadoAuditoria, registro: Registro) -> list[Linha]:
    todas = []
    for indice, item in enumerate(resultado.achados):
        meta = registro.meta(item.achado.id_regra)
        evidencia = item.achado.evidencia
        todas.append(Linha(
            indice=indice, severidade=meta.severidade, regra=meta.id, titulo=meta.titulo,
            categoria=meta.categoria, objeto=evidencia.objeto, tabela=evidencia.tabela or SEM_TABELA,
            aviso=bool(avisos(item)),
        ))
    return sorted(todas, key=lambda l: (ORDEM_SEVERIDADE[l.severidade], l.regra, l.objeto))


@dataclass(frozen=True)
class Filtro:
    """Conjunto vazio = sem restrição naquela dimensão."""

    severidades: frozenset[str] = frozenset()
    categorias: frozenset[str] = frozenset()
    regras: frozenset[str] = frozenset()
    tabelas: frozenset[str] = frozenset()
    so_com_aviso: bool = False


def filtrar(todas: list[Linha], filtro: Filtro) -> list[Linha]:
    def passa(l: Linha) -> bool:
        return (
            (not filtro.severidades or l.severidade in filtro.severidades)
            and (not filtro.categorias or l.categoria in filtro.categorias)
            and (not filtro.regras or l.regra in filtro.regras)
            and (not filtro.tabelas or l.tabela in filtro.tabelas)
            and (not filtro.so_com_aviso or l.aviso)
        )

    return [l for l in todas if passa(l)]


def opcoes_de_filtro(todas: list[Linha]) -> dict[str, list[str]]:
    return {
        "severidades": sorted({l.severidade for l in todas}, key=ORDEM_SEVERIDADE.__getitem__),
        "categorias": sorted({l.categoria for l in todas}),
        "regras": sorted({l.regra for l in todas}),
        "tabelas": sorted({l.tabela for l in todas}),
    }


@dataclass(frozen=True)
class Resumo:
    total: int
    por_severidade: dict[str, int]
    """Sempre as três severidades, em ordem, mesmo com zero."""
    por_categoria: dict[str, int]
    com_aviso: int


def resumir(todas: list[Linha]) -> Resumo:
    severidades = Counter(l.severidade for l in todas)
    return Resumo(
        total=len(todas),
        por_severidade={s: severidades[s] for s in sorted(ORDEM_SEVERIDADE, key=ORDEM_SEVERIDADE.__getitem__)},
        por_categoria=dict(sorted(Counter(l.categoria for l in todas).items())),
        com_aviso=sum(1 for l in todas if l.aviso),
    )


@dataclass(frozen=True)
class Examinado:
    regras: str
    expressoes: str
    falhas: list[str]
    lacunas: list[str]


def examinado(resultado: ResultadoAuditoria) -> Examinado:
    """O que a auditoria leu, para ser visto junto da contagem de achados
    (docstring de `ResultadoRegras`): "15 achados" e "105 de 105 expressões"
    na mesma olhada."""
    r = resultado.regras
    analisadas, total = r.cobertura_de_expressoes
    if r.falha_na_varredura:
        expressoes = f"A varredura de DAX falhou ({r.falha_na_varredura}): as regras de texto não rodaram."
    elif total == 0:
        expressoes = "Nenhuma expressão DAX em escopo."
    else:
        expressoes = f"{analisadas} de {total} expressões DAX analisadas"
    return Examinado(
        regras=f"{r.regras_executadas} de {r.total_de_regras} regras executadas",
        expressoes=expressoes,
        falhas=[f"{f.id_regra}: {f.erro}" for f in r.regras_com_falha],
        lacunas=[f"{l.objeto} ({l.sitio}, posição {l.posicao}): {l.motivo}" for l in r.lacunas_de_expressao],
    )


def escolher(visiveis: list[Linha], selecionadas: list[int]) -> Linha | None:
    """A linha do detalhe. Uma seleção que sobrou de antes do filtro (índice
    fora da lista) cai no primeiro achado visível, nunca em erro."""
    if not visiveis:
        return None
    if selecionadas and 0 <= selecionadas[0] < len(visiveis):
        return visiveis[selecionadas[0]]
    return visiveis[0]
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_consulta.py -q`
Expected: PASS. (Se `LacunaDax` exigir campos além de `sitio, objeto, tabela, posicao, trecho, motivo`, conferir em `core/rules/expressoes.py:37` e ajustar só o teste.)

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py app/consulta.py tests/test_app_consulta.py
git commit -m "feat(app): consultas puras da interface - avisos, tabela, filtros, resumo e painel"
git push
```

---

### Task 7: Execução para a interface (`app/execucao.py`)

**Files:**
- Create: `app/execucao.py`
- Test: `tests/test_app_execucao.py`

**Interfaces:**
- Consumes: `run_audit`, `gravar`, `PASTA_SAIDA`, `REGISTRO`, `carregar_gabaritos` (via `core.auditoria`); `traduzir_trecho`, `ErroDeTraducao` (Task 5); `ClienteOllama`, `ErroDeLLM`; `BaseRag`, `ErroDeIndice`; `ErroDeContexto`; `ErroEstruturaPbip`.
- Produces:
  - `ErroParaUsuario(Exception)` — a mensagem (`str(erro)`) vai direto para a tela
  - `Execucao(resultado: ResultadoAuditoria, gravado_em: Path | None, aviso_gravacao: str | None)`
  - `criar_llm(modelo: str) -> LLMClient`; `carregar_base() -> BaseRag` (pontos de troca nos testes)
  - `executar(entrada: Path, modo: ModoAuditoria, modelo: str, *, ao_progredir=None, obter_base: Callable[[], BaseRag] | None = None) -> Execucao`
  - `salvar_envio(nome: str, conteudo: bytes) -> Path`
  - `Salvo(caminho: Path, rotulo: str)`; `listar_salvos(pasta: Path | None = None) -> list[Salvo]` (mais recente primeiro)
  - `ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria`
  - `traduzir(texto: str, modelo: str) -> str`

- [ ] **Step 1: Escrever os testes que falham**

`tests/test_app_execucao.py`:

```python
"""Execução da auditoria para a interface: cada falha vira ErroParaUsuario."""

import os
from pathlib import Path

import pytest

from app import execucao
from app.execucao import ErroParaUsuario
from conftest import escrever_pbip, modelo_tmsl, tabela
from core import auditoria
from core.analise.llm import ContextoExcedido
from core.rules.registry import Registro
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta

FIXTURE_FORMATO_ANTIGO = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    return registro


@pytest.fixture
def ambiente(tmp_path, monkeypatch):
    """Pipeline com regra, gabarito, base e LLM falsos; saída em tmp."""
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(auditoria, "REGISTRO", _registro())
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {"MOD-001": gabarito()})
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo: LLMFalso())
    return tmp_path


def _pbip(raiz):
    return escrever_pbip(raiz, model_bim=modelo_tmsl([tabela("LocalDateTable_1")]))


def test_executa_completo_grava_e_informa_progresso(ambiente):
    progresso = []
    feito = execucao.executar(
        _pbip(ambiente), "completo", "m", obter_base=base_padrao,
        ao_progredir=lambda f, t, a: progresso.append((f, t)),
    )
    assert feito.resultado.modo == "completo"
    assert feito.gravado_em is not None and feito.gravado_em.parent == ambiente / "saida"
    assert (feito.aviso_gravacao, progresso) == (None, [(1, 1)])


def test_executa_so_regras_sem_base(ambiente):
    def proibido():
        raise AssertionError("só regras não carrega a base")

    feito = execucao.executar(_pbip(ambiente), "so_regras", "m", obter_base=proibido)
    assert feito.resultado.modo == "so_regras"


def test_pbip_invalido_vira_mensagem(ambiente):
    with pytest.raises(ErroParaUsuario, match="não é um projeto PBIP válido"):
        execucao.executar(ambiente / "nao-existe", "so_regras", "m")


def test_model_bim_corrompido_vira_mensagem(ambiente):
    pasta = escrever_pbip(ambiente, model_bim=None)
    (pasta / "Minimal.SemanticModel" / "model.bim").write_text("{ quebrado", encoding="utf-8")
    with pytest.raises(ErroParaUsuario, match="Não consegui ler o projeto"):
        execucao.executar(pasta, "so_regras", "m")


def test_ollama_fora_do_ar_sugere_so_regras(ambiente, monkeypatch):
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo: LLMFalso(falha_no_aquecimento=True))
    with pytest.raises(ErroParaUsuario, match="só regras"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao)


def test_indice_ausente_sugere_construir(ambiente):
    def sem_indice():
        raise FileNotFoundError("rag/store/indice/config.json")

    with pytest.raises(ErroParaUsuario, match="rag.indice construir"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=sem_indice)


def test_ancora_sem_trecho_sugere_construir(ambiente, monkeypatch):
    monkeypatch.setattr(auditoria, "carregar_gabaritos", lambda: {})
    with pytest.raises(ErroParaUsuario, match="rag.indice construir"):
        execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao)


def test_falha_ao_gravar_devolve_o_resultado_com_aviso(ambiente, monkeypatch):
    def bloqueado(resultado, pasta=None):
        raise PermissionError("arquivo aberto em outro programa")

    monkeypatch.setattr(auditoria, "gravar", bloqueado)
    feito = execucao.executar(_pbip(ambiente), "so_regras", "m")
    assert feito.gravado_em is None
    assert "não foi gravado" in feito.aviso_gravacao


# --- envio do .zip (Review Focus 2) ---

@pytest.mark.parametrize("nome", ["P8.zip", "../../fora.zip", "C:\\x\\y\\P8.zip"])
def test_envio_fica_na_pasta_temporaria_so_com_o_nome_final(nome):
    caminho = execucao.salvar_envio(nome, b"PK")
    assert caminho.name == nome.replace("\\", "/").rsplit("/", 1)[-1]
    assert caminho.parent.name.startswith("envio-")
    assert caminho.read_bytes() == b"PK"


# --- resultados salvos (Review Focus 4) ---

def test_lista_salvos_do_mais_recente_e_tolera_pasta_ausente(tmp_path):
    assert execucao.listar_salvos(tmp_path / "nao-existe") == []
    antigo, novo = tmp_path / "A-2026-10-11T1000.json", tmp_path / "B-2026-10-13T1530-so-regras.json"
    antigo.write_text("{}", encoding="utf-8")
    novo.write_text("{}", encoding="utf-8")
    os.utime(antigo, (1_000_000, 1_000_000))
    salvos = execucao.listar_salvos(tmp_path)
    assert [s.rotulo for s in salvos] == ["B-2026-10-13T1530-so-regras", "A-2026-10-11T1000"]


def test_le_o_formato_antigo():
    resultado = execucao.ler_resultado(FIXTURE_FORMATO_ANTIGO.read_bytes())
    assert resultado.modo == "completo"


@pytest.mark.parametrize("conteudo", [b"{ quebrado", b'{"outra": "coisa"}', b"\xff\xfe\x00"])
def test_conteudo_que_nao_e_resultado_vira_mensagem(conteudo):
    with pytest.raises(ErroParaUsuario, match="não é um resultado de auditoria"):
        execucao.ler_resultado(conteudo)


def test_resultado_com_regra_desconhecida_vira_mensagem():
    texto = FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8").replace("MOD-001", "XYZ-999")
    with pytest.raises(ErroParaUsuario, match="XYZ-999"):
        execucao.ler_resultado(texto)


# --- tradução (Review Focus 5) ---

def test_traduz_pelo_modelo_indicado(monkeypatch):
    usados = []
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo: usados.append(modelo) or LLMFalso('{"traducao": "Olá"}'))
    assert execucao.traduzir("Hello", "qwen") == "Olá"
    assert usados == ["qwen"]


@pytest.mark.parametrize("falha", [ContextoExcedido("longo demais"), "não é json"])
def test_traducao_que_falha_vira_mensagem(monkeypatch, falha):
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo: LLMFalso(falha))
    with pytest.raises(ErroParaUsuario, match="Não consegui traduzir"):
        execucao.traduzir("Hello", "m")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py -q`
Expected: FAIL — `ImportError: cannot import name 'execucao' from 'app'`.

- [ ] **Step 3: Implementar**

`app/execucao.py`:

```python
"""Execução da auditoria para a interface — sem Streamlit.

Roda e grava, guarda o `.zip` enviado, lista e lê resultados salvos, traduz um
trecho, e converte cada falha da seção 4 da spec em `ErroParaUsuario`, cuja
mensagem vai direto para a tela. `criar_llm` e `carregar_base` são os pontos
de troca dos testes.
"""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core import auditoria
from core.analise.contexto import ErroDeContexto
from core.analise.llm import ClienteOllama, ErroDeLLM, LLMClient
from core.analise.traducao import ErroDeTraducao, traduzir_trecho
from core.auditoria import ErroDeAuditoria, ModoAuditoria, ResultadoAuditoria
from core.ingest import ErroEstruturaPbip
from core.rules.base import Achado
from core.rules.registry import Registro
from rag.indice import BaseRag, ErroDeIndice

COMANDO_INDICE = "python -m rag.indice construir"


class ErroParaUsuario(Exception):
    """Falha com a mensagem pronta para a tela."""


@dataclass
class Execucao:
    resultado: ResultadoAuditoria
    gravado_em: Path | None
    aviso_gravacao: str | None


def criar_llm(modelo: str) -> LLMClient:
    return ClienteOllama(modelo)


def carregar_base() -> BaseRag:
    return BaseRag.carregar()


def _base_pronta(obter_base: Callable[[], BaseRag]) -> BaseRag:
    try:
        return obter_base()
    except (ErroDeIndice, OSError, ValueError) as erro:
        raise ErroParaUsuario(
            f"A base da RAG não está pronta ({erro}). Construa o índice com `{COMANDO_INDICE}` "
            "ou rode no modo só regras."
        ) from erro


def executar(
    entrada: Path,
    modo: ModoAuditoria,
    modelo: str,
    *,
    ao_progredir: Callable[[int, int, Achado], None] | None = None,
    obter_base: Callable[[], BaseRag] | None = None,
) -> Execucao:
    try:
        if modo == "so_regras":
            resultado = auditoria.run_audit(entrada, llm=None, base=None, ao_progredir=ao_progredir)
        else:
            base = _base_pronta(obter_base or carregar_base)
            resultado = auditoria.run_audit(
                entrada, llm=criar_llm(modelo), base=base, ao_progredir=ao_progredir
            )
    except ErroEstruturaPbip as erro:
        raise ErroParaUsuario(f"Isto não é um projeto PBIP válido: {erro}") from erro
    except ErroDeAuditoria as erro:
        raise ErroParaUsuario(
            f"A auditoria completa não pôde começar: {erro}. Inicie o Ollama (`ollama serve`) "
            "ou rode no modo só regras."
        ) from erro
    except (ErroDeIndice, ErroDeContexto) as erro:
        raise ErroParaUsuario(
            f"A base da RAG não está pronta ({erro}). Construa o índice com `{COMANDO_INDICE}` "
            "ou rode no modo só regras."
        ) from erro
    except (ValueError, OSError) as erro:
        # `model.bim` corrompido (JSONDecodeError é ValueError) ou ilegível.
        raise ErroParaUsuario(f"Não consegui ler o projeto: {type(erro).__name__}: {erro}") from erro
    try:
        return Execucao(resultado, auditoria.gravar(resultado), None)
    except OSError as erro:
        # A geração já custou minutos: mostra o resultado mesmo sem gravar.
        return Execucao(resultado, None, f"O resultado não foi gravado em outputs/: {erro}")


def salvar_envio(nome: str, conteudo: bytes) -> Path:
    """Grava o `.zip` enviado com o nome original, para `nome_do_projeto` dar o
    nome do projeto. Só o nome final: um nome com caminho não sai da pasta."""
    pasta = Path(tempfile.mkdtemp(prefix="envio-"))
    caminho = pasta / Path(nome.replace("\\", "/")).name
    caminho.write_bytes(conteudo)
    return caminho


@dataclass(frozen=True)
class Salvo:
    caminho: Path
    rotulo: str


def listar_salvos(pasta: Path | None = None) -> list[Salvo]:
    """Pelo nome e pela data de modificação, sem abrir cada JSON: o Streamlit
    reexecuta o script a cada clique. Um JSON inválido vira mensagem ao abrir."""
    pasta = auditoria.PASTA_SAIDA if pasta is None else pasta
    if not pasta.is_dir():
        return []
    arquivos = sorted(pasta.glob("*.json"), key=lambda c: c.stat().st_mtime, reverse=True)
    return [Salvo(c, c.stem) for c in arquivos]


def ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria:
    try:
        resultado = ResultadoAuditoria.model_validate_json(conteudo)
    except ValidationError as erro:
        raise ErroParaUsuario(
            "O arquivo não é um resultado de auditoria desta ferramenta "
            f"({erro.error_count()} problema(s) no formato)."
        ) from erro
    registro = auditoria.REGISTRO if registro is None else registro
    desconhecidas = sorted({a.achado.id_regra for a in resultado.achados} - set(registro.ids()))
    if desconhecidas:
        raise ErroParaUsuario(
            f"O resultado tem regras que esta versão da ferramenta não conhece: {', '.join(desconhecidas)}."
        )
    return resultado


def traduzir(texto: str, modelo: str) -> str:
    try:
        return traduzir_trecho(texto, criar_llm(modelo))
    except (ErroDeLLM, ErroDeTraducao) as erro:
        raise ErroParaUsuario(f"Não consegui traduzir o trecho: {erro}") from erro
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py -q`
Expected: PASS. Se `b"\xff\xfe\x00"` não levantar `ValidationError` no Pydantic instalado (e sim `UnicodeDecodeError`), acrescentar `UnicodeDecodeError` ao `except` de `ler_resultado` — não mudar o teste.

- [ ] **Step 5: Commit**

```bash
git add app/execucao.py tests/test_app_execucao.py
git commit -m "feat(app): execucao da auditoria para a interface, com erros em mensagens"
git push
```

---

### Task 8: A interface Streamlit (`app/streamlit_app.py`)

**Files:**
- Modify: `requirements.txt`
- Create: `app/streamlit_app.py`
- Test: `tests/test_app_interface.py`

**Interfaces:**
- Consumes: tudo de `app.consulta` (Task 6) e `app.execucao` (Task 7); `url_em_portugues` (Task 4); `MODELO_PADRAO`; `REGISTRO` (`core.rules.todas`).
- Produces: `streamlit run app/streamlit_app.py`. Chaves do `session_state` usadas pelos testes: `resultado`, `executando`, `mensagem` (tupla `(tipo, texto)`, `tipo` em `error|warning|success`). Chaves de widget: `envio`, `pasta`, `modo`, `modelo`, `auditar`, `salvo`, `abrir`, `json_externo`, `abrir_externo`.

- [ ] **Step 1: Instalar a dependência**

Acrescentar ao fim de `requirements.txt`:

```
# Fase 4 - interface
streamlit==1.64.0
```

Run: `.\.venv\Scripts\python.exe -m pip install streamlit==1.64.0`
Expected: instalado sem rebaixar `numpy`, `pydantic` nem `torch` (conferir com `.\.venv\Scripts\python.exe -m pip check`; se houver conflito, parar e reportar antes de seguir).

- [ ] **Step 2: Escrever os testes que falham**

`tests/test_app_interface.py`:

```python
"""Fumaça da interface com o AppTest do Streamlit: LLM falso, PBIP sintético."""

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app import execucao
from conftest import coluna, escrever_pbip, modelo_tmsl, relacionamento, tabela
from core import auditoria
from core.ingest import abrir_pbip
from core.parser_bim import ler_modelo
from core.rules.registry import Registro
from core.rules.runner import avaliar
from core.rules.todas import REGISTRO
from fabricas_analise import LLMFalso, achado, base_padrao, gabarito, meta

ARQUIVO_APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(auditoria, "PASTA_SAIDA", tmp_path / "saida")
    monkeypatch.setattr(execucao, "carregar_base", base_padrao)
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo: LLMFalso())
    st.cache_resource.clear()
    return AppTest.from_file(ARQUIVO_APP, default_timeout=60)


def _pbip_bidirecional(raiz):
    """MOD-002 marca o relacionamento bidirecional com as regras reais."""
    return escrever_pbip(raiz, model_bim=modelo_tmsl(
        tabelas=[
            tabela("DimProduct", colunas=[coluna("SubKey", tipo_dado="int64")]),
            tabela("DimProductSubcategory", colunas=[coluna("SubKey", tipo_dado="int64")]),
        ],
        relacionamentos=[relacionamento("DimProduct", "SubKey", "DimProductSubcategory", "SubKey", bidirecional=True)],
    ))


def _gravar_resultado_salvo(raiz) -> Path:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=t.nome) for t in modelo.tabelas])
    pbip = escrever_pbip(raiz / "origem", model_bim=modelo_tmsl([tabela("LocalDateTable_1")]))
    resultado = auditoria.run_audit(
        pbip, llm=LLMFalso(), base=base_padrao(), registro=registro, gabaritos={"MOD-001": gabarito()},
    )
    return auditoria.gravar(resultado)


def test_abre_sem_resultado_e_sem_erro(app):
    app.run()
    assert not app.exception
    assert app.session_state["resultado"] is None


def test_abrir_resultado_salvo_mostra_painel_e_tabela(app, tmp_path):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho))
    app.button(key="abrir").click().run()
    assert not app.exception
    assert app.session_state["resultado"].projeto == "Minimal"
    textos = " ".join(m.value for m in app.markdown)
    assert "1 de 1 regras executadas" in textos
    assert len(app.dataframe) == 1


def test_so_regras_roda_ponta_a_ponta(app, tmp_path):
    pbip = _pbip_bidirecional(tmp_path)
    esperados = len(avaliar(ler_modelo(abrir_pbip(pbip).model_bim), REGISTRO).achados)
    assert esperados >= 1
    app.run()
    app.text_input(key="pasta").input(str(pbip)).run()
    app.radio(key="modo").set_value("so_regras").run()
    app.button(key="auditar").click().run()
    assert not app.exception
    resultado = app.session_state["resultado"]
    assert (resultado.modo, len(resultado.achados)) == ("so_regras", esperados)
    assert app.session_state["executando"] is False
    assert list((tmp_path / "saida").glob("*-so-regras.json"))


def test_erro_de_pbip_vira_mensagem(app, tmp_path):
    app.run()
    app.text_input(key="pasta").input(str(tmp_path / "nao-existe")).run()
    app.radio(key="modo").set_value("so_regras").run()
    app.button(key="auditar").click().run()
    assert not app.exception
    assert any("não é um projeto PBIP válido" in e.value for e in app.error)
    assert app.session_state["executando"] is False


def test_erro_inesperado_vira_mensagem_e_destrava(app, tmp_path, monkeypatch):
    """Review Focus 1: um bug no pipeline não pode travar os controles."""
    def quebra(*args, **kwargs):
        raise KeyError("bug")

    monkeypatch.setattr(execucao, "executar", quebra)
    app.run()
    app.text_input(key="pasta").input(str(tmp_path)).run()
    app.button(key="auditar").click().run()
    assert not app.exception
    assert any("Erro inesperado" in e.value for e in app.error)
    assert app.session_state["executando"] is False


def test_json_invalido_mantem_o_resultado_anterior(app, tmp_path):
    """Review Focus 4."""
    caminho = _gravar_resultado_salvo(tmp_path)
    (caminho.parent / "quebrado.json").write_text("{ quebrado", encoding="utf-8")
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho))
    app.button(key="abrir").click().run()
    app.selectbox(key="salvo").set_value(str(caminho.parent / "quebrado.json"))
    app.button(key="abrir").click().run()
    assert not app.exception
    assert any("não é um resultado de auditoria" in e.value for e in app.error)
    assert app.session_state["resultado"].projeto == "Minimal"
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_interface.py -q`
Expected: FAIL — o arquivo `app/streamlit_app.py` não existe.

- [ ] **Step 4: Implementar**

`app/streamlit_app.py`:

```python
"""Interface da auditoria — `streamlit run app/streamlit_app.py`.

Só renderização e estado da sessão; a lógica está em `app/consulta.py` e
`app/execucao.py`. Desenho: `docs/superpowers/specs/2026-10-13-interface-streamlit-design.md`.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    # `streamlit run` põe só a pasta do script no caminho, não a raiz do repositório.
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

from app import consulta, execucao  # noqa: E402
from app.consulta import Filtro  # noqa: E402
from core.analise.base import AchadoEnriquecido  # noqa: E402
from core.analise.llm import MODELO_PADRAO  # noqa: E402
from core.auditoria import ResultadoAuditoria  # noqa: E402
from core.rules.todas import REGISTRO  # noqa: E402
from rag.catalogo import url_em_portugues  # noqa: E402

ROTULOS_SEVERIDADE = {"alta": "🔴 alta", "media": "🟠 média", "baixa": "🟡 baixa"}
ROTULOS_MODO = {"completo": "completo (com explicação do LLM)", "so_regras": "só regras"}
ESPECIAIS_MARKDOWN = "\\`*_{}[]<>()#+-.!|$"

st.set_page_config(page_title="Auditor de PBIP", layout="wide")
estado = st.session_state
estado.setdefault("resultado", None)
estado.setdefault("executando", False)
estado.setdefault("pedido", None)
estado.setdefault("mensagem", None)
estado.setdefault("traducoes", {})


def _md(texto: str) -> str:
    """Nomes de objeto como `DateTableTemplate_0eab_...` não podem virar itálico."""
    return "".join(f"\\{c}" if c in ESPECIAIS_MARKDOWN else c for c in texto)


@st.cache_resource(show_spinner="Carregando a base da RAG...")
def _base():
    return execucao.carregar_base()


def _abrir(conteudo: bytes) -> None:
    try:
        estado.resultado = execucao.ler_resultado(conteudo)
    except execucao.ErroParaUsuario as erro:
        estado.mensagem = ("error", str(erro))  # o resultado anterior continua
    else:
        estado.traducoes = {}
        estado.mensagem = None


# --- barra lateral -----------------------------------------------------------

def _barra_lateral() -> None:
    bloqueado = estado.executando
    lateral = st.sidebar
    lateral.header("Nova auditoria")
    enviado = lateral.file_uploader("Projeto PBIP em .zip", type=["zip"], disabled=bloqueado, key="envio")
    pasta = lateral.text_input("ou caminho da pasta do projeto", disabled=bloqueado, key="pasta")
    modo = lateral.radio("Modo", list(ROTULOS_MODO), format_func=ROTULOS_MODO.get, disabled=bloqueado, key="modo")
    modelo = lateral.text_input(
        "Modelo do Ollama", value=MODELO_PADRAO, disabled=bloqueado or modo == "so_regras", key="modelo"
    )
    if lateral.button("Auditar", type="primary", disabled=bloqueado or not (enviado or pasta.strip()), key="auditar"):
        entrada = (
            execucao.salvar_envio(enviado.name, enviado.getvalue()) if enviado is not None else Path(pasta.strip())
        )
        estado.pedido = {"entrada": entrada, "modo": modo, "modelo": modelo}
        estado.executando = True
        estado.mensagem = None
        st.rerun()

    lateral.header("Abrir resultado salvo")
    salvos = {str(s.caminho): s.rotulo for s in execucao.listar_salvos()}
    escolhido = lateral.selectbox(
        "Resultados em outputs/", list(salvos), index=None, format_func=salvos.get,
        placeholder="escolha um resultado", disabled=bloqueado, key="salvo",
    )
    if lateral.button("Abrir", disabled=bloqueado or escolhido is None, key="abrir"):
        _abrir(Path(escolhido).read_bytes())
    externo = lateral.file_uploader("ou envie um JSON", type=["json"], disabled=bloqueado, key="json_externo")
    if lateral.button("Abrir JSON enviado", disabled=bloqueado or externo is None, key="abrir_externo"):
        _abrir(externo.getvalue())


# --- execução ----------------------------------------------------------------

def _executar(pedido: dict) -> None:
    try:
        with st.status("Auditando...", expanded=True) as status:
            st.write("Lendo o projeto e rodando as regras.")
            barra = st.progress(0.0)

            def ao_progredir(feito, total, achado):
                etapa = "explicações" if pedido["modo"] == "completo" else "achados"
                barra.progress(
                    feito / total,
                    text=f"{etapa}: achado {feito} de {total} — {achado.id_regra} {achado.evidencia.objeto}",
                )

            try:
                feito = execucao.executar(
                    pedido["entrada"], pedido["modo"], pedido["modelo"], ao_progredir=ao_progredir, obter_base=_base
                )
            except execucao.ErroParaUsuario as erro:
                estado.mensagem = ("error", str(erro))
                status.update(label="A auditoria não terminou", state="error")
            else:
                estado.resultado = feito.resultado
                estado.traducoes = {}
                estado.mensagem = (
                    ("warning", feito.aviso_gravacao) if feito.aviso_gravacao
                    else ("success", f"Resultado gravado em {feito.gravado_em}")
                )
                status.update(label="Auditoria concluída", state="complete")
    except Exception as erro:  # noqa: BLE001 — nenhum traceback na tela, e os controles destravam
        estado.mensagem = ("error", f"Erro inesperado: {type(erro).__name__}: {erro}")
    finally:
        estado.executando = False
        estado.pedido = None
    st.rerun()


# --- resultado ---------------------------------------------------------------

def _cabecalho(resultado: ResultadoAuditoria) -> None:
    st.title(resultado.projeto)
    if resultado.modo == "so_regras":
        modo = "só regras (sem LLM)"
    else:
        modo = f"completo — modelo {resultado.modelo_llm}"
    st.caption(f"Auditado em {resultado.gerado_em.replace('T', ' ')} · {modo} · {resultado.segundos_total:.1f} s")
    if resultado.modo == "so_regras":
        st.info("Resultado só regras: os achados vêm da detecção determinística, com a recomendação padrão de "
                "cada regra e sem explicação do LLM.")


def _examinado(resultado: ResultadoAuditoria) -> None:
    examinado = consulta.examinado(resultado)
    with st.container(border=True):
        st.subheader("O que foi examinado")
        st.markdown(f"- {examinado.regras}\n- {examinado.expressoes}")
        for falha in examinado.falhas:
            st.error(f"Regra com falha — {falha}")
        if examinado.lacunas:
            st.warning(f"{len(examinado.lacunas)} expressão(ões) DAX não analisada(s) pelo leitor de DAX.")
            with st.expander("Ver as expressões não analisadas"):
                st.markdown("\n".join(f"- {_md(l)}" for l in examinado.lacunas))


def _resumo(linhas: list[consulta.Linha]) -> None:
    resumo = consulta.resumir(linhas)
    colunas = st.columns(5)
    colunas[0].metric("Achados", resumo.total)
    for coluna, (severidade, n) in zip(colunas[1:4], resumo.por_severidade.items()):
        coluna.metric(ROTULOS_SEVERIDADE[severidade], n)
    colunas[4].metric("Com aviso", resumo.com_aviso)
    if resumo.por_categoria:
        st.caption(" · ".join(f"{categoria}: {n}" for categoria, n in resumo.por_categoria.items()))


def _filtros(linhas: list[consulta.Linha]) -> Filtro:
    opcoes = consulta.opcoes_de_filtro(linhas)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    return Filtro(
        severidades=frozenset(c1.multiselect("Severidade", opcoes["severidades"], key="f_severidade")),
        categorias=frozenset(c2.multiselect("Categoria", opcoes["categorias"], key="f_categoria")),
        regras=frozenset(c3.multiselect("Regra", opcoes["regras"], key="f_regra")),
        tabelas=frozenset(c4.multiselect("Tabela", opcoes["tabelas"], key="f_tabela")),
        so_com_aviso=c5.checkbox("Só com aviso", key="f_aviso"),
    )


def _tabela(visiveis: list[consulta.Linha]) -> consulta.Linha | None:
    if not visiveis:
        st.info("Nenhum achado com estes filtros.")
        return None
    dados = [
        {"Severidade": ROTULOS_SEVERIDADE[l.severidade], "Regra": l.regra, "Título": l.titulo,
         "Objeto": l.objeto, "Tabela": l.tabela, "Aviso": "⚠" if l.aviso else ""}
        for l in visiveis
    ]
    evento = st.dataframe(
        dados, on_select="rerun", selection_mode="single-row", hide_index=True, width="stretch", key="tabela"
    )
    try:
        selecionadas = list(evento.selection.rows)
    except AttributeError:
        selecionadas = []
    return consulta.escolher(visiveis, selecionadas)


def _link(rotulo: str, url: str) -> str:
    portugues = url_em_portugues(url)
    texto = f"[{rotulo}]({url})"
    return f"{texto} · [ler em português]({portugues})" if portugues else texto


def _citacoes(item: AchadoEnriquecido, indice: int, resultado: ResultadoAuditoria) -> None:
    if item.geracao is None:
        return
    st.markdown("**Fontes citadas**")
    por_numero = {t.numero: t for t in item.contexto}
    modelo = estado.get("modelo") or MODELO_PADRAO
    for numero in item.geracao.citacoes:
        trecho = por_numero[numero]
        chave = f"{resultado.gerado_em}|{indice}|{numero}"
        with st.container(border=True):
            st.markdown(f"[{numero}] " + _link(f"{trecho.titulo} — {trecho.caminho}", f"{trecho.url}#{trecho.ancora}"))
            original, traducao = st.columns(2)
            original.caption("Original")
            original.markdown(_md(trecho.texto))
            if chave in estado.traducoes:
                traducao.caption("Tradução automática — o texto citado é o original")
                traducao.markdown(_md(estado.traducoes[chave]))
            elif traducao.button("Traduzir trecho", key=f"traduzir|{chave}"):
                with st.spinner("Traduzindo..."):
                    try:
                        estado.traducoes[chave] = execucao.traduzir(trecho.texto, modelo)
                    except execucao.ErroParaUsuario as erro:
                        traducao.error(str(erro))
                    else:
                        st.rerun()


def _detalhes_tecnicos(item: AchadoEnriquecido) -> None:
    with st.expander("Detalhes técnicos"):
        st.markdown(
            f"- Modelo: {item.modelo or '—'}\n"
            f"- Tempo da chamada: {item.segundos if item.segundos is not None else '—'} s\n"
            f"- Tokens do prompt: {item.tokens_prompt if item.tokens_prompt is not None else '—'}\n"
            f"- Trechos retirados para caber: {item.reducoes_de_contexto}"
        )
        for trecho in item.contexto:
            origem = "âncora da regra" if trecho.origem == "ancora" else "busca"
            st.markdown(f"**[{trecho.numero}] {_md(trecho.titulo)} — {_md(trecho.caminho)}** ({origem})")
            st.markdown(_md(trecho.texto))


def _detalhe(resultado: ResultadoAuditoria, linha: consulta.Linha) -> None:
    item = resultado.achados[linha.indice]
    meta = REGISTRO.meta(item.achado.id_regra)
    evidencia = item.achado.evidencia
    st.divider()
    st.subheader(f"{meta.id} — {meta.titulo}")
    st.caption(f"{ROTULOS_SEVERIDADE[meta.severidade]} · {meta.categoria} · {evidencia.tipo_objeto} {evidencia.objeto}")
    st.markdown(_md(item.achado.mensagem))
    for aviso in consulta.avisos(item):
        st.warning(f"**{aviso.titulo}** — {_md(aviso.explicacao)}")
    if evidencia.trecho:
        st.code(evidencia.trecho, language=None)
    if evidencia.detalhe:
        with st.expander("Valores lidos pela regra"):
            st.json(evidencia.detalhe)
    if item.geracao is not None:
        st.markdown("**Explicação**")
        st.markdown(_md(item.geracao.explicacao))
    st.markdown("**Recomendação**")
    st.markdown(_md(item.recomendacao_final(meta)))
    _citacoes(item, linha.indice, resultado)
    st.markdown("Fonte da regra: " + _link(meta.titulo, meta.url_canonica))
    _detalhes_tecnicos(item)


def _resultado(resultado: ResultadoAuditoria) -> None:
    _cabecalho(resultado)
    _examinado(resultado)
    linhas = consulta.linhas(resultado, REGISTRO)
    _resumo(linhas)
    visiveis = consulta.filtrar(linhas, _filtros(linhas))
    linha = _tabela(visiveis)
    if linha is not None:
        _detalhe(resultado, linha)


# --- página ------------------------------------------------------------------

_barra_lateral()
if estado.mensagem:
    tipo, texto = estado.mensagem
    getattr(st, tipo)(texto)
if estado.executando and estado.pedido is not None:
    _executar(estado.pedido)
elif estado.resultado is not None:
    _resultado(estado.resultado)
else:
    st.title("Auditor de projetos Power BI (PBIP)")
    st.markdown("Envie um projeto na barra lateral, ou abra um resultado salvo.")
```

Notas para quem implementa:
- `st.rerun()` dentro de `_executar` fica **fora** do `try/finally`: ele levanta uma exceção de controle do Streamlit que não pode ser engolida pelo `except Exception`.
- O `except Exception` também envolve o `st.status`: é o que garante o Review Focus 1.
- Se o `AppTest` desta versão não aceitar `set_value` com uma opção que é `str` de caminho, conferir a API em `streamlit.testing.v1.element_tree.Selectbox` e ajustar só o teste.
- Se `st.dataframe(..., width="stretch")` não existir na 1.64.0, usar `use_container_width=True`.

- [ ] **Step 5: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_interface.py -q`
Expected: PASS (6 testes).

- [ ] **Step 6: Suíte inteira**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: tudo passa, 1 pulado.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt app/streamlit_app.py tests/test_app_interface.py
git commit -m "feat(app): interface Streamlit - auditoria, resultado salvo, filtros e detalhe"
git push
```

---

### Task 9: Aceite manual e registro

**Files:**
- Modify: `docs/project/progress-log.md`, `docs/project/status.md`, `docs/project/backlog.md`, `README.md` (seção de uso, se existir)

- [ ] **Step 1: Só regras em P1–P7 pela CLI**

```powershell
foreach ($p in Get-ChildItem data/pbip -Directory | Where-Object Name -match '^P[1-7]_') { .\.venv\Scripts\python.exe -m core.auditoria $p.FullName --so-regras }
```

Expected: soma dos "Achados:" = **61** (P1 11, P2 3, P3 9, P4 13, P5 18, P6 7, P7 0 — VP + FP + indeterminados marcados por projeto em `eval/results/regras-2026-10-12-pos-correcao.json`). Divergência = parar e investigar antes de seguir.

- [ ] **Step 2: Interface no P8, modo completo**

Com o Ollama no ar: `.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py`. No navegador: caminho `data/pbip/P8_contoso-vendas`, modo completo, auditar. Conferir: barra de progresso avançando por achado; painel "9 de 9 regras executadas" e "105 de 105 expressões DAX analisadas"; 15 achados; filtros; detalhe com avisos, citações, "ler em português" e "Traduzir trecho" em pelo menos uma citação; abrir de novo o JSON gravado pela barra lateral; abrir o JSON antigo `outputs/P8_contoso-vendas-2026-10-11.json`. Anotar tempo total e número de achados.

- [ ] **Step 3: Interface no P8, só regras, e com o Ollama parado**

Só regras: 15 achados em segundos, selo "só regras". Depois, com o Ollama parado, modo completo: a mensagem sugere só regras e nada é gravado.

- [ ] **Step 4: Registrar**

- `progress-log.md`: entrada de 13/10 (ou da data real) com os números dos Steps 1–3, o que precisou de ajuste e "**Próximo passo:** PR da `fase4-interface`; depois o subprojeto da semana 10 (relatório HTML/PDF e cache da demo)".
- `status.md`: linha da F4 "Em andamento" com a interface concluída; entregável novo na tabela da seção 3 ("Interface Streamlit — `streamlit run app/streamlit_app.py`"), contagem de testes atualizada.
- `backlog.md`, em Trabalhos Futuros: "Cancelamento da auditoria em andamento (thread em segundo plano)", "Texto oficial em pt-BR dos trechos citados (coleta pt-BR e alinhamento de seções)", "Comparar duas auditorias do mesmo projeto".
- `README.md`: como abrir a interface, se o README tiver seção de uso.

- [ ] **Step 5: Commit**

```bash
git add docs/project/progress-log.md docs/project/status.md docs/project/backlog.md README.md
git commit -m "docs: interface Streamlit aceita no P8 e em P1-P7"
git push
```
