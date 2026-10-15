#import "../abnt.typ": fonte

= Avaliação <cap-avaliacao>

A avaliação responde a três perguntas, uma para cada camada da ferramenta. As regras apontam os problemas certos? A recuperação encontra a passagem da documentação que sustenta cada achado? A explicação gerada pode ser entregue ao dono do modelo sem edição? Este capítulo apresenta o desenho da avaliação, os resultados de cada pergunta e o estudo de caso do projeto P8. Todas as tabelas de resultado foram geradas pelo código a partir dos arquivos de resultado versionados no repositório, que o leitor pode conferir.

== Desenho da avaliação <sec-desenho>

Cada pergunta tem a sua medida, o seu gabarito e uma regra de decisão escrita antes da medição. Fixar a regra antes de medir impede que a escolha se ajuste ao resultado: quando o resultado contrariou a expectativa, a regra foi mantida e a divergência, declarada. Esta seção define as medidas usadas no restante do capítulo.

=== Achado, gabarito e os quatro desfechos

Um *achado* é a afirmação da ferramenta de que um objeto do modelo — uma tabela, uma coluna, um relacionamento ou uma expressão DAX — viola uma regra. O *gabarito* é o julgamento humano, feito de forma independente, sobre cada objeto que poderia violar aquela regra, quer a ferramenta o tenha marcado, quer não. Cruzar os dois produz quatro desfechos possíveis para cada objeto:

- *verdadeiro positivo* (VP): a ferramenta marcou o objeto e o gabarito confirma a violação;
- *falso positivo* (FP): a ferramenta marcou o objeto, mas o gabarito diz que ele não viola a regra;
- *falso negativo* (FN): a ferramenta não marcou o objeto, mas o gabarito diz que ele viola a regra;
- *verdadeiro negativo* (VN): a ferramenta não marcou e o gabarito confirma que não há violação.

Um exemplo do próprio conjunto de avaliação ajuda a fixar os termos. No projeto P6, a tabela `Logo` não tem nenhum relacionamento, e a MOD-003, que aponta tabelas sem relacionamento, a marcou. O anotador, porém, julgou que ela não viola a regra: é uma tabela criada à mão só para exibir o logotipo no relatório, e não precisa se relacionar com nada. É, portanto, um falso positivo.

=== Precisão e revocação

A *precisão* é a fração dos achados emitidos que estão certos, VP / (VP + FP). Ela responde à pergunta de quem recebe o relatório: quando a ferramenta aponta um problema, posso confiar? A *revocação* é a fração dos problemas existentes que a ferramenta encontrou, VP / (VP + FN). Ela responde à pergunta de quem quer cobertura: quantos problemas ficaram de fora? As duas medidas costumam competir, porque uma regra mais permissiva encontra mais problemas e também erra mais. Pelo argumento do Capítulo 3, este trabalho dá prioridade à precisão: um relatório com muitos alarmes falsos perde a confiança de quem o lê.

Quando há várias regras, as medidas podem ser agregadas de duas formas. A média *micro* soma os desfechos de todas as regras antes de calcular a proporção, de modo que uma regra com muitos achados pesa mais. A média *macro* calcula a proporção de cada regra e depois tira a média entre elas, de modo que cada regra pesa igual. A primeira descreve a experiência de quem lê o relatório inteiro; a segunda, a qualidade típica de uma regra.

=== Casos indeterminados: principal, piso e teto

Alguns objetos não podem ser julgados a partir do que o modelo contém. Na MOD-005, por exemplo, o `model.bim` não registra se uma tabela foi marcada como tabela de data, de modo que, com o tempo automático desligado, não há como afirmar se a marcação foi feita. Nesses casos o anotador registra *indeterminado*. A proporção *principal* é calculada só sobre os casos decididos. Ela vem acompanhada de dois limites: o *piso*, que conta todos os indeterminados contra a ferramenta, e o *teto*, que os conta a favor. Se o piso e o teto ficam próximos da principal, os indeterminados não mudam a conclusão.

=== Intervalo de confiança de Wilson

