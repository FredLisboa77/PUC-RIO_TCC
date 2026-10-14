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

from app import execucao  # noqa: E402
from core import apresentacao as consulta  # noqa: E402
from core.analise.base import AchadoEnriquecido  # noqa: E402
from core.analise.llm import MODELO_PADRAO  # noqa: E402
from core.apresentacao import Filtro  # noqa: E402
from core.auditoria import ResultadoAuditoria, nome_base  # noqa: E402
from core.rules.todas import REGISTRO  # noqa: E402
from rag.catalogo import url_em_portugues  # noqa: E402
from reports.html import gerar_html  # noqa: E402

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
estado.setdefault("pdf", None)


def _md(texto: str) -> str:
    """Nomes de objeto como `DateTableTemplate_0eab_...` não podem virar itálico."""
    return "".join(f"\\{c}" if c in ESPECIAIS_MARKDOWN else c for c in texto)


@st.cache_resource(show_spinner="Carregando a base da RAG...")
def _base():
    return execucao.carregar_base()


def _abrir(ler) -> None:
    try:
        estado.resultado = ler()
    except execucao.ErroParaUsuario as erro:
        estado.mensagem = ("error", str(erro))  # o resultado anterior continua
    else:
        estado.traducoes = {}
        estado.pdf = None
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
    cache = lateral.checkbox(
        "reusar respostas guardadas do LLM (cache)", value=False,
        disabled=bloqueado or modo == "so_regras", key="cache",
    )
    if lateral.button("Auditar", type="primary", disabled=bloqueado or not (enviado or pasta.strip()), key="auditar"):
        if enviado is not None:
            # O .zip só é gravado durante a execução, e apagado ao fim (`executar_envio`).
            estado.pedido = {"envio": (enviado.name, enviado.getvalue()), "modo": modo, "modelo": modelo, "cache": cache}
        else:
            estado.pedido = {"entrada": Path(pasta.strip()), "modo": modo, "modelo": modelo, "cache": cache}
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
        _abrir(lambda: execucao.ler_salvo(Path(escolhido)))
    externo = lateral.file_uploader("ou envie um JSON", type=["json"], disabled=bloqueado, key="json_externo")
    if lateral.button("Abrir JSON enviado", disabled=bloqueado or externo is None, key="abrir_externo"):
        _abrir(lambda: execucao.ler_resultado(externo.getvalue()))


# --- execução ----------------------------------------------------------------

def _executar(pedido: dict, topo) -> None:
    try:
        with topo, st.status("Auditando...", expanded=True) as status:
            st.write("Lendo o projeto e rodando as regras.")
            barra = st.progress(0.0)

            def ao_progredir(feito, total, achado):
                etapa = "explicações" if pedido["modo"] == "completo" else "achados"
                barra.progress(
                    feito / total,
                    text=f"{etapa}: achado {feito} de {total} — {achado.id_regra} {achado.evidencia.objeto}",
                )

            try:
                comum = dict(ao_progredir=ao_progredir, obter_base=_base, cache=pedido.get("cache", False))
                if "envio" in pedido:
                    nome, conteudo = pedido["envio"]
                    feito = execucao.executar_envio(nome, conteudo, pedido["modo"], pedido["modelo"], **comum)
                else:
                    feito = execucao.executar(pedido["entrada"], pedido["modo"], pedido["modelo"], **comum)
            except execucao.ErroParaUsuario as erro:
                estado.mensagem = ("error", str(erro))
                status.update(label="A auditoria não terminou", state="error")
            else:
                estado.resultado = feito.resultado
                estado.traducoes = {}
                estado.pdf = None
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


def _examinado(resultado: ResultadoAuditoria) -> None:
    examinado = consulta.examinado(resultado)
    with st.container(border=True):
        st.subheader("O que foi examinado")
        st.markdown(f"- {examinado.regras}\n- {examinado.expressoes}")
        for falha in examinado.falhas:
            st.error(f"Regra com falha — {_md(falha)}")
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
    if resumo.do_cache:
        st.caption(f"{resumo.do_cache} explicação(ões) vieram do cache de respostas do LLM, não de uma chamada nova.")


def _filtros(linhas: list[consulta.Linha], bloqueado: bool) -> Filtro:
    opcoes = consulta.opcoes_de_filtro(linhas)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
    comum = dict(disabled=bloqueado)
    return Filtro(
        severidades=frozenset(c1.multiselect("Severidade", opcoes["severidades"], key="f_severidade", placeholder="todas", **comum)),
        categorias=frozenset(c2.multiselect("Categoria", opcoes["categorias"], key="f_categoria", placeholder="todas", **comum)),
        regras=frozenset(c3.multiselect("Regra", opcoes["regras"], key="f_regra", placeholder="todas", **comum)),
        tabelas=frozenset(c4.multiselect("Tabela", opcoes["tabelas"], key="f_tabela", placeholder="todas", **comum)),
        so_com_aviso=c5.checkbox("Só com aviso", key="f_aviso", **comum),
    )


