"""Modelo interno normalizado.

O `model.bim` é TMSL puro: verboso, com propriedades que variam conforme o
`compatibilityLevel` e com DAX e M gravados ora como string, ora como lista de
linhas. As regras não deveriam lidar com isso. Estas classes são o contrato
estável entre o parser e o resto do pipeline.

Os nomes seguem o vocabulário do projeto (português), e cada classe guarda em
`bruto` o dicionário TMSL de origem, para que uma regra possa consultar uma
propriedade que ainda não foi normalizada sem precisar reabrir o arquivo.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

DirecaoFiltro = Literal["um_sentido", "ambos_sentidos"]


class Coluna(BaseModel):
    nome: str
    tipo_dado: str | None = None
    tipo: str | None = None
    """`type` do TMSL: `calculated` numa coluna calculada em DAX,
    `calculatedTableColumn` numa coluna de tabela calculada, ausente numa coluna
    vinda da origem. Não confundir com `tipo_dado`, que é o `dataType`."""
    resumir_por: str | None = None
    """`summarizeBy`: a agregação implícita que o Power BI oferece ao autor do
    relatório. `none` significa que a coluna não é somável por padrão."""
    expressao: str | None = None
    """DAX da coluna calculada; `None` numa coluna comum."""
    oculta: bool = False
    ordenar_por: str | None = None
    """`sortByColumn`: a coluna que define a ordem desta. Conta como uso da
    coluna apontada — esquecer isso faria a PERF-005 recomendar apagar a coluna
    de ordenação, quebrando a ordem no relatório."""
    bruto: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def e_calculada(self) -> bool:
        return self.expressao is not None


class Medida(BaseModel):
    nome: str
    expressao: str = ""
    tabela: str = ""
    pasta: str | None = None
    formato: str | None = None
    oculta: bool = False
    bruto: dict[str, Any] = Field(default_factory=dict, repr=False)


class Particao(BaseModel):
    nome: str
    modo: str | None = None
    """`import`, `directQuery`, `dual`… conforme o TMSL."""
    tipo_origem: str | None = None
    """`source.type`: `m` numa partição de Power Query, `calculated` numa
    tabela calculada em DAX."""
    origem: str | None = None
    """Expressão da partição: M quando `tipo_origem == "m"`, DAX quando
    `tipo_origem == "calculated"`. O campo carrega as duas, e quem lê precisa
    olhar `tipo_origem` antes — uma regra de DAX que varresse toda partição
    leria as 10 expressões M do P8."""
    bruto: dict[str, Any] = Field(default_factory=dict, repr=False)


class Nivel(BaseModel):
    """Um nível de hierarquia. Referencia uma coluna da própria tabela."""

    nome: str
    tabela: str
    coluna: str
    ordem: int | None = None


class Hierarquia(BaseModel):
    nome: str
    tabela: str
    niveis: list[Nivel] = Field(default_factory=list)


class PermissaoDeTabela(BaseModel):
    tabela: str
    expressao_filtro: str | None = None
    """DAX da RLS. Referencia colunas, e por isso conta como uso de coluna."""


class Role(BaseModel):
    """Role de segurança em nível de linha."""

    nome: str
    permissoes: list[PermissaoDeTabela] = Field(default_factory=list)


class Tabela(BaseModel):
    nome: str
    oculta: bool = False
    data_category: str | None = None
    """`dataCategory`: vale `Time` numa tabela marcada como tabela de data."""
    colunas: list[Coluna] = Field(default_factory=list)
    medidas: list[Medida] = Field(default_factory=list)
    particoes: list[Particao] = Field(default_factory=list)
    hierarquias: list[Hierarquia] = Field(default_factory=list)
    bruto: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def colunas_calculadas(self) -> list[Coluna]:
        return [c for c in self.colunas if c.e_calculada]


class Relacionamento(BaseModel):
    nome: str
    tabela_origem: str
    coluna_origem: str
    tabela_destino: str
    coluna_destino: str
    direcao_filtro: DirecaoFiltro = "um_sentido"
    ativo: bool = True
    cardinalidade_origem: str = "muitos"
    cardinalidade_destino: str = "um"
    bruto: dict[str, Any] = Field(default_factory=dict, repr=False)


class ModeloSemantico(BaseModel):
    nome: str = ""
    compatibility_level: int | None = None
    cultura: str | None = None
    tabelas: list[Tabela] = Field(default_factory=list)
    relacionamentos: list[Relacionamento] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)

    @property
    def medidas(self) -> list[Medida]:
        """Todas as medidas do modelo, em qualquer tabela."""
        return [m for t in self.tabelas for m in t.medidas]