Uma proporção medida sobre poucos casos é incerta: acertar o único achado de uma regra não prova que a regra acerta sempre. O *intervalo de confiança de 95%* expressa essa incerteza como uma faixa de valores compatíveis com o que foi observado. Foi usado o intervalo de Wilson @wilson1927, que se comporta bem justamente nas situações frequentes aqui, amostras pequenas e proporções perto de 0 ou de 1, nas quais o intervalo mais conhecido, baseado na aproximação normal, produz faixas que ultrapassam os limites de 0 e 1 ou se reduzem a um ponto. Por exemplo, um acerto em um caso dá precisão 1,00, mas com intervalo de 0,21 a 1,00: o dado é compatível tanto com uma regra excelente quanto com uma regra que erra quatro vezes em cinco.

=== Concordância e kappa de Cohen

Para saber se um critério automático substitui o julgamento humano, compara-se os dois caso a caso. A *concordância simples* é a fração de casos em que os dois dizem a mesma coisa. Ela tem um defeito: se quase todos os casos são "sim", dois julgadores que respondem "sim" sempre concordam muito sem que um saiba nada do outro. O *kappa de Cohen* @cohen1960 corrige isso, descontando a concordância que se esperaria ao acaso, dadas as proporções de "sim" e "não" de cada julgador. Vale 1 quando a concordância é perfeita, 0 quando ela é a que o acaso produziria, e fica negativo quando os dois concordam menos do que o acaso.

== Regras <sec-aval-regras>

O gabarito das regras tem 350 linhas, uma por objeto candidato a violar uma regra nos projetos P1 a P7. Um objeto é *candidato* quando é do tipo que a regra examina: para a MOD-003, toda tabela; para a PERF-001, toda coluna calculada; para a DAX-001, toda expressão que contém o operador de divisão. A anotação foi cega, como descrito no Capítulo 3: o anotador julgou cada candidato sem saber se a ferramenta o marcara. A primeira medição levou a uma releitura das divergências, e 12 julgamentos foram revistos com base na documentação, cada um com o motivo registrado e o julgamento original preservado no histórico do repositório. A revisão andou nos dois sentidos. Sete linhas da MOD-005 passaram de "viola" a "indeterminado", porque o `model.bim` não registra a marcação de tabela de data e não havia como afirmar que a tabela não estava marcada. Três linhas da DAX-001 passaram de "não viola" a "viola", porque a página da âncora usa exatamente aquele padrão como exemplo do que deve ser trocado pela função `DIVIDE` @learn-dax-divide. O padrão é a divisão *protegida* por um teste, como em `IF(denominador <> 0, numerador / denominador, BLANK())`: a expressão só divide quando o denominador é diferente de zero e, caso contrário, devolve vazio. O anotador tinha julgado que a proteção afastava o problema; a documentação diz que `DIVIDE` faz o mesmo teste de forma mais eficiente que a função `IF`. As demais revisões foram uma coluna gerada pelo recurso de agrupamento do Power BI e uma tabela de negócio sem nenhum relacionamento. A @tab-regras mostra o resultado oficial, com as regras na versão congelada.

#include "../gerado/regras.typ"

A precisão total foi de 0,88: dos 52 achados emitidos pelas regras, 46 foram confirmados pelo gabarito. A revocação total também foi de 0,88. Seis das nove regras tiveram precisão 1,00. Duas não emitiram achado algum: a MOD-002 porque nenhum dos sete projetos tem relacionamento bidirecional que ela cubra, e o gabarito confirmou a ausência, e a MOD-005 porque, com o tempo automático desligado, ela se cala por desenho, o falso negativo que o Capítulo 3 declarou; os sete casos que o anotador não pôde decidir aparecem na coluna de indeterminados. A amplitude dos intervalos de Wilson mostra o quanto o número de casos limita as conclusões por regra: a MOD-001 e a MOD-007 têm precisão 1,00 sobre um único achado, com intervalo de 0,21 a 1,00. As regras com mais casos, PERF-001 e PERF-003, têm intervalos estreitos, com limite inferior acima de 0,80.

