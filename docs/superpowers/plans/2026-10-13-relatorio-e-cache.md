# Relatório HTML/PDF e cache das respostas do LLM — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar o relatório da auditoria em HTML autocontido e em PDF (Playwright + Edge do sistema), guardar as respostas do LLM num cache opcional e rotulado, e fechar os menores adiados da interface.

**Architecture:** As consultas puras saem de `app/consulta.py` para `core/apresentacao.py` (interface e relatório usam as mesmas). `reports/html.py` monta o HTML com Jinja2 a partir do `ResultadoAuditoria`; `reports/pdf.py` imprime esse HTML pelo Edge numa thread própria; `reports/comando.py` é a CLI. O cache é um envoltório do `LLMClient` (`core/analise/cache.py`) com um arquivo por chave sha256; `do_cache` atravessa `RespostaLLM` → `AchadoEnriquecido`.

**Tech Stack:** Python 3.11, Pydantic 2, Jinja2 3.1.6, Playwright 1.62.0 (canal `msedge`), Streamlit 1.64.0, pytest.

**Spec:** `docs/superpowers/specs/2026-10-13-relatorio-e-cache-design.md`

## Global Constraints

- Todo o projeto em português: código, nomes de função e de teste, docstrings, mensagens, commits.
- Toda falha vira mensagem (tela ou stderr), nunca traceback.
- `aquecer()` sempre vai ao LLM real; com o Ollama fora do ar a auditoria completa aborta, com ou sem cache (ADR-003).
- O cache é **desligado por padrão** na CLI e na interface; achado vindo do cache leva `do_cache=True` e isso aparece no resumo, na interface e no relatório.
- JSONs gravados antes desta etapa (sem `do_cache`) continuam abrindo.
- O relatório cita o texto **original** do trecho; tradução automática não entra nele.
- HTML autocontido: nenhum `src=`/`href=` externo além de `https://learn.microsoft.com`; todo texto passa pelo autoescape do Jinja2.
- Dependências novas: `jinja2==3.1.6`, `playwright==1.62.0` (seção "Fase 4 - relatório" do `requirements.txt`). **Não** rodar `playwright install`: o navegador é o Edge do sistema (`channel="msedge"`).
- Python sempre pelo venv: `.\.venv\Scripts\python.exe -m pytest ...`. Suíte completa ~7 min: rode só os arquivos tocados durante a tarefa e a suíte inteira no fim das tarefas que mexem em `core/`.
- Commits terminam com `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; push na `fase4-relatorio` a cada tarefa.

## Review Focus

1. **Playwright síncrono chamado de dentro de um loop asyncio** (o Streamlit roda o script numa thread com contexto próprio; uma chamada a partir de código async quebraria com "Sync API inside the asyncio loop"): o PDF precisa sair mesmo assim — por isso `gerar_pdf` roda numa thread própria. Teste real na Task 6 chamando de dentro de `asyncio.run`.
2. **Arquivo de cache de outro formato** (JSON válido sem `texto`, ou `texto` não-string): tratado como ausente, não como resposta vazia. Teste na Task 3.
3. **Índice da RAG reconstruído entre duas auditorias** (o contexto recuperado muda): a chave muda e o LLM é chamado — nunca uma resposta velha para um contexto novo. Teste na Task 3 (mensagens diferentes → chaves diferentes).
4. **Nome de objeto, texto do LLM ou título de página com HTML** (`<script>`, `<img onerror>`): aparece como texto no relatório. Teste na Task 5.
5. **Resultado de outra versão aberto na CLI do relatório** (JSON quebrado, regra desconhecida, BOM): mensagem e código 1, mesma leitura da interface. Testes nas Tasks 4 e 7.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `core/apresentacao.py` (mover de `app/consulta.py`) | Avisos, linhas, filtros, resumo, painel, escolha; `ler_resultado`, `ErroDeLeitura` |
| `core/analise/base.py`, `core/analise/llm.py` (modificar) | `do_cache` em `AchadoEnriquecido` e `RespostaLLM` |
| `core/analise/enriquecimento.py` (modificar) | Propaga `do_cache` |
| `core/analise/cache.py` (criar) | `ClienteComCache`, `chave_de`, `PASTA_CACHE` |
| `core/auditoria.py` (modificar) | `nome_base` com segundos; `resumir` com cache; `--cache` |
| `reports/__init__.py`, `reports/html.py`, `reports/templates/relatorio.html.j2` (criar) | HTML |
| `reports/pdf.py` (criar) | PDF via Edge |
| `reports/comando.py`, `reports/__main__.py` (criar) | CLI `python -m reports` |
| `app/execucao.py`, `app/streamlit_app.py` (modificar) | Cache, downloads, menores |
| `docs/adr/ADR-002-stack-tecnologica.md` (emenda) | Canal `msedge` |

---

### Task 1: `app/consulta.py` → `core/apresentacao.py`

**Files:**
- Move: `app/consulta.py` → `core/apresentacao.py`; `tests/test_app_consulta.py` → `tests/test_apresentacao.py`
- Modify: `app/streamlit_app.py` (import)

**Interfaces:**
- Produces: `core.apresentacao` com exatamente a API que `app.consulta` tinha (`Aviso`, `avisos`, `Linha`, `linhas`, `Filtro`, `filtrar`, `opcoes_de_filtro`, `Resumo`, `resumir`, `Examinado`, `examinado`, `escolher`, `SEM_TABELA`, `MOTIVOS`).

- [ ] **Step 1: Mover com histórico**

```bash
git mv app/consulta.py core/apresentacao.py
git mv tests/test_app_consulta.py tests/test_apresentacao.py
```

- [ ] **Step 2: Ajustar imports (os testes passam a falhar antes do ajuste do app)**

Em `tests/test_apresentacao.py`: `from app import consulta` → `from core import apresentacao as consulta`; `from app.consulta import Filtro` → `from core.apresentacao import Filtro`; primeira linha do docstring: `"""Consultas puras de apresentação (interface e relatório): avisos, tabela, filtros, resumo e painel."""`.

Em `core/apresentacao.py`, primeira linha do docstring: `"""Consultas sobre um resultado de auditoria, para a interface e o relatório — sem Streamlit.`

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_interface.py -q`
Expected: FAIL — `ImportError: cannot import name 'consulta' from 'app'`.

- [ ] **Step 3: Ajustar o app**

Em `app/streamlit_app.py`: `from app import consulta, execucao  # noqa: E402` → `from app import execucao  # noqa: E402` e `from core import apresentacao as consulta  # noqa: E402`; `from app.consulta import Filtro  # noqa: E402` → `from core.apresentacao import Filtro  # noqa: E402`. Manter a ordem alfabética dos imports `core.*`.

- [ ] **Step 4: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_apresentacao.py tests/test_app_interface.py tests/test_app_execucao.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A app core/apresentacao.py tests/test_apresentacao.py
git commit -m "refactor: consultas de apresentacao saem de app/ para core/apresentacao.py"
git push
```

---

### Task 2: `do_cache` no contrato, nome com segundos e resumo com cache

**Files:**
- Modify: `core/analise/base.py`, `core/analise/llm.py`, `core/auditoria.py`
- Test: `tests/test_analise_base.py`, `tests/test_auditoria.py`

**Interfaces:**
- Produces: `RespostaLLM.do_cache: bool = False`; `AchadoEnriquecido.do_cache: bool = False` (em `so_regras` precisa ser `False`); `nome_base(resultado: ResultadoAuditoria) -> str` em `core/auditoria.py` = `<projeto>-<AAAA-MM-DDTHHMMSS>[-so-regras]`; `gravar` usa `nome_base`; `resumir` imprime `Do cache: N` quando N > 0 e calcula o tempo médio só sobre achados com `do_cache=False`.

- [ ] **Step 1: Testes que falham**

`tests/test_analise_base.py`, ao fim:

```python
def test_do_cache_padrao_e_falso_e_so_regras_nao_pode_ter():
    assert _gerado().do_cache is False
    assert _gerado(do_cache=True).do_cache is True
    with pytest.raises(ValidationError, match="coerente"):
        AchadoEnriquecido(achado=achado(), contexto=[], situacao="so_regras", modelo=None, do_cache=True)
```

`tests/test_auditoria.py`: substituir `test_gravar_usa_projeto_data_e_hora_e_relê_igual` por

```python
def test_gravar_usa_projeto_data_e_hora_com_segundos_e_relê_igual(tmp_path):
    resultado, _ = _auditar(tmp_path)
    caminho = gravar(resultado, tmp_path / "saida")
    carimbo = resultado.gerado_em[:19].replace(":", "")
    assert caminho.name == f"Minimal-{carimbo}.json"
    assert caminho.stem == auditoria.nome_base(resultado)
    assert ResultadoAuditoria.model_validate_json(caminho.read_text(encoding="utf-8")) == resultado
```

substituir `test_duas_auditorias_no_mesmo_dia_nao_se_sobrescrevem` por

```python
def test_duas_auditorias_no_mesmo_minuto_nao_se_sobrescrevem(tmp_path):
    resultado, _ = _auditar(tmp_path)
    base = resultado.gerado_em[:17]
    um = resultado.model_copy(update={"gerado_em": base + "01"})
    outro = resultado.model_copy(update={"gerado_em": base + "02"})
    assert gravar(um, tmp_path / "saida") != gravar(outro, tmp_path / "saida")
```

e acrescentar

```python
def test_resumo_conta_o_cache_e_tira_do_tempo_medio(tmp_path):
    resultado, _ = _auditar(tmp_path)
    a, b = resultado.achados
    misto = resultado.model_copy(update={"achados": [
        a.model_copy(update={"segundos": 8.0}),
        b.model_copy(update={"segundos": 0.0, "do_cache": True}),
    ]})
    texto = resumir(misto)
    assert "Do cache: 1" in texto
    assert "medio 8.0s" in texto


def test_resumo_sem_cache_nao_menciona(tmp_path):
    resultado, _ = _auditar(tmp_path)
    assert "cache" not in resumir(resultado).lower()
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py tests/test_auditoria.py -q`
Expected: FAIL — `do_cache` desconhecido, `nome_base` ausente, carimbo sem segundos.

- [ ] **Step 2: Implementar**

`core/analise/llm.py`, em `RespostaLLM`, depois de `tokens_prompt`:

```python
    do_cache: bool = False
    """Veio de `ClienteComCache`, não de uma chamada ao modelo."""
```

`core/analise/base.py`, em `AchadoEnriquecido`, depois de `reducoes_de_contexto`:

```python
    do_cache: bool = False
    """A resposta veio do cache de respostas (`core/analise/cache.py`), não de uma
    chamada nova; `segundos` é o tempo desta leitura."""
```

e, no ramo `so_regras` do `_situacao_coerente`, acrescentar `and not self.do_cache` à expressão `coerentes`.

`core/auditoria.py`: acrescentar antes de `gravar`

```python
def nome_base(resultado: ResultadoAuditoria) -> str:
    """`<projeto>-<AAAA-MM-DDTHHMMSS>[-so-regras]`: com segundos, duas auditorias do
    mesmo projeto no mesmo minuto não se sobrescrevem (só regras leva 0,3 s)."""
    carimbo = resultado.gerado_em[:19].replace(":", "")
    sufixo = "-so-regras" if resultado.modo == "so_regras" else ""
    return f"{resultado.projeto}-{carimbo}{sufixo}"
```

e trocar o miolo de `gravar` (as linhas do comentário "Hora no nome", `carimbo`, `sufixo` e `caminho`) por:

```python
    caminho = pasta / f"{nome_base(resultado)}.json"
```

Em `resumir`, trocar `tempos = [a.segundos for a in achados if a.segundos is not None]` por

```python
    tempos = [a.segundos for a in achados if a.segundos is not None and not a.do_cache]
    do_cache = sum(1 for a in achados if a.do_cache)
```

e, logo antes de `if tempos:`, acrescentar

```python
    if do_cache:
        linhas.append(f"Do cache: {do_cache} (tempo medio so das chamadas reais)")
```

- [ ] **Step 3: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_base.py tests/test_auditoria.py tests/test_app_execucao.py -q`
Expected: PASS. (Se algum teste de `test_app_execucao.py` ou `test_app_interface.py` depender do nome com minutos, ajustar para `nome_base`.)

- [ ] **Step 4: Commit**

```bash
git add core/analise/base.py core/analise/llm.py core/auditoria.py tests/test_analise_base.py tests/test_auditoria.py
git commit -m "feat(auditoria): do_cache no contrato, nome com segundos e resumo com cache"
git push
```

---

### Task 3: Cache das respostas do LLM

**Files:**
- Create: `core/analise/cache.py`
- Modify: `core/analise/enriquecimento.py`, `core/auditoria.py` (`main`)
- Test: `tests/test_analise_cache.py`, `tests/test_auditoria.py`

**Interfaces:**
- Consumes: `RespostaLLM.do_cache`, `AchadoEnriquecido.do_cache` (Task 2); `NUM_CTX`, `SEED` de `core.analise.llm`.
- Produces: `PASTA_CACHE: Path` (= `RAIZ_REPO / "outputs" / "cache-llm"`); `chave_de(modelo: str, mensagens: list[dict[str, str]], esquema: dict) -> str`; `ClienteComCache(llm: LLMClient, pasta: Path = PASTA_CACHE)` com `nome`, `aquecer()`, `gerar()`; CLI `python -m core.auditoria <pasta> --cache`.

- [ ] **Step 1: Testes que falham**

`tests/test_analise_cache.py`:

```python
"""Cache das respostas do LLM: acerto, chave, falhas e rótulo."""

import json

import pytest

from core.analise.cache import ClienteComCache, chave_de
from core.analise.llm import ContextoExcedido, ErroDeLLM
from fabricas_analise import LLMFalso

MENSAGENS = [{"role": "user", "content": "explique"}]
ESQUEMA = {"type": "object"}


def test_segunda_chamada_vem_do_cache_sem_chamar_o_llm(tmp_path):
    llm = LLMFalso('{"a": 1}')
    cliente = ClienteComCache(llm, tmp_path)
    primeira = cliente.gerar(MENSAGENS, ESQUEMA)
    segunda = cliente.gerar(MENSAGENS, ESQUEMA)
    assert (primeira.texto, primeira.do_cache) == ('{"a": 1}', False)
    assert (segunda.texto, segunda.do_cache) == ('{"a": 1}', True)
    assert len(llm.chamadas) == 1
    assert cliente.nome == "llm-falso"


def test_chave_muda_com_mensagens_esquema_e_modelo():
    base = chave_de("m", MENSAGENS, ESQUEMA)
    assert base == chave_de("m", [dict(MENSAGENS[0])], dict(ESQUEMA))
    assert base != chave_de("m", [{"role": "user", "content": "explique."}], ESQUEMA)
    assert base != chave_de("m", MENSAGENS, {"type": "array"})
    assert base != chave_de("outro", MENSAGENS, ESQUEMA)


@pytest.mark.parametrize("falha", [ErroDeLLM("caiu"), ContextoExcedido("longo")])
def test_falha_do_llm_passa_adiante_e_nao_e_guardada(tmp_path, falha):
    cliente = ClienteComCache(LLMFalso(falha), tmp_path)
    with pytest.raises(ErroDeLLM):
        cliente.gerar(MENSAGENS, ESQUEMA)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("conteudo", ["{ quebrado", json.dumps({"outro": 1}), json.dumps({"texto": 5})])
def test_arquivo_ilegivel_ou_de_outro_formato_e_tratado_como_ausente(tmp_path, conteudo):
    """Review Focus 2."""
    (tmp_path / f"{chave_de('llm-falso', MENSAGENS, ESQUEMA)}.json").write_text(conteudo, encoding="utf-8")
    llm = LLMFalso('{"a": 2}')
    resposta = ClienteComCache(llm, tmp_path).gerar(MENSAGENS, ESQUEMA)
    assert (resposta.texto, resposta.do_cache, len(llm.chamadas)) == ('{"a": 2}', False, 1)
    assert ClienteComCache(LLMFalso(), tmp_path).gerar(MENSAGENS, ESQUEMA).texto == '{"a": 2}'


def test_pasta_sem_escrita_usa_a_resposta_e_nao_grava(tmp_path):
    arquivo_no_lugar_da_pasta = tmp_path / "cache"
    arquivo_no_lugar_da_pasta.write_text("x", encoding="utf-8")
    resposta = ClienteComCache(LLMFalso('{"a": 3}'), arquivo_no_lugar_da_pasta).gerar(MENSAGENS, ESQUEMA)
    assert resposta.texto == '{"a": 3}'


def test_aquecer_vai_sempre_ao_llm_real(tmp_path):
    llm = LLMFalso(falha_no_aquecimento=True)
    with pytest.raises(ErroDeLLM):
        ClienteComCache(llm, tmp_path).aquecer()
    assert llm.aquecimentos == 1
```

Em `tests/test_auditoria.py`, acrescentar:

```python
def test_auditoria_repetida_com_cache_da_textos_iguais_sem_chamar_o_llm(tmp_path):
    from core.analise.cache import ClienteComCache

    pasta_cache = tmp_path / "cache"
    pbip = _pbip(tmp_path)
    primeira_llm = LLMFalso()
    primeira = run_audit(pbip, llm=ClienteComCache(primeira_llm, pasta_cache), base=base_padrao(),
                         registro=_registro(), gabaritos={"MOD-001": gabarito()})
    segunda_llm = LLMFalso()
    segunda = run_audit(pbip, llm=ClienteComCache(segunda_llm, pasta_cache), base=base_padrao(),
                        registro=_registro(), gabaritos={"MOD-001": gabarito()})
    assert [a.geracao for a in segunda.achados] == [a.geracao for a in primeira.achados]
    assert [a.do_cache for a in primeira.achados] == [False, False]
    assert [a.do_cache for a in segunda.achados] == [True, True]
    assert (len(segunda_llm.chamadas), segunda_llm.aquecimentos) == (0, 1)


def test_comando_com_cache_envolve_o_cliente(tmp_path, monkeypatch, capsys):
    _comando_falso(monkeypatch, tmp_path)
    monkeypatch.setattr(auditoria, "PASTA_CACHE", tmp_path / "cache")
    assert auditoria.main([str(_pbip(tmp_path)), "--cache"]) == 0
    assert auditoria.main([str(_pbip(tmp_path / "de-novo")), "--cache"]) == 0
    assert "Do cache: 2" in capsys.readouterr().out
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_cache.py tests/test_auditoria.py -q`
Expected: FAIL — `ModuleNotFoundError: core.analise.cache`.

- [ ] **Step 2: Implementar `core/analise/cache.py`**

```python
"""Cache das respostas do LLM (F16; spec de 13/10/2026, seção 4).

