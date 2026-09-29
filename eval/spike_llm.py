"""Spike de LLM da semana 2 — decide entre modelo local e API paga (R-02, ADR-002).

Mede, para cada modelo candidato e sobre 5 achados representativos:

- tempo por achado (critério de reprovação: > 60 s)
- se a explicação cita uma das fontes fornecidas (critério: < 4 de 5 reprova)
- VRAM e RAM ocupadas durante a execução

O prompt reproduz a condição real do pipeline (ADR-003): a regra já decidiu que
existe o achado; o LLM apenas redige explicação e recomendação a partir dos
trechos recuperados, e é obrigado a citar a fonte. Nada aqui inventa achados.

Uso:
    python eval/spike_llm.py qwen2.5:3b qwen2.5:7b-instruct-q4_K_M
"""

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434"
NUM_CTX = 4096
LIMITE_SEGUNDOS = 60.0
MINIMO_CITACOES = 4

# Cinco achados representativos das quatro categorias de regra. Os dois
# primeiros são reais, extraídos do P8 pelo parser da Fase 2.
ACHADOS = [
    {
        "id": "MOD001",
        "categoria": "MODELAGEM",
        "objeto": "Modelo",
        "evidencia": (
            "O modelo tem 4 tabelas de data geradas automaticamente "
            "(1 DateTableTemplate_* e 3 LocalDateTable_*), embora já exista "
            "uma tabela de calendário própria chamada DimCalendar. Uma das "
            "tabelas automáticas foi gerada sobre a coluna de data da própria "
            "DimCalendar."
        ),
        "trechos": [
            {
                "fonte": "Microsoft Learn — Auto date/time guidance in Power BI Desktop",
                "url": "https://learn.microsoft.com/en-us/power-bi/guidance/auto-date-time",
                "texto": (
                    "The auto date/time option creates a hidden auto date/time table "
                    "for each date column. These tables increase the model size and "
                    "are not needed when the model already includes a date table. "
                    "Consider disabling the option and using your own date table."
                ),
            },
            {
                "fonte": "Microsoft Learn — Model date tables",
                "url": "https://learn.microsoft.com/en-us/power-bi/guidance/model-date-tables",
                "texto": (
                    "A model date table lets you filter and group by date periods "
                    "consistently. Mark it as a date table so time intelligence "
                    "functions work correctly."
                ),
            },
        ],
    },
    {
        "id": "MOD002",
        "categoria": "MODELAGEM",
        "objeto": "Relacionamentos",
        "evidencia": (
            "4 dos 11 relacionamentos do modelo usam filtro cruzado "
            "bidirectional (crossFilteringBehavior = bothDirections)."
        ),
        "trechos": [
            {
                "fonte": "Microsoft Learn — Bi-directional relationship guidance",
                "url": "https://learn.microsoft.com/en-us/power-bi/guidance/relationships-bidirectional-filtering",
                "texto": (
                    "Bi-directional relationships can degrade query performance and "
                    "may produce ambiguous filter propagation paths. Use them only "
                    "when there is a specific requirement, and prefer the DAX "
                    "CROSSFILTER function to enable the behavior for a single measure."
                ),
            },
        ],
    },
    {
        "id": "DAX001",
        "categoria": "DAX",
        "objeto": "Medida 'Margem %'",
        "evidencia": "A medida usa o operador / em vez da função DIVIDE: [Lucro] / [Receita]",
        "trechos": [
            {
                "fonte": "Microsoft Learn — DAX: DIVIDE function vs divide operator",
                "url": "https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator",
                "texto": (
                    "The DIVIDE function handles division by zero without raising an "
                    "error, returning BLANK or an alternate result you provide. The "
                    "divide operator returns an error for division by zero."
                ),
            },
        ],
    },
    {
        "id": "PERF001",
        "categoria": "PERFORMANCE",
        "objeto": "Tabela 'FactOnlineSales'",
        "evidencia": (
            "A tabela de fatos tem 35 colunas calculadas em DAX, entre elas "
            "colunas que poderiam ser calculadas na origem dos dados."
        ),
        "trechos": [
            {
                "fonte": "Microsoft Learn — Data reduction techniques for Import modeling",
                "url": "https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction",
                "texto": (
                    "Calculated columns are computed and stored in the model, "
                    "increasing its size, and they do not compress as well as columns "
                    "loaded from the source. Where possible, push the calculation to "
                    "the data source or to Power Query."
                ),
            },
        ],
    },
    {
        "id": "M001",
        "categoria": "M",
        "objeto": "Partição 'FactOnlineSales-part'",
        "evidencia": (
            "A consulta M aplica Table.SelectRows depois de Table.Sort sobre a "
            "tabela inteira, o que impede o query folding."
        ),
        "trechos": [
            {
                "fonte": "Microsoft Learn — Power Query query folding",
                "url": "https://learn.microsoft.com/en-us/power-query/power-query-folding",
                "texto": (
                    "Query folding pushes transformations to the data source. Some "
                    "transformations prevent folding, which forces Power Query to "
                    "process data locally and can slow refresh substantially."
                ),
            },
        ],
    },
]