O projeto fixou, entre os seus riscos, um limiar de precisão de 0,7 por regra, abaixo do qual a regra seria revista. A referência industrial é mais exigente: as ferramentas de análise estática do Google só mantêm uma verificação se menos de 10% dos seus avisos forem *falsos positivos efetivos* @winters2020. O conceito é definido pelo efeito sobre quem recebe o aviso, e não pela correção técnica: um aviso é falso positivo efetivo quando o desenvolvedor não toma nenhuma providência depois de vê-lo, seja porque o aviso está errado, seja porque ele não o entendeu. Por esse critério, uma explicação confusa transforma um achado correto em falso positivo efetivo, o que liga a qualidade da geração, avaliada adiante, à utilidade das regras. Só uma regra ficou abaixo do limiar: a MOD-003, com precisão de 0,14, um acerto e seis falsos positivos.

A análise desses seis falsos positivos mostrou duas causas. Quatro eram objetos que o Power BI cria desconectados de propósito. Dois eram *grupos de cálculo*, tabelas especiais cujas linhas são fórmulas DAX aplicadas sobre as medidas do modelo, por exemplo para mostrar qualquer medida no acumulado do ano sem escrever uma medida nova para cada caso; elas agem sobre as medidas, e não sobre as linhas de outra tabela, por isso não têm relacionamento. Os outros dois eram *parâmetros de campo*, tabelas que o Power BI gera para que o leitor do relatório escolha, num seletor, qual medida ou coluna um visual exibe; também elas funcionam sem relacionamento. Os dois tipos têm sinal estrutural próprio no `model.bim`: a propriedade `calculationGroup`, no primeiro caso, e uma propriedade de metadados de parâmetro, no segundo. Os outros dois, `Logo` e `Indicators`, eram tabelas digitadas à mão para a apresentação do relatório, sem nenhum sinal que as distinga de uma dimensão digitada e esquecida. Na PERF-001, os seis falsos negativos tinham uma causa só: a exceção para colunas de tabelas de data estava larga demais e excluía também as tabelas de data importadas pelo Power Query, quando a documentação só recomenda colunas calculadas na tabela de data criada em DAX.

As duas regras foram corrigidas depois da medição oficial, sempre por sinal estrutural e nunca pelo nome do objeto, e medidas de novo contra o mesmo gabarito (@tab-regras-pos-correcao). Esse resultado é *análise de erros*, não resultado: as correções foram motivadas pelos próprios casos em que são medidas, e a sua validação exigiria projetos que as regras ainda não viram.

#include "../gerado/regras-pos-correcao.typ"

A MOD-003 subiu para 0,33 e continua abaixo do limiar, por causa das duas tabelas digitadas, uma limitação declarada da regra. A PERF-001 passou a ter revocação 1,00 e precisão 0,92. Parte desse ganho, porém, está em casos indeterminados que a regra passou a marcar: contados contra ela, a precisão da PERF-001 cai para 0,77.

O conjunto de avaliação também precisava de achados suficientes. O planejamento fixou um mínimo de cerca de 40 achados confirmados em P1 a P7, abaixo do qual um oitavo projeto seria acrescentado. Os 46 achados confirmados superam o mínimo, mas 16 deles vêm de uma única regra, a PERF-003; sem ela, seriam 30.

== Recuperação <sec-aval-recuperacao>

A recuperação foi avaliada em duas etapas. A primeira escolheu o método de busca; a segunda, feita depois que a âncora passou a entrar sempre no contexto, verificou se a busca entregava trechos complementares úteis.

Na primeira etapa, o gabarito de cada regra é a sua *seção âncora*: a seção da página do Microsoft Learn que contém a passagem transcrita quando a regra foi aprovada. Para reconhecer a seção âncora entre os resultados sem depender de julgamento, cada gabarito guarda uma *frase-marca*, um trecho literal da passagem; um resultado acerta quando contém essa frase. A *consulta* é o texto que a ferramenta envia à busca: os termos de pesquisa da regra, em inglês, acrescidos dos dados do achado, como o nome do objeto. Foram 62 consultas, uma por regra e uma por achado de P1 a P7.

