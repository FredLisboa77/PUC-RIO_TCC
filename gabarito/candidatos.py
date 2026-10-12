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