PROMPT = """Você é um auditor de modelos Power BI. Uma regra determinística JÁ identificou o problema abaixo. Sua tarefa NÃO é decidir se o problema existe, e sim explicá-lo e recomendar a correção.

ACHADO
Categoria: {categoria}
Objeto: {objeto}
Evidência: {evidencia}

TRECHOS DE DOCUMENTAÇÃO RECUPERADOS
{trechos}

Responda em português do Brasil, em no máximo 120 palavras, com exatamente estas três partes:
EXPLICACAO: por que isso é um problema.
RECOMENDACAO: o que fazer, de forma acionável.
FONTE: a URL exata de um dos trechos acima. Use apenas uma URL, copiada literalmente.

Não use nenhuma informação que não esteja nos trechos acima."""


def montar_prompt(achado: dict) -> str:
    trechos = "\n\n".join(
        f"[{i + 1}] {t['fonte']}\nURL: {t['url']}\n{t['texto']}"
        for i, t in enumerate(achado["trechos"])
    )
    return PROMPT.format(
        categoria=achado["categoria"],
        objeto=achado["objeto"],
        evidencia=achado["evidencia"],
        trechos=trechos,
    )


def gerar(modelo: str, prompt: str) -> tuple[str, float]:
    corpo = json.dumps(
        {
            "model": modelo,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": NUM_CTX, "temperature": 0.2},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA}/api/generate", data=corpo, headers={"Content-Type": "application/json"}
    )
    inicio = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        dados = json.loads(resp.read())
    return dados.get("response", ""), time.perf_counter() - inicio


def vram_mib() -> int | None:
    try:
        saida = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=15,
        )
        return int(saida.stdout.strip().splitlines()[0])
    except Exception:
        return None


def citacao_valida(resposta: str, achado: dict) -> bool:
    """A URL citada precisa ser uma das fornecidas — é a regra da ADR-003."""
    return any(t["url"] in resposta for t in achado["trechos"])


def rodar(modelo: str) -> dict:
    print(f"\n{'=' * 70}\nMODELO: {modelo}\n{'=' * 70}")

    # Aquecimento, fora da medição. A primeira chamada carrega o modelo do disco
    # para a VRAM e chega a levar dezenas de segundos — custo que se paga uma vez
    # por sessão, não por achado. Medi-lo junto com a inferência reprovaria um
    # modelo por um motivo que o critério da ADR-002 não descreve.
    _, carga = gerar(modelo, "Responda apenas: ok")
    print(f"  (carga do modelo: {carga:.1f}s, fora da medicao)")

    linhas, tempos, validas = [], [], 0

    for achado in ACHADOS:
        resposta, segundos = gerar(modelo, montar_prompt(achado))
        ok = citacao_valida(resposta, achado)
        validas += ok
        tempos.append(segundos)
        linhas.append(
            {
                "achado": achado["id"],
                "categoria": achado["categoria"],
                "segundos": round(segundos, 1),
                "citacao_valida": ok,
                "palavras": len(resposta.split()),
                "resposta": resposta.strip(),
            }
        )
        print(f"  {achado['id']:<8} {segundos:6.1f}s  citacao {'OK ' if ok else 'INVALIDA'}  "
              f"vram {vram_mib()} MiB")

    pior = max(tempos)
    aprovado = pior <= LIMITE_SEGUNDOS and validas >= MINIMO_CITACOES
    print(f"\n  tempo medio {sum(tempos) / len(tempos):.1f}s | pior {pior:.1f}s "
          f"| citacoes validas {validas}/{len(ACHADOS)}")
    print(f"  VEREDITO: {'APROVADO' if aprovado else 'REPROVADO'} "
          f"(criterios: pior <= {LIMITE_SEGUNDOS:.0f}s e citacoes >= {MINIMO_CITACOES})")

    return {
        "modelo": modelo,
        "tempo_carga_s": round(carga, 1),
        "tempo_medio_s": round(sum(tempos) / len(tempos), 1),
        "tempo_pior_s": round(pior, 1),
        "citacoes_validas": validas,
        "total_achados": len(ACHADOS),
        "aprovado": aprovado,
        "vram_mib_final": vram_mib(),
        "execucoes": linhas,
    }


def main(modelos: list[str]) -> int:
    resultados = []
    for modelo in modelos:
        try:
            resultados.append(rodar(modelo))
        except urllib.error.URLError as erro:
            print(f"  FALHOU ao chamar o Ollama para {modelo}: {erro}")

    destino = Path("eval/results/spike_llm.json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nResultado completo em {destino}")

    if any(r["aprovado"] for r in resultados):
        print("Pelo menos um modelo local aprovou: a ADR-006 nao precisa ser aberta.")
        return 0
    print("Nenhum modelo local aprovou: abrir a ADR-006 e migrar para API paga.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or ["qwen2.5:3b"]))