A busca devolve uma lista ordenada de seções, da mais à menos relevante segundo ela. Três medidas descrevem essa lista. O *acerto\@$K$* vale 1 quando a seção âncora aparece entre as $K$ primeiras posições e 0 caso contrário; com $K = 5$, por exemplo, ele pergunta se a âncora estaria entre os cinco trechos que caberiam no contexto do modelo. A *precisão\@$K$* é a fração das $K$ primeiras seções que são a âncora; como cada consulta tem uma única seção âncora, ela vale no máximo $1 \/ K$, e por isso cai à medida que $K$ cresce. O *MRR* (_mean reciprocal rank_) é a média do inverso da posição em que a âncora aparece: vale 1 quando ela está em primeiro lugar, 0,5 quando está em segundo, 0,33 em terceiro, e assim por diante, até a décima posição, a partir da qual conta zero. Ele premia a busca que põe a âncora mais acima. As médias são *macro*: calculadas primeiro entre as consultas de cada regra e depois entre as nove regras, para que a PERF-001, com mais achados, não domine o resultado. A @tab-recuperacao mostra a combinação vencedora entre as 24 comparadas.

#include "../gerado/recuperacao.typ"

A seção âncora apareceu entre os cinco primeiros resultados em todas as regras, e na primeira posição em menos da metade delas. O número precisa de duas ressalvas, registradas na decisão. A primeira é um *efeito teto*, nome dado à situação em que muitas alternativas atingem o valor máximo da medida e ela deixa de distinguir a melhor: 7 das 12 combinações do corpus completo chegaram ao acerto\@5 de 1,00. Isso acontece porque as consultas carregam os termos da própria regra, que também aparecem na passagem âncora, o que torna a tarefa mais fácil do que uma pergunta livre de um usuário seria. A segunda é que uma única consulta decidiu o empate: a busca densa ficou fora dele só porque a consulta da MOD-005 encontrou a âncora na sétima posição, e essa regra, com uma consulta, pesa um nono da média. A ampliação do corpus para as referências completas de DAX e M, por outro lado, não prejudicou a recuperação: o corpus restrito à orientação não superou o completo.

A segunda etapa mudou a pergunta. Com a âncora fixa como primeiro trecho, a busca só escolhe os *trechos complementares*, do segundo ao quinto, que acrescentam contexto à âncora. A medida anterior, que procurava a âncora, deixou de informar sobre eles. A nova medida é a *pertinência*: a fração dos complementares que de fato ajudam a explicar o achado, segundo o julgamento do autor. Foram comparadas as três buscas descritas no Capítulo 3: a lexical BM25, a densa e a híbrida. Para não julgar a mesma seção várias vezes nem favorecer uma busca, as seções entregues pelas três foram reunidas num só conjunto, técnica chamada de _pooling_: o autor julgou as 89 seções distintas entregues em 70 consultas, sem saber qual busca tinha entregado cada uma. A regra, fixada antes, só trocaria o BM25 por outra busca se ela superasse a média do BM25 em pelo menos 0,10 (@tab-complementares).

#include "../gerado/complementares.typ"

Nenhuma alternativa superou o BM25 pela margem fixada, e ele foi mantido. A medição mostrou um problema que nenhuma troca de busca resolveria: na PERF-001, nenhuma das três buscas entregou complemento pertinente. A consulta dessa regra leva o nome da coluna, e 13 das 31 colunas estão em tabelas de data, com nomes como `Year`, `Month` ou `Mth of year`. A explicação provável é que esses nomes coincidem com nomes e termos de funções DAX: as buscas trouxeram páginas da referência de funções, como a de `YEARFRAC`, sem relação com o achado. O defeito, portanto, está na construção da consulta, não no tipo de busca. Registrou-se também que, considerando só as consultas por achado, que são as que a ferramenta de fato faz, a busca densa superaria o BM25 por 0,13; a regra aprovada antes da medição usava as 70 consultas e foi mantida.

== Geração <sec-aval-geracao>

A geração foi avaliada sobre todos os 61 achados que as regras emitem em P1 a P7, sem amostragem. Como a geração depende só de quais achados existem, e não de como as regras os detectaram, foi usada a versão corrigida das regras; o resultado oficial da detecção continua sendo o da @tab-regras. Os 61 achados receberam explicação: nenhuma resposta foi descartada pela validação da citação. A rodada levou 8 minutos e 53 segundos e foi gravada no cache, de modo que repeti-la reproduz exatamente os textos avaliados.

Cada explicação foi julgada pelo autor numa planilha que não mostrava nenhum dos sinais automáticos, para que a comparação entre os dois fosse válida. Três itens foram julgados com "sim", "não" ou "indeterminado", com justificativa obrigatória no "não":