Uma auditoria repetida do mesmo projeto roda ao vivo em segundos e com os mesmos
textos. A chave cobre modelo, mensagens, esquema e opções de geração: qualquer
mudança no prompt — regra, contexto recuperado, texto do prompt — é outra chave,
e não há invalidação manual. Só respostas bem-sucedidas entram. `aquecer()` vai
sempre ao modelo real: com o Ollama fora do ar a auditoria aborta (ADR-003).
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from core.analise.llm import NUM_CTX, SEED, LLMClient, RespostaLLM
from rag.avaliacao import RAIZ_REPO

logger = logging.getLogger(__name__)

PASTA_CACHE = RAIZ_REPO / "outputs" / "cache-llm"


def chave_de(modelo: str, mensagens: list[dict[str, str]], esquema: dict) -> str:
    canonico = json.dumps(
        {
            "modelo": modelo,
            "mensagens": mensagens,
            "esquema": esquema,
            "opcoes": {"num_ctx": NUM_CTX, "temperature": 0, "seed": SEED},
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


class ClienteComCache:
    def __init__(self, llm: LLMClient, pasta: Path = PASTA_CACHE) -> None:
        self.llm = llm
        self.pasta = pasta
        self.nome = llm.nome

    def aquecer(self) -> None:
        self.llm.aquecer()

    def _ler(self, arquivo: Path) -> dict | None:
        if not arquivo.is_file():
            return None
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            logger.warning("cache ilegível em %s, chamando o LLM: %s", arquivo.name, erro)
            return None
        if not isinstance(dados, dict) or not isinstance(dados.get("texto"), str):
            logger.warning("cache de outro formato em %s, chamando o LLM", arquivo.name)
            return None
        return dados

    def _gravar(self, arquivo: Path, resposta: RespostaLLM) -> None:
        dados = {
            "texto": resposta.texto,
            "tokens_prompt": resposta.tokens_prompt,
            "modelo": self.nome,
            "gravado_em": datetime.now().isoformat(timespec="seconds"),
        }
        temporario = arquivo.with_suffix(".tmp")
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
            os.replace(temporario, arquivo)
        except OSError as erro:
            logger.warning("não consegui gravar o cache em %s: %s", self.pasta, erro)

    def gerar(self, mensagens: list[dict[str, str]], esquema: dict) -> RespostaLLM:
        inicio = time.perf_counter()
        arquivo = self.pasta / f"{chave_de(self.nome, mensagens, esquema)}.json"
        guardada = self._ler(arquivo)
        if guardada is not None:
            return RespostaLLM(
                texto=guardada["texto"],
                segundos=round(time.perf_counter() - inicio, 2),
                tokens_prompt=guardada.get("tokens_prompt"),
                do_cache=True,
            )
        resposta = self.llm.gerar(mensagens, esquema)
        self._gravar(arquivo, resposta)
        return resposta
```

- [ ] **Step 3: Propagar `do_cache` e ligar `--cache`**

`core/analise/enriquecimento.py`: trocar `comum.update(segundos=resposta.segundos, tokens_prompt=resposta.tokens_prompt)` por

```python
    comum.update(segundos=resposta.segundos, tokens_prompt=resposta.tokens_prompt, do_cache=resposta.do_cache)
```

`core/auditoria.py`: import `from core.analise.cache import PASTA_CACHE, ClienteComCache` (ordem alfabética, antes de `core.analise.contexto`); em `main`, depois do `--so-regras`:

```python
    parser.add_argument(
        "--cache", action="store_true",
        help="reusa respostas guardadas do LLM (outputs/cache-llm); o resultado marca o que veio do cache",
    )
```

e trocar o ramo completo:

```python
        else:
            llm = ClienteOllama(args.modelo)
            if args.cache:
                llm = ClienteComCache(llm, PASTA_CACHE)
            resultado = run_audit(args.pasta_pbip, llm=llm, base=BaseRag.carregar())
```

(`PASTA_CACHE` é lido do módulo `auditoria` na hora da chamada, para o teste poder trocá-lo.)

- [ ] **Step 4: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analise_cache.py tests/test_auditoria.py tests/test_analise_enriquecimento.py -q`
Expected: PASS.

- [ ] **Step 5: Suíte inteira** — `.\.venv\Scripts\python.exe -m pytest -q` → tudo passa.

- [ ] **Step 6: Commit**

```bash
git add core/analise/cache.py core/analise/enriquecimento.py core/auditoria.py tests/test_analise_cache.py tests/test_auditoria.py
git commit -m "feat(analise): cache das respostas do LLM, opcional e rotulado (--cache)"
git push
```

---

### Task 4: Leitura do resultado e contagem do cache em `core/apresentacao.py`

**Files:**
- Modify: `core/apresentacao.py`, `app/execucao.py`
- Test: `tests/test_apresentacao.py`, `tests/test_app_execucao.py`

**Interfaces:**
- Consumes: `AchadoEnriquecido.do_cache` (Task 2).
- Produces: `ErroDeLeitura(Exception)`; `ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria` em `core.apresentacao` (aceita BOM UTF-8; mensagens iguais às de hoje); `Linha.do_cache: bool`; `Resumo.do_cache: int`. `app.execucao.ler_resultado` passa a delegar e converter `ErroDeLeitura` em `ErroParaUsuario`; nova `app.execucao.ler_salvo(caminho: Path) -> ResultadoAuditoria` (OSError → `ErroParaUsuario`).

- [ ] **Step 1: Testes que falham**

`tests/test_apresentacao.py`, ao fim (os três imports vão para o topo do arquivo, junto dos outros):

```python
from pathlib import Path

import pytest

from core.apresentacao import ErroDeLeitura, ler_resultado

FIXTURE_FORMATO_ANTIGO = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def test_resumo_conta_achados_do_cache():
    resultado = _resultado([_gerado(achado("MOD-001", objeto="A"), do_cache=True), _gerado(achado("MOD-001", objeto="B"))])
    ls = consulta.linhas(resultado, _registro())
    assert [l.do_cache for l in ls] == [True, False]
    assert consulta.resumir(ls).do_cache == 1


def test_ler_resultado_aceita_bom():
    bruto = FIXTURE_FORMATO_ANTIGO.read_bytes()
    assert ler_resultado(b"\xef\xbb\xbf" + bruto).modo == "completo"
    assert ler_resultado("﻿" + bruto.decode("utf-8")).modo == "completo"


def test_ler_resultado_recusa_formato_e_regra_desconhecida():
    with pytest.raises(ErroDeLeitura, match="não é um resultado de auditoria"):
        ler_resultado(b"{ quebrado")
    with pytest.raises(ErroDeLeitura, match="XYZ-999"):
        ler_resultado(FIXTURE_FORMATO_ANTIGO.read_text(encoding="utf-8").replace("MOD-001", "XYZ-999"))
```

`tests/test_app_execucao.py`, ao fim:

```python
def test_ler_salvo_que_sumiu_vira_mensagem(tmp_path):
    with pytest.raises(ErroParaUsuario, match="Não consegui abrir"):
        execucao.ler_salvo(tmp_path / "sumiu.json")


def test_ler_salvo_le_o_arquivo():
    assert execucao.ler_salvo(FIXTURE_FORMATO_ANTIGO).modo == "completo"
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_apresentacao.py tests/test_app_execucao.py -q`
Expected: FAIL — `ImportError: ErroDeLeitura`, `ler_salvo` ausente, `Linha` sem `do_cache`.

- [ ] **Step 2: Implementar em `core/apresentacao.py`**

Imports: acrescentar `from pydantic import ValidationError` e `from core.rules.todas import REGISTRO`.

Em `Linha`, depois de `aviso: bool`: `do_cache: bool = False`. Em `linhas()`, no construtor de `Linha`, acrescentar `do_cache=item.do_cache,`.

Em `Resumo`, depois de `com_aviso: int`: `do_cache: int = 0`; em `resumir`, acrescentar `do_cache=sum(1 for l in todas if l.do_cache),`.

Ao fim do módulo:

```python
BOM = "﻿"


class ErroDeLeitura(Exception):
    """O conteúdo não é um resultado que esta versão da ferramenta saiba mostrar."""


def ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria:
    """Mesma leitura para a interface e para a CLI do relatório. Aceita o BOM que o
    Bloco de Notas põe ao salvar de novo um JSON."""
    if isinstance(conteudo, bytes) and conteudo.startswith(BOM.encode("utf-8")):
        conteudo = conteudo[len(BOM.encode("utf-8")):]
    elif isinstance(conteudo, str) and conteudo.startswith(BOM):
        conteudo = conteudo[len(BOM):]
    try:
        resultado = ResultadoAuditoria.model_validate_json(conteudo)
    except ValidationError as erro:
        raise ErroDeLeitura(
            "O arquivo não é um resultado de auditoria desta ferramenta "
            f"({erro.error_count()} problema(s) no formato)."
        ) from erro
    registro = REGISTRO if registro is None else registro
    desconhecidas = sorted({a.achado.id_regra for a in resultado.achados} - set(registro.ids()))
    if desconhecidas:
        raise ErroDeLeitura(
            f"O resultado tem regras que esta versão da ferramenta não conhece: {', '.join(desconhecidas)}."
        )
    return resultado
```

- [ ] **Step 3: `app/execucao.py` delega**

Substituir `ler_resultado` por:

```python
def ler_resultado(conteudo: bytes | str, registro: Registro | None = None) -> ResultadoAuditoria:
    try:
        return apresentacao.ler_resultado(conteudo, auditoria.REGISTRO if registro is None else registro)
    except apresentacao.ErroDeLeitura as erro:
        raise ErroParaUsuario(str(erro)) from erro


def ler_salvo(caminho: Path) -> ResultadoAuditoria:
    """O arquivo listado pode ter sumido entre a listagem e o clique."""
    try:
        conteudo = caminho.read_bytes()
    except OSError as erro:
        raise ErroParaUsuario(f"Não consegui abrir {caminho.name}: {erro}") from erro
    return ler_resultado(conteudo)
```

Imports: `from core import apresentacao, auditoria`; remover `from pydantic import ValidationError` se não sobrar uso (a Task 9 volta a usá-lo).

(`auditoria.REGISTRO` continua sendo o ponto de troca dos testes de `test_app_execucao.py`.)

Em `app/streamlit_app.py`, no botão "Abrir": `_abrir(Path(escolhido).read_bytes())` → trocar `_abrir` para receber uma função de leitura:

```python
def _abrir(ler) -> None:
    try:
        estado.resultado = ler()
    except execucao.ErroParaUsuario as erro:
        estado.mensagem = ("error", str(erro))  # o resultado anterior continua
    else:
        estado.traducoes = {}
        estado.pdf = None
        estado.mensagem = None
```

com as chamadas `_abrir(lambda: execucao.ler_salvo(Path(escolhido)))` e `_abrir(lambda: execucao.ler_resultado(externo.getvalue()))`, e `estado.setdefault("pdf", None)` junto dos outros `setdefault`.

- [ ] **Step 4: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_apresentacao.py tests/test_app_execucao.py tests/test_app_interface.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/apresentacao.py app/execucao.py app/streamlit_app.py tests/test_apresentacao.py tests/test_app_execucao.py
git commit -m "feat(apresentacao): leitura do resultado em core, aceita BOM, e contagem do cache"
git push
```

---

### Task 5: Relatório HTML (`reports/html.py` + template)

**Files:**
- Create: `reports/__init__.py` (vazio), `reports/html.py`, `reports/templates/relatorio.html.j2`
- Modify: `requirements.txt`
- Test: `tests/test_relatorio_html.py`

**Interfaces:**
- Consumes: `core.apresentacao` (`linhas`, `avisos`, `resumir`, `examinado`), `url_em_portugues`, `REGISTRO`.
- Produces: `gerar_html(resultado: ResultadoAuditoria, *, tecnico: bool = False, registro: Registro | None = None) -> str`; `PASTA_TEMPLATES`.

- [ ] **Step 1: Dependência**

Acrescentar ao `requirements.txt`:

```
# Fase 4 - relatório (o PDF usa o Edge do sistema: sem `playwright install`)
jinja2==3.1.6
playwright==1.62.0
```

Run: `.\.venv\Scripts\python.exe -m pip install jinja2==3.1.6 playwright==1.62.0` e `.\.venv\Scripts\python.exe -m pip check`
Expected: instalado, "No broken requirements found." (Conflito = parar e reportar.)

- [ ] **Step 2: Testes que falham**

`tests/test_relatorio_html.py`:

```python
"""Relatório HTML: conteúdo, avisos, escape, seção técnica e autocontenção."""

import re

from core.analise.base import AchadoEnriquecido, Fidelidade, Geracao
from core.auditoria import ResultadoAuditoria
from core.rules.base import RegraMeta
from core.rules.expressoes import LacunaDax
from core.rules.registry import Registro
from core.rules.runner import FalhaDeRegra, ResultadoRegras
from fabricas_analise import RECOMENDACAO_PADRAO, achado, contexto
from reports.html import gerar_html

URL_REGRA = "https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time"


def _registro() -> Registro:
    registro = Registro()
    registro.registrar(RegraMeta(
        id="MOD-001", titulo="Tempo automático de data/hora está ligado", categoria="modelagem",
        severidade="alta", url_canonica=URL_REGRA, termos_consulta=("t",), recomendacao_padrao=RECOMENDACAO_PADRAO,
    ), lambda m: [])
    return registro


def _gerado(objeto="LocalDateTable_1", **extra) -> AchadoEnriquecido:
    campos = dict(
        achado=achado(objeto=objeto), contexto=contexto(2),
        geracao=Geracao(explicacao="A tabela automática aumenta o modelo.",
                        recomendacao="Desative a opção.", citacoes=[1]),
        situacao="gerado", cita_ancora=True, fidelidade=Fidelidade(), modelo="m", segundos=8.1, tokens_prompt=1200,
    )
    campos.update(extra)
    return AchadoEnriquecido(**campos)


def _resultado(achados, regras=None, **extra) -> ResultadoAuditoria:
    campos = dict(
        projeto="P8_contoso-vendas", modelo_llm="qwen", gerado_em="2026-10-13T19:45:31",
        regras=regras or ResultadoRegras(regras_executadas=1, expressoes_analisadas=105),
        achados=achados, segundos_total=155.1,
    )
    campos.update(extra)
    return ResultadoAuditoria(**campos)


def test_cabecalho_painel_resumo_e_achado():
    html = gerar_html(_resultado([_gerado()]), registro=_registro())
    assert "P8_contoso-vendas" in html
    assert "1 de 1 regras executadas" in html
    assert "105 de 105 expressões DAX analisadas" in html
    assert "não lê a camada de relatório" in html
    assert "A tabela automática aumenta o modelo." in html
    assert "Desative a opção." in html
    assert "Disable the auto date/time option." in html  # texto original do trecho citado
    assert 'href="#achado-1"' in html and 'id="achado-1"' in html


def test_avisos_aparecem():
    html = gerar_html(_resultado([
        _gerado(cita_ancora=False),
        AchadoEnriquecido(achado=achado(objeto="T2"), contexto=contexto(1), situacao="sem_fundamentacao",
                          motivo_descarte="json_invalido", modelo="m"),
    ]), registro=_registro())
    assert "Não cita a seção âncora da regra" in html
    assert "Sem fundamentação — recomendação padrão da regra" in html
    assert RECOMENDACAO_PADRAO in html


def test_so_regras_tem_selo_e_recomendacao_padrao():
    resultado = _resultado([AchadoEnriquecido.so_regras(achado())], modo="so_regras", modelo_llm=None)
    html = gerar_html(resultado, registro=_registro())
    assert "só regras" in html
    assert RECOMENDACAO_PADRAO in html
    assert "Fontes citadas" not in html


def test_falha_de_regra_lacuna_e_zero_achados():
    regras = ResultadoRegras(
        regras_executadas=0, regras_com_falha=[FalhaDeRegra(id_regra="MOD-001", erro="KeyError: 'x'")],
        expressoes_analisadas=9,
        lacunas_de_expressao=[LacunaDax(sitio="medida", objeto="[Total]", tabela="Vendas", posicao=12,
                                        trecho="SUM(", motivo="parêntese sem par")],
    )
    html = gerar_html(_resultado([], regras), registro=_registro())
    assert "MOD-001: KeyError" in html
    assert "[Total] (medida, posição 12): parêntese sem par" in html
    assert "Nenhum achado" in html


def test_escapa_html_vindo_do_modelo_e_do_llm():
    """Review Focus 4."""
    malicioso = _gerado(
        objeto="<script>alert(1)</script>",
        geracao=Geracao(explicacao='<img src=x onerror="alert(2)">', recomendacao="r", citacoes=[1]),
    )
    html = gerar_html(_resultado([malicioso]), registro=_registro())
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)" in html
    assert "<img src=x" not in html


def test_secao_tecnica_so_quando_pedida():
    resultado = _resultado([_gerado(do_cache=True)])
    sem = gerar_html(resultado, registro=_registro())
    com = gerar_html(resultado, tecnico=True, registro=_registro())
    assert "Seção técnica" not in sem and "Seção técnica" in com
    assert "1200" in com  # tokens
    assert "1 explicação(ões) vieram do cache" in sem


def test_links_em_portugues_e_nada_externo_alem_do_learn():
    html = gerar_html(_resultado([_gerado()]), registro=_registro())
    assert "https://learn.microsoft.com/pt-br/power-bi/guidance/auto-date-time" in html
    externos = re.findall(r'(?:src|href)="(?!#)([^"]+)"', html)
    assert externos and all(u.startswith("https://learn.microsoft.com/") for u in externos)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_html.py -q`
Expected: FAIL — `ModuleNotFoundError: reports.html`.

- [ ] **Step 3: Implementar `reports/html.py`**

```python
"""Relatório HTML da auditoria (F13; spec de 13/10/2026, seção 3).

Autocontido: CSS embutido e nenhum recurso externo além dos links para o Learn.
Todo texto passa pelo autoescape do Jinja2. Cita o texto original dos trechos;
tradução automática não entra.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from core import apresentacao
from core.auditoria import ResultadoAuditoria
from core.rules.registry import Registro
from core.rules.todas import REGISTRO
from rag.catalogo import url_em_portugues

PASTA_TEMPLATES = Path(__file__).resolve().parent / "templates"

_ambiente = Environment(
    loader=FileSystemLoader(PASTA_TEMPLATES),
    autoescape=select_autoescape(["html", "j2"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

ROTULOS_SEVERIDADE = {"alta": "alta", "media": "média", "baixa": "baixa"}


def _bloco(resultado: ResultadoAuditoria, linha: apresentacao.Linha, numero: int, registro: Registro) -> dict:
    item = resultado.achados[linha.indice]
    meta = registro.meta(item.achado.id_regra)
    por_numero = {t.numero: t for t in item.contexto}
    citacoes = [
        {"trecho": por_numero[n], "url": f"{por_numero[n].url}#{por_numero[n].ancora}",
         "url_pt": url_em_portugues(por_numero[n].url)}
        for n in (item.geracao.citacoes if item.geracao else [])
    ]
    return {
        "numero": numero, "linha": linha, "item": item, "meta": meta,
        "avisos": apresentacao.avisos(item), "citacoes": citacoes,
        "recomendacao": item.recomendacao_final(meta),
    }


def gerar_html(
    resultado: ResultadoAuditoria, *, tecnico: bool = False, registro: Registro | None = None
) -> str:
    registro = REGISTRO if registro is None else registro
    linhas = apresentacao.linhas(resultado, registro)
    regras = [{"meta": m, "url_pt": url_em_portugues(m.url_canonica)} for m in registro.metas()]
    return _ambiente.get_template("relatorio.html.j2").render(
        resultado=resultado,
        examinado=apresentacao.examinado(resultado),
        resumo=apresentacao.resumir(linhas),
        blocos=[_bloco(resultado, l, i, registro) for i, l in enumerate(linhas, start=1)],
        regras=regras,
        tecnico=tecnico,
        severidade=ROTULOS_SEVERIDADE,
    )
```

- [ ] **Step 4: Template `reports/templates/relatorio.html.j2`**

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Auditoria — {{ resultado.projeto }}</title>
<style>
  :root { --tinta: #1f2328; --suave: #59636e; --linha: #d1d9e0; --fundo: #f6f8fa;
          --alta: #b42318; --media: #b54708; --baixa: #8a6d00; --aviso: #fff4e5; --info: #eef4ff; }
  * { box-sizing: border-box; }
  body { font: 14px/1.5 "Segoe UI", system-ui, sans-serif; color: var(--tinta); margin: 0 auto;
         max-width: 960px; padding: 32px 24px; background: #fff; }
  h1 { font-size: 26px; margin: 0 0 4px; } h2 { font-size: 19px; margin: 32px 0 8px; border-bottom: 1px solid var(--linha); padding-bottom: 4px; }
  h3 { font-size: 16px; margin: 0 0 4px; } .suave { color: var(--suave); }
  .selo { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 12px; background: var(--info); }
  .caixa { border: 1px solid var(--linha); border-radius: 6px; padding: 12px 16px; margin: 12px 0; background: var(--fundo); }
  .aviso { border-left: 4px solid var(--media); background: var(--aviso); padding: 8px 12px; margin: 8px 0; }
  .falha { border-left: 4px solid var(--alta); background: #fdecea; padding: 8px 12px; margin: 8px 0; }
  .sev-alta { color: var(--alta); font-weight: 600; } .sev-media { color: var(--media); font-weight: 600; }
  .sev-baixa { color: var(--baixa); font-weight: 600; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border-bottom: 1px solid var(--linha); padding: 4px 6px; text-align: left; vertical-align: top; }
  th { background: var(--fundo); }
  .numeros { display: flex; gap: 24px; flex-wrap: wrap; } .numeros div { min-width: 90px; }
  .numeros strong { display: block; font-size: 22px; }
  .achado { border: 1px solid var(--linha); border-radius: 6px; padding: 12px 16px; margin: 12px 0; }
  pre { background: var(--fundo); border: 1px solid var(--linha); padding: 8px; white-space: pre-wrap; word-break: break-word; font-size: 12px; }
  blockquote { margin: 6px 0; padding: 6px 12px; border-left: 3px solid var(--linha); color: var(--suave); }
  a { color: #0b5cad; } .quebra { word-break: break-all; }
  @media print {
    body { padding: 0; max-width: none; }
    .achado, .caixa, tr { break-inside: avoid; }
    h2 { break-after: avoid; }
  }
</style>
</head>
<body>

<header>
  <p class="suave">Relatório de auditoria de modelo semântico do Power BI (PBIP)</p>
  <h1>{{ resultado.projeto }}</h1>
  <p class="suave">
    Auditado em {{ resultado.gerado_em | replace("T", " ") }} ·
    {% if resultado.modo == "so_regras" %}<span class="selo">só regras (sem LLM)</span>
    {% else %}completo — modelo {{ resultado.modelo_llm }}{% endif %}
    · {{ "%.1f" | format(resultado.segundos_total) }} s
  </p>
  <p>
    A ferramenta lê o modelo semântico salvo no projeto (tabelas, colunas, medidas, relacionamentos),
    aplica regras determinísticas ancoradas na documentação oficial e, no modo completo, pede ao modelo
    de linguagem uma explicação que cite essa documentação. Ela não lê a camada de relatório (visuais e
    páginas) nem os dados.
  </p>
  {% if resultado.modo == "so_regras" %}
  <p class="caixa">Resultado só regras: os achados vêm da detecção determinística, com a recomendação
    padrão de cada regra e sem explicação do modelo de linguagem.</p>
  {% endif %}
</header>

<section>
  <h2>O que foi examinado</h2>
  <ul>
    <li>{{ examinado.regras }}</li>
    <li>{{ examinado.expressoes }}</li>
  </ul>
  {% for falha in examinado.falhas %}<div class="falha">Regra com falha — {{ falha }}</div>{% endfor %}
  {% if examinado.lacunas %}
  <div class="aviso">{{ examinado.lacunas | length }} expressão(ões) DAX não analisada(s) pelo leitor de DAX:
    <ul>{% for lacuna in examinado.lacunas %}<li>{{ lacuna }}</li>{% endfor %}</ul>
  </div>
  {% endif %}
</section>

<section>
  <h2>Resumo</h2>
  <div class="numeros">
    <div><strong>{{ resumo.total }}</strong>achados</div>
    {% for sev, n in resumo.por_severidade.items() %}
    <div><strong class="sev-{{ sev }}">{{ n }}</strong>{{ severidade[sev] }}</div>
    {% endfor %}
    <div><strong>{{ resumo.com_aviso }}</strong>com aviso</div>
  </div>
  {% if resumo.por_categoria %}
  <p class="suave">{% for cat, n in resumo.por_categoria.items() %}{{ cat }}: {{ n }}{% if not loop.last %} · {% endif %}{% endfor %}</p>
  {% endif %}
  {% if resumo.do_cache %}
  <p class="suave">{{ resumo.do_cache }} explicação(ões) vieram do cache de respostas do modelo, não de uma chamada nova.</p>
  {% endif %}
</section>

<section>
  <h2>Achados</h2>
  {% if not blocos %}
  <p>Nenhum achado.</p>
  {% else %}
  <table>
    <thead><tr><th>#</th><th>Severidade</th><th>Regra</th><th>Objeto</th><th>Tabela</th><th>Aviso</th></tr></thead>
    <tbody>
    {% for b in blocos %}
      <tr>
        <td><a href="#achado-{{ b.numero }}">{{ b.numero }}</a></td>
        <td class="sev-{{ b.linha.severidade }}">{{ severidade[b.linha.severidade] }}</td>
        <td>{{ b.linha.regra }}</td>
        <td class="quebra">{{ b.linha.objeto }}</td>
        <td class="quebra">{{ b.linha.tabela }}</td>
        <td>{% if b.linha.aviso %}⚠{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  {% for b in blocos %}
  {% if loop.changed(b.linha.regra) %}<h2>{{ b.meta.id }} — {{ b.meta.titulo }}</h2>{% endif %}
  <article class="achado" id="achado-{{ b.numero }}">
    <h3>{{ b.numero }}. <span class="quebra">{{ b.item.achado.evidencia.objeto }}</span></h3>
    <p class="suave"><span class="sev-{{ b.meta.severidade }}">{{ severidade[b.meta.severidade] }}</span>
      · {{ b.meta.categoria }} · {{ b.item.achado.evidencia.tipo_objeto }}</p>
    <p>{{ b.item.achado.mensagem }}</p>
    {% for aviso in b.avisos %}<div class="aviso"><strong>{{ aviso.titulo }}</strong> — {{ aviso.explicacao }}</div>{% endfor %}
    {% if b.item.achado.evidencia.trecho %}<pre>{{ b.item.achado.evidencia.trecho }}</pre>{% endif %}
    {% if b.item.achado.evidencia.detalhe %}
    <p class="suave">Valores lidos pela regra:
      {% for chave, valor in b.item.achado.evidencia.detalhe.items() %}{{ chave }} = {{ valor }}{% if not loop.last %}; {% endif %}{% endfor %}</p>
    {% endif %}
    {% if b.item.geracao %}<p><strong>Explicação.</strong> {{ b.item.geracao.explicacao }}</p>{% endif %}
    <p><strong>Recomendação.</strong> {{ b.recomendacao }}</p>
    {% if b.citacoes %}
    <p><strong>Fontes citadas</strong></p>
    {% for c in b.citacoes %}
    <p>[{{ c.trecho.numero }}] <a href="{{ c.url }}">{{ c.trecho.titulo }} — {{ c.trecho.caminho }}</a>
      {% if c.url_pt %} · <a href="{{ c.url_pt }}">ler em português</a>{% endif %}</p>
    <blockquote>{{ c.trecho.texto }}</blockquote>
    {% endfor %}
    {% endif %}
  </article>
  {% endfor %}
  {% endif %}
</section>

<section>
  <h2>Regras aplicadas</h2>
  <table>
    <thead><tr><th>Regra</th><th>Título</th><th>Severidade</th><th>Categoria</th><th>Fundamentação</th></tr></thead>
    <tbody>
    {% for r in regras %}
      <tr>
        <td>{{ r.meta.id }}</td><td>{{ r.meta.titulo }}</td>
        <td class="sev-{{ r.meta.severidade }}">{{ severidade[r.meta.severidade] }}</td><td>{{ r.meta.categoria }}</td>
        <td><a href="{{ r.meta.url_canonica }}">Microsoft Learn</a>{% if r.url_pt %} · <a href="{{ r.url_pt }}">em português</a>{% endif %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</section>

{% if tecnico %}
<section>
  <h2>Seção técnica</h2>
  <p class="suave">O que o modelo de linguagem leu em cada achado, para julgar a citação.</p>
  {% for b in blocos %}
  <div class="caixa">
    <h3>{{ b.numero }}. {{ b.linha.regra }} — <span class="quebra">{{ b.linha.objeto }}</span></h3>
    <p class="suave">Situação: {{ b.item.situacao }}{% if b.item.motivo_descarte %} ({{ b.item.motivo_descarte }}){% endif %}
      · modelo: {{ b.item.modelo or "—" }}
      · tempo: {{ b.item.segundos if b.item.segundos is not none else "—" }} s
      · tokens do prompt: {{ b.item.tokens_prompt if b.item.tokens_prompt is not none else "—" }}
      · trechos retirados para caber: {{ b.item.reducoes_de_contexto }}
      {% if b.item.do_cache %}· <strong>do cache</strong>{% endif %}</p>
    {% for t in b.item.contexto %}
    <p><strong>[{{ t.numero }}] {{ t.titulo }} — {{ t.caminho }}</strong>
      ({{ "âncora da regra" if t.origem == "ancora" else "busca" }})</p>
    <blockquote>{{ t.texto }}</blockquote>
    {% endfor %}
  </div>
  {% endfor %}
</section>
{% endif %}

</body>
</html>
```

- [ ] **Step 5: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_html.py -q`
Expected: PASS. Se o teste da contagem do cache falhar no texto, o template escreve "explicação(ões) vieram do cache" e o teste confere `"1 explicação(ões) vieram do cache"` — manter os dois iguais.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt reports/__init__.py reports/html.py reports/templates/relatorio.html.j2 tests/test_relatorio_html.py
git commit -m "feat(reports): relatorio HTML autocontido com Jinja2"
git push
```

---

### Task 6: PDF pelo Edge (`reports/pdf.py`) e emenda da ADR-002

**Files:**
- Create: `reports/pdf.py`
- Modify: `pytest.ini` (marcador `pdf`), `docs/adr/ADR-002-stack-tecnologica.md`
- Test: `tests/test_relatorio_pdf.py`

**Interfaces:**
- Produces: `ErroDePdf(Exception)`; `gerar_pdf(html: str, destino: Path, *, timeout_s: float = 60) -> Path`; `CANAL = "msedge"`. `sync_playwright` e `ErroPlaywright` são atributos do módulo (pontos de troca dos testes; `None`/`Exception` quando o pacote falta).

- [ ] **Step 1: Testes que falham**

`pytest.ini`, em `markers`, acrescentar a linha:

```
    pdf: gera PDF pelo Edge do sistema; pulado quando o Playwright ou o Edge não estão disponíveis
```

`tests/test_relatorio_pdf.py`:

```python
"""PDF pelo Edge do sistema: real quando possível, e os caminhos de erro simulados."""

import asyncio

import pytest

from reports import pdf
from reports.pdf import ErroDePdf, gerar_pdf

HTML = "<!doctype html><html><body><h1>Relatório</h1><p>Olá, ação.</p></body></html>"


def _gerar_ou_pular(destino):
    if pdf.sync_playwright is None:
        pytest.skip("pacote playwright não instalado")
    try:
        return gerar_pdf(HTML, destino)
    except ErroDePdf as erro:
        if "is not found" in str(erro) or "não encontrado" in str(erro):
            pytest.skip(f"Edge indisponível: {erro}")
        raise


@pytest.mark.pdf
def test_pdf_real_pelo_edge(tmp_path):
    caminho = _gerar_ou_pular(tmp_path / "saida" / "r.pdf")
    assert caminho.read_bytes()[:4] == b"%PDF"


@pytest.mark.pdf
def test_pdf_real_de_dentro_de_um_loop_asyncio(tmp_path):
    """Review Focus 1: a API síncrona do Playwright recusa rodar dentro de um loop."""
    async def dentro_do_loop():
        return _gerar_ou_pular(tmp_path / "r.pdf")

    assert asyncio.run(dentro_do_loop()).read_bytes()[:4] == b"%PDF"


def test_pacote_ausente_vira_erro_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(pdf, "sync_playwright", None)
    with pytest.raises(ErroDePdf, match="playwright não está instalado"):
        gerar_pdf(HTML, tmp_path / "r.pdf")


def test_falha_ao_abrir_o_edge_vira_erro_claro(tmp_path, monkeypatch):
    class Falha(Exception):
        pass

    class Chromium:
        def launch(self, **kwargs):
            assert kwargs["channel"] == "msedge"
            raise Falha("Chromium distribution 'msedge' is not found")

    class Contexto:
        chromium = Chromium()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(pdf, "ErroPlaywright", Falha)
    monkeypatch.setattr(pdf, "sync_playwright", lambda: Contexto())
    with pytest.raises(ErroDePdf, match="PDF indisponível.*msedge"):
        gerar_pdf(HTML, tmp_path / "r.pdf")
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_pdf.py -q`
Expected: FAIL — `ModuleNotFoundError: reports.pdf`.

- [ ] **Step 2: Implementar `reports/pdf.py`**

```python
"""PDF do relatório (F14; spec de 13/10/2026, seção 3.2).

Playwright controlando o Edge do sistema (`channel="msedge"`): sem baixar o
Chromium do Playwright (~150 MB, atrás do Norton). Roda numa thread própria
porque a API síncrona do Playwright recusa rodar dentro de um loop asyncio.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from playwright.sync_api import Error as ErroPlaywright
    from playwright.sync_api import sync_playwright
except ImportError:  # dependência opcional em tempo de execução: o HTML não precisa dela
    ErroPlaywright = Exception
    sync_playwright = None

CANAL = "msedge"
MARGENS = {"top": "18mm", "bottom": "18mm", "left": "15mm", "right": "15mm"}
RODAPE = (
    '<div style="font-size:8px;width:100%;text-align:center;color:#59636e;">'
    'página <span class="pageNumber"></span> de <span class="totalPages"></span></div>'
)


class ErroDePdf(Exception):
    """O PDF não pôde ser gerado; o HTML continua disponível."""


def _imprimir(html: str, destino: Path, timeout_s: float) -> None:
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel=CANAL)
        try:
            pagina = navegador.new_page()
            pagina.set_default_timeout(timeout_s * 1000)
            pagina.set_content(html, wait_until="load")
            pagina.pdf(
                path=str(destino), format="A4", print_background=True, margin=MARGENS,
                display_header_footer=True, header_template="<div></div>", footer_template=RODAPE,
            )
        finally:
            navegador.close()