def _tabela(visiveis: list[consulta.Linha], bloqueado: bool, total: int) -> consulta.Linha | None:
    if total == 0:
        st.info("Nenhum achado.")
        return None
    if not visiveis:
        st.info("Nenhum achado com estes filtros.")
        return None
    dados = [
        {"Severidade": ROTULOS_SEVERIDADE[l.severidade], "Regra": l.regra, "Título": l.titulo,
         "Objeto": l.objeto, "Tabela": l.tabela, "Aviso": "⚠" if l.aviso else ""}
        for l in visiveis
    ]
    evento = st.dataframe(
        dados, on_select="ignore" if bloqueado else "rerun", selection_mode="single-row", hide_index=True, width="stretch", key="tabela"
    )
    try:
        selecionadas = list(evento.selection.rows)
    except AttributeError:
        selecionadas = []
    return consulta.escolher(visiveis, selecionadas)


def _link(rotulo: str, url: str) -> str:
    portugues = url_em_portugues(url)
    texto = f"[{_md(rotulo)}]({url})"
    return f"{texto} · [ler em português]({portugues})" if portugues else texto


def _citacoes(item: AchadoEnriquecido, indice: int, resultado: ResultadoAuditoria, bloqueado: bool) -> None:
    if item.geracao is None:
        return
    st.markdown("**Fontes citadas**")
    por_numero = {t.numero: t for t in item.contexto}
    modelo = resultado.modelo_llm or estado.get("modelo") or MODELO_PADRAO
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
            elif traducao.button("Traduzir trecho", key=f"traduzir|{chave}", disabled=bloqueado):
                with st.spinner("Traduzindo..."):
                    try:
                        estado.traducoes[chave] = execucao.traduzir(trecho.texto, modelo, cache=bool(estado.get("cache")))
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
            + ("\n- Origem: resposta guardada no cache (o tempo é de leitura, não de geração)" if item.do_cache else "")
        )
        for trecho in item.contexto:
            origem = "âncora da regra" if trecho.origem == "ancora" else "busca"
            st.markdown(f"**[{trecho.numero}] {_md(trecho.titulo)} — {_md(trecho.caminho)}** ({origem})")
            st.markdown(_md(trecho.texto))


def _detalhe(resultado: ResultadoAuditoria, linha: consulta.Linha, bloqueado: bool) -> None:
    item = resultado.achados[linha.indice]
    meta = REGISTRO.meta(item.achado.id_regra)
    evidencia = item.achado.evidencia
    st.divider()
    st.subheader(f"{meta.id} — {meta.titulo}")
    st.caption(f"{ROTULOS_SEVERIDADE[meta.severidade]} · {meta.categoria} · {evidencia.tipo_objeto} {_md(evidencia.objeto)}")
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
    if item.do_cache:
        st.caption("Resposta guardada no cache de respostas do LLM, não gerada nesta auditoria.")
    st.markdown("**Recomendação**")
    st.markdown(_md(item.recomendacao_final(meta)))
    _citacoes(item, linha.indice, resultado, bloqueado)
    st.markdown("Fonte da regra: " + _link(meta.titulo, meta.url_canonica))
    _detalhes_tecnicos(item)


def _resultado(resultado: ResultadoAuditoria, bloqueado: bool = False) -> None:
    """`bloqueado` durante a auditoria: o resultado anterior continua na tela, mas
    um clique nele reexecutaria o script e mataria a auditoria em andamento."""
    _cabecalho(resultado)
    _relatorio(resultado, bloqueado)
    _examinado(resultado)
    linhas = consulta.linhas(resultado, REGISTRO)
    _resumo(linhas)
    visiveis = consulta.filtrar(linhas, _filtros(linhas, bloqueado))
    linha = _tabela(visiveis, bloqueado, len(linhas))
    if linha is not None:
        _detalhe(resultado, linha, bloqueado)


# --- página ------------------------------------------------------------------

_barra_lateral()
if estado.mensagem:
    tipo, texto = estado.mensagem
    getattr(st, tipo)(texto)
if estado.executando and estado.pedido is not None:
    # O status vai para o topo; o resultado anterior é redesenhado desabilitado logo
    # abaixo, para não sobrar na tela um elemento antigo ainda clicável.
    topo = st.container()
    if estado.resultado is not None:
        _resultado(estado.resultado, bloqueado=True)
    _executar(estado.pedido, topo)
elif estado.resultado is not None:
    _resultado(estado.resultado)
else:
    st.title("Auditor de projetos Power BI (PBIP)")
    st.markdown("Envie um projeto na barra lateral, ou abra um resultado salvo.")