- *pertinente*: pelo menos um trecho citado é a passagem da documentação que sustenta o achado, e não apenas um trecho existente no contexto;
- *fiel*: tudo o que a explicação afirma é sustentado pelos trechos citados ou pelos fatos do achado, sem números, nomes ou comportamentos inventados;
- *recomendação correta*: a recomendação resolve o problema neste modelo, sem erro técnico.

Uma explicação é *utilizável como está* quando recebe "sim" nos três itens. Não houve casos indeterminados. A @tab-geracao mostra o resultado.

#include "../gerado/geracao.typ"

A recuperação e a citação funcionaram: todas as 61 explicações citaram uma passagem pertinente. O problema está no que o modelo escreve a partir dela. Pouco mais da metade das explicações foi fiel aos trechos, e pouco mais de um terço pode ser entregue sem edição. A @tab-geracao-por-regra mostra que os erros se concentram em duas regras.

#include "../gerado/geracao-por-regra.typ"

Os "não" seguem padrões, e não se distribuem ao acaso. Na PERF-001, que responde por metade dos achados, a maior parte das explicações infiéis repete a mesma distorção: o trecho diz que o VertiPaq *comprime* com menos eficiência as colunas calculadas, e a explicação diz que ele não as "compreende" eficientemente, ou fala em "descompressão". Tudo indica um erro de tradução do modelo, que escreve em português sobre uma fonte em inglês. As recomendações erradas da PERF-001 propõem sintaxe DAX para o Power Query ou funções de M que não existem. Na DAX-001, cinco das seis explicações tratam como defeito o fato de `DIVIDE` devolver vazio quando o denominador é zero. O vazio, `BLANK` no DAX, é o valor que representa a ausência de dado, e um visual simplesmente não exibe a linha de uma medida que devolve vazio; o trecho citado diz que esse é, em geral, o comportamento desejável para uma medida. Na MOD-003, as três recomendações mandam relacionar tabelas auxiliares que são desconectadas de propósito, o mesmo ponto cego da regra. Em contraste, a PERF-003 teve 15 de 16 explicações utilizáveis.

Por fim, a @tab-concordancia compara o julgamento humano com os dois critérios automáticos da ferramenta: se a explicação cita a seção âncora e se a conferência de números e nomes não acusou divergência.

#include "../gerado/concordancia.typ"

No item pertinente, a concordância foi de 0,98, mas o kappa foi zero. Não há contradição: quase todos os casos caíram na mesma célula, ambos "sim", e o kappa, que desconta a concordância esperada ao acaso, perde o sentido quando uma categoria domina a tabela, um paradoxo conhecido da medida @feinstein1990. O que se pode afirmar é mais simples: a combinação da âncora fixa com a citação obrigatória entregou evidência pertinente em todos os achados, e o único caso em que o modelo não citou a âncora citou outra passagem que também sustentava o achado.

No item fiel, a conferência automática concordou com o humano em menos da metade dos casos, com kappa de −0,08, nenhum acordo além do acaso. Em 24 explicações a conferência não viu problema e a leitura humana encontrou infidelidade. A razão é que as infidelidades reais são de sentido, como "compreende" no lugar de "comprime", e não números ou nomes trocados, que é o que a conferência verifica. O resultado mudou a ferramenta: o aviso, que se chamava "divergência de fidelidade", passou a se chamar "números ou nomes sem origem nos trechos", e toda explicação gerada passou a vir com uma nota dizendo que a ausência de aviso não garante a correção do texto.

== Estudo de caso: o projeto P8 <sec-caso-p8>