def gerar_pdf(html: str, destino: Path, *, timeout_s: float = 60) -> Path:
    if sync_playwright is None:
        raise ErroDePdf(
            "PDF indisponível: o pacote playwright não está instalado (pip install -r requirements.txt)."
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(_imprimir, html, destino, timeout_s).result()
    except ErroPlaywright as erro:
        raise ErroDePdf(f"PDF indisponível: {erro}") from erro
    return destino
```

- [ ] **Step 3: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_pdf.py -q -rs`
Expected: 4 passed nesta máquina (Edge 155 instalado). Se os dois testes reais forem pulados, ler o motivo do skip: pulo por "is not found" aqui é falha de ambiente a investigar, não resultado.

- [ ] **Step 4: Emenda na ADR-002**

Acrescentar ao fim de `docs/adr/ADR-002-stack-tecnologica.md`:

```markdown
## Emenda de 13/10/2026 — PDF pelo Edge do sistema

O Playwright gera o PDF controlando o **Microsoft Edge já instalado** (`channel="msedge"`), em vez
do Chromium que `playwright install` baixaria. Motivos: o Norton intercepta TLS nesta máquina e o
download (~150 MB) exigiria contornar o certificado de novo; o Edge vem em todo Windows 11. O
controle do `page.pdf()` (A4, margens, fundo, rodapé "página X de Y") é o mesmo. Fora do Windows,
a geração do PDF falha com mensagem clara e o HTML continua disponível (spec
`2026-10-13-relatorio-e-cache-design.md`).
```

- [ ] **Step 5: Commit**

```bash
git add pytest.ini reports/pdf.py tests/test_relatorio_pdf.py docs/adr/ADR-002-stack-tecnologica.md
git commit -m "feat(reports): PDF pelo Edge do sistema via Playwright; emenda na ADR-002"
git push
```

---

### Task 7: CLI do relatório (`python -m reports`)

**Files:**
- Create: `reports/comando.py`, `reports/__main__.py`
- Test: `tests/test_relatorio_comando.py`

**Interfaces:**
- Consumes: `ler_resultado`, `ErroDeLeitura` (Task 4); `gerar_html` (Task 5); `gerar_pdf`, `ErroDePdf` (Task 6).
- Produces: `reports.comando.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Testes que falham**

`tests/test_relatorio_comando.py`:

```python
"""CLI do relatório: grava ao lado do JSON; falha do PDF deixa o HTML e sai com 1."""

import shutil
from pathlib import Path

from reports import comando
from reports.pdf import ErroDePdf

FIXTURE = Path(__file__).parent / "fixtures" / "resultado-formato-2026-10-11.json"


def _json(tmp_path) -> Path:
    destino = tmp_path / "P8-2026-10-11T214012.json"
    shutil.copy(FIXTURE, destino)
    return destino


def test_grava_html_ao_lado_do_json(tmp_path, capsys):
    origem = _json(tmp_path)
    assert comando.main([str(origem)]) == 0
    html = (tmp_path / "P8-2026-10-11T214012.html").read_text(encoding="utf-8")
    assert "Formato-antigo" in html and "Seção técnica" not in html
    assert "P8-2026-10-11T214012.html" in capsys.readouterr().out


def test_tecnico_leva_sufixo(tmp_path):
    assert comando.main([str(_json(tmp_path)), "--tecnico"]) == 0
    assert "Seção técnica" in (tmp_path / "P8-2026-10-11T214012-tecnico.html").read_text(encoding="utf-8")


def test_pdf_grava_ao_lado(tmp_path, monkeypatch):
    def falso(html, destino, **kwargs):
        destino.write_bytes(b"%PDF-falso")
        return destino

    monkeypatch.setattr(comando, "gerar_pdf", falso)
    assert comando.main([str(_json(tmp_path)), "--pdf"]) == 0
    assert (tmp_path / "P8-2026-10-11T214012.pdf").read_bytes().startswith(b"%PDF")


def test_falha_do_pdf_deixa_o_html_e_sai_com_1(tmp_path, monkeypatch, capsys):
    def falha(html, destino, **kwargs):
        raise ErroDePdf("PDF indisponível: Edge ausente")

    monkeypatch.setattr(comando, "gerar_pdf", falha)
    assert comando.main([str(_json(tmp_path)), "--pdf"]) == 1
    assert (tmp_path / "P8-2026-10-11T214012.html").is_file()
    assert "Edge ausente" in capsys.readouterr().err


def test_json_invalido_ou_ausente_sai_com_mensagem(tmp_path, capsys):
    """Review Focus 5."""
    quebrado = tmp_path / "x.json"
    quebrado.write_text("{ quebrado", encoding="utf-8")
    assert comando.main([str(quebrado)]) == 1
    assert comando.main([str(tmp_path / "nao-existe.json")]) == 1
    erro = capsys.readouterr().err
    assert "não é um resultado de auditoria" in erro and "nao-existe.json" in erro
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_comando.py -q`
Expected: FAIL — `ImportError: cannot import name 'comando'`.

- [ ] **Step 2: Implementar**

`reports/comando.py`:

```python
"""`python -m reports <resultado.json> [--pdf] [--tecnico]`: grava o relatório ao
lado do JSON, com o mesmo nome (sufixo `-tecnico` com a seção técnica)."""

import argparse
import sys
from pathlib import Path

from core.apresentacao import ErroDeLeitura, ler_resultado
from reports.html import gerar_html
from reports.pdf import ErroDePdf, gerar_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m reports", description="Gera o relatorio de uma auditoria.")
    parser.add_argument("resultado", help="JSON gravado por python -m core.auditoria ou pela interface")
    parser.add_argument("--pdf", action="store_true", help="gera tambem o PDF (Edge do sistema)")
    parser.add_argument("--tecnico", action="store_true", help="inclui a secao tecnica")
    args = parser.parse_args(argv)

    origem = Path(args.resultado)
    try:
        resultado = ler_resultado(origem.read_bytes())
    except OSError as erro:
        print(f"erro: nao consegui abrir {origem.name}: {erro}", file=sys.stderr)
        return 1
    except ErroDeLeitura as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    nome = origem.stem + ("-tecnico" if args.tecnico else "")
    html = gerar_html(resultado, tecnico=args.tecnico)
    destino_html = origem.with_name(f"{nome}.html")
    try:
        destino_html.write_text(html, encoding="utf-8")
    except OSError as erro:
        print(f"erro: nao consegui gravar {destino_html.name}: {erro}", file=sys.stderr)
        return 1
    print(f"HTML: {destino_html}")
    if args.pdf:
        try:
            print(f"PDF: {gerar_pdf(html, origem.with_name(f'{nome}.pdf'))}")
        except ErroDePdf as erro:
            print(f"erro: {erro}", file=sys.stderr)
            return 1
    return 0
```

`reports/__main__.py`:

```python
import sys

from reports.comando import main

sys.exit(main())
```

Nota: o console do Windows pode não imprimir acentos das mensagens de `ErroDeLeitura`; os testes leem pelo `capsys`, e o resto da CLI do projeto usa ASCII nas próprias strings, como aqui.

- [ ] **Step 3: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_relatorio_comando.py -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add reports/comando.py reports/__main__.py tests/test_relatorio_comando.py
git commit -m "feat(reports): CLI python -m reports com --pdf e --tecnico"
git push
```

---

### Task 8: Interface — cache e downloads do relatório

**Files:**
- Modify: `app/execucao.py`, `app/streamlit_app.py`
- Test: `tests/test_app_execucao.py`, `tests/test_app_interface.py`

**Interfaces:**
- Consumes: `ClienteComCache`, `PASTA_CACHE` (Task 3); `gerar_html` (Task 5); `gerar_pdf`, `ErroDePdf` (Task 6); `nome_base` (Task 2).
- Produces: `criar_llm(modelo: str, *, cache: bool = False) -> LLMClient`; `executar(..., cache: bool = False)`; `traduzir(texto, modelo, *, cache: bool = False)`; `relatorio_pdf(resultado, *, tecnico: bool) -> bytes` (levanta `ErroParaUsuario`). Chaves novas de widget: `cache` (checkbox), `rel_tecnico` (checkbox), `baixar_html`, `gerar_pdf`, `baixar_pdf`. Estado: `pdf` = `(chave, bytes)` ou `None`.

- [ ] **Step 1: Testes que falham**

`tests/test_app_execucao.py`:

```python
def test_criar_llm_com_cache_envolve(monkeypatch, tmp_path):
    from core.analise.cache import ClienteComCache

    monkeypatch.setattr(execucao, "PASTA_CACHE", tmp_path)
    sem = execucao.criar_llm("m")
    com = execucao.criar_llm("m", cache=True)
    assert not isinstance(sem, ClienteComCache)
    assert isinstance(com, ClienteComCache) and com.pasta == tmp_path and com.nome == "m"


def test_executar_repassa_o_cache(ambiente, monkeypatch):
    pedidos = []
    monkeypatch.setattr(execucao, "criar_llm", lambda modelo, cache=False: pedidos.append(cache) or LLMFalso())
    execucao.executar(_pbip(ambiente), "completo", "m", obter_base=base_padrao, cache=True)
    assert pedidos == [True]


def test_relatorio_pdf_devolve_bytes_e_erro_vira_mensagem(monkeypatch):
    from reports.pdf import ErroDePdf

    resultado = execucao.ler_resultado(FIXTURE_FORMATO_ANTIGO.read_bytes())

    def falso(html, destino, **kwargs):
        assert "Formato-antigo" in html
        destino.write_bytes(b"%PDF-ok")
        return destino

    monkeypatch.setattr(execucao, "gerar_pdf", falso)
    assert execucao.relatorio_pdf(resultado, tecnico=False) == b"%PDF-ok"

    def falha(html, destino, **kwargs):
        raise ErroDePdf("PDF indisponível: Edge ausente")

    monkeypatch.setattr(execucao, "gerar_pdf", falha)
    with pytest.raises(ErroParaUsuario, match="Edge ausente"):
        execucao.relatorio_pdf(resultado, tecnico=False)
```

Ajustar o fixture `ambiente` e o teste `test_traduz_pelo_modelo_indicado` para a assinatura nova: `lambda modelo, cache=False: ...`.

`tests/test_app_interface.py`: no fixture `app`, trocar o `criar_llm` por `lambda modelo, cache=False: LLMFalso()`; acrescentar

```python
def test_resultado_aberto_oferece_html_e_pdf(app, tmp_path, monkeypatch):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()
    assert not app.exception
    assert app.get("download_button")  # "Baixar relatório HTML"
    monkeypatch.setattr(execucao, "relatorio_pdf", lambda resultado, tecnico: b"%PDF-ok")
    app.button(key="gerar_pdf").click().run()
    assert not app.exception
    assert app.session_state["pdf"][1] == b"%PDF-ok"


def test_falha_do_pdf_vira_mensagem(app, tmp_path, monkeypatch):
    caminho = _gravar_resultado_salvo(tmp_path)
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()

    def falha(resultado, tecnico):
        raise execucao.ErroParaUsuario("PDF indisponível: Edge ausente")

    monkeypatch.setattr(execucao, "relatorio_pdf", falha)
    app.button(key="gerar_pdf").click().run()
    assert not app.exception
    assert any("Edge ausente" in e.value for e in app.error)
```

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py tests/test_app_interface.py -q`
Expected: FAIL — `criar_llm() got an unexpected keyword argument 'cache'`, `relatorio_pdf` ausente.

- [ ] **Step 2: `app/execucao.py`**

Imports: `import tempfile` já existe; acrescentar `from core.analise.cache import PASTA_CACHE, ClienteComCache`, `from reports.html import gerar_html`, `from reports.pdf import ErroDePdf, gerar_pdf`.

```python
def criar_llm(modelo: str, *, cache: bool = False) -> LLMClient:
    llm = ClienteOllama(modelo)
    return ClienteComCache(llm, PASTA_CACHE) if cache else llm
```

Em `executar`, acrescentar o parâmetro `cache: bool = False` (keyword-only, depois de `obter_base`) e trocar `llm=criar_llm(modelo)` por `llm=criar_llm(modelo, cache=cache)`.

`traduzir(texto: str, modelo: str, *, cache: bool = False)`, com `criar_llm(modelo, cache=cache)`.

Ao fim:

```python
def relatorio_pdf(resultado: ResultadoAuditoria, *, tecnico: bool) -> bytes:
    with tempfile.TemporaryDirectory(prefix="relatorio-") as pasta:
        destino = Path(pasta) / "relatorio.pdf"
        try:
            gerar_pdf(gerar_html(resultado, tecnico=tecnico), destino)
        except ErroDePdf as erro:
            raise ErroParaUsuario(str(erro)) from erro
        return destino.read_bytes()
```

- [ ] **Step 3: `app/streamlit_app.py`**

Imports: `from core.auditoria import ResultadoAuditoria, nome_base  # noqa: E402` e `from reports.html import gerar_html  # noqa: E402`.

Na barra lateral, depois do campo do modelo:

```python
    cache = lateral.checkbox(
        "reusar respostas guardadas do LLM (cache)", value=False,
        disabled=bloqueado or modo == "so_regras", key="cache",
    )
```

e no pedido: `estado.pedido = {"entrada": entrada, "modo": modo, "modelo": modelo, "cache": cache}`; em `_executar`, `execucao.executar(..., obter_base=_base, cache=pedido.get("cache", False))`.

Em `_citacoes`, `execucao.traduzir(trecho.texto, modelo, cache=bool(estado.get("cache")))`.

Nova função, chamada em `_resultado` logo depois de `_cabecalho(resultado)`:

```python
def _relatorio(resultado: ResultadoAuditoria, bloqueado: bool) -> None:
    with st.container(border=True):
        st.markdown("**Relatório**")
        tecnico = st.checkbox("incluir seção técnica", key="rel_tecnico", disabled=bloqueado)
        nome = nome_base(resultado) + ("-tecnico" if tecnico else "")
        c1, c2 = st.columns(2)
        c1.download_button(
            "Baixar relatório HTML", gerar_html(resultado, tecnico=tecnico), file_name=f"{nome}.html",
            mime="text/html", key="baixar_html", disabled=bloqueado,
        )
        chave = (resultado.gerado_em, tecnico)
        if estado.pdf is not None and estado.pdf[0] == chave:
            c2.download_button(
                "Baixar relatório PDF", estado.pdf[1], file_name=f"{nome}.pdf",
                mime="application/pdf", key="baixar_pdf", disabled=bloqueado,
            )
        elif c2.button("Gerar PDF", key="gerar_pdf", disabled=bloqueado):
            with st.spinner("Gerando o PDF pelo Edge..."):
                try:
                    estado.pdf = (chave, execucao.relatorio_pdf(resultado, tecnico=tecnico))
                except execucao.ErroParaUsuario as erro:
                    c2.error(str(erro))
                else:
                    st.rerun()
```

Em `_resumo`, depois da linha das categorias:

```python
    if resumo.do_cache:
        st.caption(f"{resumo.do_cache} explicação(ões) vieram do cache de respostas do LLM, não de uma chamada nova.")
```

Em `_executar`, no ramo de sucesso, acrescentar `estado.pdf = None`.

- [ ] **Step 4: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py tests/test_app_interface.py -q`
Expected: PASS. Se o `AppTest` desta versão não expuser `download_button` via `app.get("download_button")`, conferir o tipo em `streamlit.testing.v1.element_tree` e ajustar só o teste.

- [ ] **Step 5: Commit**

```bash
git add app/execucao.py app/streamlit_app.py tests/test_app_execucao.py tests/test_app_interface.py
git commit -m "feat(app): cache opcional e downloads do relatorio HTML e PDF"
git push
```

---

### Task 9: Acabamento da interface (menores adiados)

**Files:**
- Modify: `app/execucao.py`, `app/streamlit_app.py`
- Test: `tests/test_app_execucao.py`, `tests/test_app_interface.py`

(Já resolvidos antes: carimbo com segundos — Task 2; BOM e arquivo que some — Task 4.)

**Interfaces:**
- Produces: `executar_envio(nome: str, conteudo: bytes, modo, modelo, **kwargs) -> Execucao` (grava o `.zip`, executa, apaga a pasta `envio-*`; falha ao gravar vira `ErroParaUsuario`). Pedido da interface passa a carregar `"envio": (nome, bytes)` no lugar de gravar na barra lateral.

- [ ] **Step 1: Testes que falham**

`tests/test_app_execucao.py`:

```python
def test_envio_executa_e_apaga_a_pasta_temporaria(ambiente, monkeypatch):
    import io
    import zipfile

    pbip = _pbip(ambiente / "origem")
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as arquivo:
        for caminho in pbip.rglob("*"):
            arquivo.write(caminho, caminho.relative_to(pbip.parent))
    gravados = []
    original = execucao.salvar_envio
    monkeypatch.setattr(execucao, "salvar_envio", lambda nome, conteudo: gravados.append(original(nome, conteudo)) or gravados[-1])
    feito = execucao.executar_envio("Minimal.zip", memoria.getvalue(), "so_regras", "m")
    assert feito.resultado.projeto == "Minimal"
    assert not gravados[0].parent.exists()


def test_envio_que_nao_grava_vira_mensagem(monkeypatch):
    def cheio(*args, **kwargs):
        raise OSError("disco cheio")

    monkeypatch.setattr(execucao.tempfile, "mkdtemp", cheio)
    with pytest.raises(ErroParaUsuario, match="disco cheio"):
        execucao.executar_envio("P.zip", b"PK", "so_regras", "m")


def test_erro_de_validacao_do_pipeline_e_erro_inesperado(ambiente, monkeypatch):
    from core.auditoria import ResultadoAuditoria

    def quebra(*args, **kwargs):
        ResultadoAuditoria.model_validate({})

    monkeypatch.setattr(auditoria, "run_audit", quebra)
    with pytest.raises(ErroParaUsuario, match="Erro inesperado"):
        execucao.executar(_pbip(ambiente), "so_regras", "m")
```

`tests/test_app_interface.py`:

```python
def _gravar_resultado(raiz, objetos) -> Path:
    registro = Registro()
    registro.registrar(meta(), lambda modelo: [achado(objeto=o) for o in objetos])
    pbip = escrever_pbip(raiz / "origem", model_bim=modelo_tmsl([tabela("T")]))
    resultado = auditoria.run_audit(
        pbip, llm=LLMFalso(), base=base_padrao(), registro=registro, gabaritos={"MOD-001": gabarito()},
    )
    return auditoria.gravar(resultado)


def _abrir_salvo(app, caminho):
    app.run()
    app.selectbox(key="salvo").set_value(str(caminho)).run()
    app.button(key="abrir").click().run()


def test_traducao_usa_o_modelo_do_resultado(app, tmp_path, monkeypatch):
    usados = []
    monkeypatch.setattr(execucao, "traduzir", lambda texto, modelo, cache=False: usados.append(modelo) or "ok")
    _abrir_salvo(app, _gravar_resultado_salvo(tmp_path))
    app.text_input(key="modelo").input("outro-modelo").run()
    next(b for b in app.button if (b.key or "").startswith("traduzir")).click().run()
    assert usados == ["llm-falso"]


def test_objeto_com_markdown_aparece_escapado(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado(tmp_path, ["Tabela_*a*"]))
    assert any("Tabela\\_\\*a\\*" in c.value for c in app.caption)


def test_resultado_sem_achados_diz_nenhum_achado(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado(tmp_path, []))
    assert any(i.value == "Nenhum achado." for i in app.info)


def test_filtros_com_placeholder_em_portugues(app, tmp_path):
    _abrir_salvo(app, _gravar_resultado_salvo(tmp_path))
    assert app.multiselect and all(m.placeholder == "todas" for m in app.multiselect)
```

(O fixture `_gravar_resultado(raiz, objetos)` gera um achado por objeto, independentemente das tabelas do modelo.)

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py tests/test_app_interface.py -q`
Expected: FAIL nos novos.

- [ ] **Step 2: `app/execucao.py`**

Imports: `import shutil`; `from pydantic import ValidationError`.

Em `executar`, antes do `except ErroEstruturaPbip`:

```python
    except ValidationError as erro:
        # É `ValueError`, mas aqui é bug do pipeline, não projeto ilegível.
        raise ErroParaUsuario(f"Erro inesperado na auditoria: {type(erro).__name__}: {erro}") from erro
```

Ao fim:

```python
def executar_envio(nome: str, conteudo: bytes, modo: ModoAuditoria, modelo: str, **kwargs) -> Execucao:
    """O `.zip` enviado vive só durante a auditoria: a pasta `envio-*` é apagada ao fim."""
    try:
        caminho = salvar_envio(nome, conteudo)
    except OSError as erro:
        raise ErroParaUsuario(f"Não consegui guardar o arquivo enviado: {erro}") from erro
    try:
        return executar(caminho, modo, modelo, **kwargs)
    finally:
        shutil.rmtree(caminho.parent, ignore_errors=True)
```

- [ ] **Step 3: `app/streamlit_app.py`**

No botão "Auditar", trocar a gravação do envio:

```python
        if enviado is not None:
            estado.pedido = {"envio": (enviado.name, enviado.getvalue()), "modo": modo, "modelo": modelo, "cache": cache}
        else:
            estado.pedido = {"entrada": Path(pasta.strip()), "modo": modo, "modelo": modelo, "cache": cache}
```

Em `_executar`, trocar a chamada:

```python
                comum = dict(ao_progredir=ao_progredir, obter_base=_base, cache=pedido.get("cache", False))
                if "envio" in pedido:
                    nome, conteudo = pedido["envio"]
                    feito = execucao.executar_envio(nome, conteudo, pedido["modo"], pedido["modelo"], **comum)
                else:
                    feito = execucao.executar(pedido["entrada"], pedido["modo"], pedido["modelo"], **comum)
```

Em `_citacoes`: `modelo = resultado.modelo_llm or estado.get("modelo") or MODELO_PADRAO`.

Escape de markdown: em `_detalhe`, o caption passa a usar `_md(evidencia.objeto)`; em `_examinado`, `st.error(f"Regra com falha — {_md(falha)}")`; em `_link`, `texto = f"[{_md(rotulo)}]({url})"`.

Zero achados: `_tabela(visiveis, bloqueado, total: int)` e, no início, `if total == 0: st.info("Nenhum achado."); return None`; a chamada em `_resultado` passa `len(linhas)`.

Placeholders: em `_filtros`, acrescentar `placeholder="todas"` aos quatro `multiselect` (o `checkbox` não tem placeholder e fica como está).

- [ ] **Step 4: Rodar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_app_execucao.py tests/test_app_interface.py -q`
Expected: PASS. Se `Multiselect` do `AppTest` não tiver `placeholder`, ler `m.proto.placeholder` e ajustar só o teste.

- [ ] **Step 5: Suíte inteira** — `.\.venv\Scripts\python.exe -m pytest -q` → tudo passa.

- [ ] **Step 6: Commit**

```bash
git add app/execucao.py app/streamlit_app.py tests/test_app_execucao.py tests/test_app_interface.py
git commit -m "fix(app): acabamento da interface - envio temporario, erros, traducao, escape, zero achados, placeholders"
git push
```

---

### Task 10: Aceite manual e registro

**Files:**
- Modify: `docs/project/progress-log.md`, `docs/project/status.md`, `docs/project/riscos.md` (R-07, se o PDF mudar o corte), `README.md`

- [ ] **Step 1: Relatórios pela CLI**

```powershell
.\.venv\Scripts\python.exe -m reports "outputs\P8_contoso-vendas-2026-10-13T1945.json" --pdf
.\.venv\Scripts\python.exe -m reports "outputs\P8_contoso-vendas-2026-10-13T1945.json" --pdf --tecnico
.\.venv\Scripts\python.exe -m reports "outputs\P5_Store Sales-2026-10-13T1941-so-regras.json" --pdf
```

Expected: três `.html` e três `.pdf`, código 0. Abrir os PDFs e os HTMLs e conferir: cabeçalho, painel, 15 achados do P8 com avisos e citações, links "ler em português", rodapé "página X de Y", seção técnica só no `-tecnico`, P5 com selo só regras e 18 achados. Anotar páginas e tamanho dos PDFs.

- [ ] **Step 2: Cache ao vivo**

```powershell
.\.venv\Scripts\python.exe -m core.auditoria data\pbip\P8_contoso-vendas --cache
.\.venv\Scripts\python.exe -m core.auditoria data\pbip\P8_contoso-vendas --cache
```

Expected: a primeira como hoje (~2–2,5 min); a segunda em segundos, com "Do cache: 15". Conferir que os textos das duas são idênticos (comparar `geracao` nos dois JSONs).

- [ ] **Step 3: Interface**

`streamlit run app/streamlit_app.py`: abrir o P8, baixar o HTML, gerar e baixar o PDF (com e sem seção técnica), auditar o P8 com o cache ligado e ver a legenda do cache.

- [ ] **Step 4: Registrar**

- `progress-log.md`: entrada com os números dos Steps 1–3 e "**Próximo passo:** revisão final e merge da `fase4-relatorio`; depois a Fase 5 (avaliação, documentação e banca)".
- `status.md`: F4 **Concluída** (interface + relatório + cache); entregáveis "Relatório HTML/PDF (`python -m reports`)" e "Cache das respostas do LLM (`--cache`)" na seção 3; contagem de testes.
- `README.md`: seção "Relatório" com os comandos.

- [ ] **Step 5: Commit**

```bash
git add docs/project README.md
git commit -m "docs: relatorio HTML/PDF e cache aceitos no P8 e no P5"
git push
```