O P8 é um modelo de vendas de varejo online, de autoria própria, com 19 tabelas, 93 medidas e 35 colunas calculadas. Ele foi o primeiro projeto auditado e o que motivou várias decisões de método, mas não entra nas métricas, porque não pode ser reproduzido por terceiros. A ferramenta encontra nele 15 achados de oito regras. O mais característico é o tempo automático ligado. O *tempo automático de data/hora* é uma opção do Power BI Desktop que, para cada coluna de data do modelo, cria uma tabela oculta de calendário, com ano, trimestre, mês e dia, para que o autor do relatório possa agrupar e navegar pelas datas sem construir um calendário. O Power BI cria uma tabela-modelo (`DateTableTemplate`) e, a partir dela, uma tabela local (`LocalDateTable`) para cada coluna de data. O P8 tem uma dimensão de data própria, `DimCalendar`, uma tabela de calendário criada pelo autor, com uma linha por dia, e, ao lado dela, quatro tabelas automáticas: a tabela-modelo e três tabelas locais, uma para cada coluna de data. As quatro aumentam o modelo sem necessidade, porque o calendário próprio já cumpre o papel delas. A MOD-001 aponta as quatro.

A MOD-005 aponta a própria `DimCalendar`. *Marcar como tabela de data* é a forma de dizer ao Power BI qual tabela é o calendário oficial do modelo; a marcação é exigida pelas funções clássicas de inteligência temporal do DAX, como as de acumulado do ano, e, quando ela é feita, o Power BI remove as tabelas automáticas que havia criado @learn-date-tables. Como as colunas de data da `DimCalendar` ainda apontam para tabelas automáticas, a tabela comprovadamente não foi marcada, e esta é a prova que a regra usa, como descrito no Capítulo 3.

#figure(
  kind: image,
  block(width: 100%, stroke: 0.5pt, inset: 8pt, align(left, {
    set text(size: 9pt)
    set par(first-line-indent: 0pt, justify: true, leading: 0.5em, spacing: 0.8em)
    [*Achado (regra MOD-001):* A tabela oculta 'LocalDateTable\_0d3564f1-…' foi gerada pelo Tempo automático de data/hora, não pelo autor do modelo.

    *Explicação:* A tabela 'LocalDateTable\_0d3564f1-…' foi gerada pelo Auto date/time, o que pode aumentar o tamanho do modelo e dificultar a propagação de filtros entre tabelas. Isso não é recomendado para modelos mais complexos ou quando uma única tabela de datas é desejável.

    *Recomendação:* Crie uma tabela de datas manualmente usando DAX, como a função CALENDAR ou CALENDARAUTO, e conecte-a às tabelas relevantes. Isso permitirá uma propagação de filtros mais eficiente e manterá o modelo mais limpo.

    *Trechos citados:* [1] Auto date/time guidance in Power BI Desktop › Recommendations (âncora); [3] … › Considerations; [5] Design guidance for date tables in Power BI Desktop › Use Auto date/time.]
  })),
  caption: [Achado do P8 com a explicação gerada pela ferramenta (identificador da tabela abreviado)],
) <fig-exemplo-p8>
#fonte[Saída da ferramenta no projeto P8, execução de 13/10/2026.]

A @fig-exemplo-p8 mostra um desses achados como sai da ferramenta. A explicação é correta e está ancorada: o tamanho do modelo e a impossibilidade de propagar um filtro de data a várias tabelas estão entre as considerações da página citada, e a recomendação é a que a própria página faz @learn-auto-date-time. Na primeira execução completa, todos os 15 achados receberam explicação com citação válida, e 14 citaram a seção âncora da regra.

A leitura à mão das 15 explicações, porém, encontrou dois erros que nenhum critério automático acusou, ambos na MOD-006. Num deles, a recomendação mandava integrar numa única tabela a dimensão de produto, a de subcategoria e também a tabela de fatos de vendas; juntar fatos e dimensão é um erro de modelagem. No outro, recomendava uma tabela "normalizada" quando a fonte diz o contrário, desnormalizar. Como todos os nomes citados existiam no achado, a conferência automática não tinha o que acusar. Foram esses casos que levaram a rubrica a ter um item próprio para a correção da recomendação.

Quanto ao desempenho, a geração custou em média 8,1 segundos por achado, com pior caso de 10,5 segundos, numa GPU de 6 GB, e a auditoria completa do P8 levou 123 segundos, incluindo a carga do modelo. Duas execuções do mesmo projeto não produzem textos idênticos, apesar da temperatura 0: os totais se repetem, mas a redação e algumas citações variam, e numa das execuções pela interface 13 dos 15 achados citaram a âncora. Com o cache ligado, a segunda auditoria do P8 caiu de 165,6 segundos para 1,5 segundo, com textos idênticos aos da primeira.
