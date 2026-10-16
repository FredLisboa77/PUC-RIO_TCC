#import "../abnt.typ": fonte

= Fundamentação e trabalhos relacionados <cap-fundamentacao>

Este capítulo apresenta os conceitos sobre os quais o trabalho se apoia, em quatro frentes. A primeira é o próprio objeto auditado: o modelo semântico do Power BI, com as suas tabelas, relacionamentos e fórmulas. A segunda são as boas práticas de modelagem que as regras verificam. A terceira é a análise estática, a área da engenharia de software que estuda ferramentas que examinam um artefato sem executá-lo, e o que ela aprendeu sobre o custo dos falsos alarmes. A quarta são os modelos de linguagem e a técnica de geração aumentada por recuperação, usados para explicar os achados. O capítulo termina com as ferramentas existentes para auditar modelos do Power BI e com a posição deste trabalho em relação a elas.

== O Power BI e o modelo semântico <sec-powerbi>

O Power BI é a plataforma de análise de dados da Microsoft. Nele, um relatório tem duas partes. O _modelo semântico_ organiza os dados: define as tabelas, as colunas, os relacionamentos entre as tabelas e as fórmulas de cálculo. O _relatório_ é o conjunto de páginas e visuais, como gráficos, tabelas e cartões, que consultam o modelo. Cada visual, ao ser exibido, envia ao modelo uma consulta que filtra, agrupa e resume os dados @learn-star-schema. O modelo é, portanto, a camada da qual depende a correção e o desempenho de tudo o que o relatório mostra, e é a camada que este trabalho audita. O modelo é construído no Power BI Desktop, a aplicação gratuita de autoria, e publicado no serviço do Power BI para ser compartilhado.

=== Modos de armazenamento e o VertiPaq

Um modelo pode guardar os dados de três modos. No modo de _importação_, o mais comum e o padrão do Power BI Desktop, os dados são copiados das fontes para dentro do modelo. Nesse processo, o mecanismo de armazenamento chamado _VertiPaq_ os comprime e os guarda em disco e, quando o modelo é consultado, os carrega inteiros na memória, o que permite respostas muito rápidas. A documentação estima que 10 GB de dados de origem podem ocupar cerca de 1 GB depois da compressão @learn-modos. Em contrapartida, os dados do modelo só são tão recentes quanto a última _atualização_, a operação que recarrega os dados das fontes, normalmente agendada. No modo _DirectQuery_, o modelo guarda apenas a estrutura, e cada consulta é traduzida para a linguagem da fonte e enviada a ela; o modo _composto_ mistura os dois por tabela. Os projetos avaliados neste trabalho usam o modo de importação, e várias regras, como as de desempenho, tratam de como o VertiPaq armazena os dados.

O VertiPaq armazena cada coluna separadamente, em estruturas próprias. Colunas numéricas são codificadas pelo próprio valor; colunas de texto recebem um dicionário, no qual cada valor distinto ganha um identificador numérico, e a coluna guarda apenas os identificadores @learn-data-reduction. Por isso o tamanho do modelo depende não só do número de linhas, mas também do número de colunas e da quantidade de valores distintos em cada uma: uma coluna de texto com muitos valores distintos ocupa mais espaço que uma coluna numérica.

=== Tabelas, colunas e tipos de dados

Cada tabela do modelo tem colunas, e cada coluna tem um _tipo de dado_ que determina o que ela pode guardar e como é armazenada. Para números, o Power BI oferece três tipos: _Número inteiro_; _Número decimal fixo_, com exatamente quatro casas decimais; e _Número decimal_, armazenado em ponto flutuante, de forma aproximada, com até 15 dígitos de precisão @learn-tipos-de-dados. Cada coluna também tem uma _agregação padrão_, a forma como o Power BI a resume quando ela é arrastada para um visual sem nenhuma fórmula: somar, contar, tirar a média ou não resumir.

=== Relacionamentos, cardinalidade e direção do filtro

Um _relacionamento_ liga uma coluna de uma tabela a uma coluna de outra e serve para propagar filtros: quando o leitor do relatório filtra uma tabela, o filtro passa pelos relacionamentos às tabelas relacionadas @learn-relacionamentos. A documentação dá um exemplo com quatro tabelas, categoria, produto, ano e vendas. Ao filtrar a categoria "Cat-A", o filtro passa à tabela de produtos, isolando os produtos daquela categoria, e daí à de vendas, isolando as vendas desses produtos; um filtro no ano passa diretamente às vendas, e os dois filtros se combinam.

Cada relacionamento tem uma _cardinalidade_, que descreve quantas linhas de cada lado podem se corresponder. No lado "um", a coluna tem valores únicos; no lado "muitos", pode ter valores repetidos. As opções são um-para-muitos (ou, lido ao contrário, muitos-para-um), a mais comum; um-para-um, em que os dois lados têm valores únicos; e muitos-para-muitos @learn-relacionamentos. Num relacionamento entre produtos e vendas, por exemplo, cada produto aparece uma vez na tabela de produtos e muitas vezes na de vendas: é um relacionamento um-para-muitos.

Cada relacionamento tem também uma _direção do filtro cruzado_. Na direção _única_, o filtro vai sempre do lado "um" para o lado "muitos", dos produtos para as vendas. Na direção _ambas_, chamada de _bidirecional_, ele também volta, das vendas para os produtos. Relacionamentos um-para-um são sempre bidirecionais. A documentação adverte que relacionamentos bidirecionais podem prejudicar o desempenho e criar caminhos ambíguos de propagação, e recomenda usá-los só quando necessário @learn-relacionamentos. Ela registra ainda que uma tabela sem relacionamentos, dita _desconectada_, é incomum, mas pode ser legítima quando serve para receber uma escolha do leitor, como um valor de câmbio escolhido num seletor e usado depois por uma fórmula @learn-relacionamentos. Esse caso reaparece na avaliação da regra MOD-003, no Capítulo 4.

=== DAX: medidas, colunas calculadas e tabelas calculadas

O _DAX_ (_Data Analysis Expressions_) é a linguagem de fórmulas dos modelos tabulares, usada no Power BI, no Analysis Services e no Power Pivot do Excel @learn-dax. Ela aparece em três tipos de objeto do modelo, que diferem no momento em que são calculados.

Uma _medida_ é uma fórmula calculada no momento da consulta, cujo resultado depende do _contexto_: dos filtros aplicados pelo visual, pelos seletores e pelas próprias fórmulas. A medida `Total Sales = SUM(Sales[Sales Amount])`, por exemplo, devolve a soma das vendas de cada categoria quando colocada num visual que agrupa por categoria, e o total geral quando colocada sozinha num cartão. As medidas não guardam valores; são recalculadas a cada consulta @learn-dax.

Uma _coluna calculada_ é uma coluna acrescentada a uma tabela cujo valor, linha a linha, é definido por uma fórmula DAX, como uma coluna que junta o ano e o trimestre num texto "2017 Q1". Ao contrário da medida, ela é calculada na atualização dos dados e guardada no modelo, ocupando memória como qualquer outra coluna @learn-dax. Uma _tabela calculada_ é uma tabela inteira definida por uma fórmula DAX, em vez de carregada de uma fonte; o caso típico é a tabela de calendário gerada pelas funções `CALENDAR` ou `CALENDARAUTO` @learn-auto-date-time.

=== Power Query e a linguagem M

Antes de chegar ao modelo, os dados passam pelo _Power Query_, o mecanismo de preparação de dados do Power BI, que se conecta às fontes e aplica transformações como remover colunas, filtrar linhas, mesclar e agrupar consultas @learn-power-query. Cada transformação é registrada como um passo de uma consulta que se repete a cada atualização. Por trás da interface gráfica, toda consulta é escrita na _linguagem M_, a linguagem de transformação do Power Query, que o autor também pode editar diretamente @learn-power-query. Uma mesma coluna derivada pode, assim, ser criada de duas formas: como coluna personalizada no Power Query, em M, ou como coluna calculada no modelo, em DAX. A escolha entre as duas é o assunto da regra PERF-001.

== Boas práticas de modelagem <sec-boas-praticas>

=== O esquema estrela

O _esquema estrela_ é a abordagem de modelagem consolidada nos armazéns de dados relacionais e descrita em profundidade por #cite(<kimball2013>, form: "prose"). Ela classifica as tabelas em dois papéis. As _tabelas de dimensão_ descrevem as entidades do negócio, as "coisas" que se analisam: produtos, clientes, lojas e, quase sempre, o próprio tempo, numa dimensão de data com uma linha por dia. As _tabelas de fatos_ registram os eventos ou observações: vendas, pedidos, saldos de estoque. Uma tabela de fatos tem colunas que apontam para as dimensões e colunas numéricas que são resumidas @learn-star-schema.

A documentação do Power BI explica por que o esquema estrela se encaixa no produto. Cada visual gera uma consulta que filtra, agrupa e resume; as dimensões servem para filtrar e agrupar, e os fatos, para resumir. No modelo, o papel de cada tabela é definido pelos relacionamentos: o lado "um" de um relacionamento um-para-muitos é a dimensão, e o lado "muitos", o fato @learn-star-schema. A documentação recomenda não misturar os dois papéis numa mesma tabela e ter "o número certo de tabelas com os relacionamentos certos", e reconhece que o bom desenho é "parte ciência, parte arte", podendo ser contrariado quando houver razão @learn-star-schema.

Duas variações desse esquema aparecem nas regras. No _floco de neve_, uma dimensão é normalizada em várias tabelas encadeadas, como produto, subcategoria e categoria; em geral, recomenda-se integrá-las numa só tabela. A _dimensão degenerada_ é um atributo da própria tabela de fatos usado para filtrar, como o número do pedido, que pode justificar um relacionamento um-para-um @learn-star-schema @learn-um-para-um.

=== A documentação oficial como referência

As boas práticas de modelagem do Power BI estão publicadas na seção de orientação (_guidance_) do Microsoft Learn, o portal de documentação da Microsoft, mantida pela equipe do produto e atualizada com ele. Este trabalho adota essa documentação como a referência normativa das regras, por três razões: ela é pública e pode ser citada; ela traz, junto de cada recomendação, as exceções que a própria Microsoft reconhece; e ela pode ser coletada e indexada para a recuperação, como descrito no Capítulo 3. A escolha tem uma consequência importante para o método: uma regra só é aceita se houver uma passagem da documentação que a sustente, e a explicação gerada para cada achado precisa citar essa passagem.

== Análise estática e o custo dos falsos positivos <sec-analise-estatica>

A _análise estática_ é a família de técnicas que examina um artefato de software sem executá-lo, em busca de defeitos ou de desvios de boas práticas. O exemplo mais comum são os verificadores de código-fonte, que apontam erros prováveis enquanto o programador escreve. A ferramenta deste trabalho é uma análise estática no mesmo sentido: examina a definição do modelo semântico, no arquivo, sem carregar os dados nem executar as consultas.

A literatura sobre essas ferramentas registra, de forma consistente, que o maior obstáculo à sua adoção não é a falta de cobertura, mas o excesso de alarmes falsos. Num estudo com vinte desenvolvedores, #cite(<johnson2013>, form: "prose") verificaram que, embora todos considerassem as ferramentas úteis, os falsos positivos e a forma como os avisos são apresentados eram barreiras ao uso. A experiência do Google aponta na mesma direção. #cite(<sadowski2018>, form: "prose") descrevem uma infraestrutura de análise estática usada diariamente pela maioria dos engenheiros da empresa, que encontra milhares de problemas por dia corrigidos pelos próprios engenheiros, por escolha deles, e atribuem esse resultado às lições de tentativas anteriores. O critério que a empresa adota é explícito: uma verificação só é mantida se menos de 10% dos seus avisos forem _falsos positivos efetivos_, isto é, avisos sobre os quais o desenvolvedor não age, seja porque estão errados, seja porque não foram entendidos @winters2020.

Duas lições dessa literatura orientam este trabalho. A primeira é que precisão vale mais que cobertura: uma regra que erra com frequência compromete a confiança no relatório inteiro, e é melhor não ter a regra. É essa a justificativa do critério de detectabilidade descrito no Capítulo 3. A segunda é que a explicação faz parte da precisão: um aviso correto que não é entendido tem, para quem o recebe, o mesmo efeito de um aviso errado. É por isso que a qualidade das explicações geradas é avaliada no Capítulo 4.

== Modelos de linguagem e geração aumentada por recuperação <sec-llm-rag>

=== Modelos de linguagem

Um _modelo de linguagem de grande porte_ (_large language model_, LLM) é uma rede neural treinada sobre grandes volumes de texto para prever a continuação de um texto. Os modelos atuais usam a arquitetura _Transformer_, baseada num mecanismo de atenção que relaciona cada parte do texto com as demais @vaswani2017. O modelo não lê palavras, e sim _tokens_, pedaços de palavra de um vocabulário fixo; a _janela de contexto_ é o número máximo de tokens que ele considera de uma vez, somando o pedido e a resposta. Para gerar, o modelo atribui uma probabilidade a cada token possível e escolhe um; a _temperatura_ controla essa escolha, de modo que valores baixos favorecem os tokens mais prováveis e tornam a saída mais estável.

Os modelos de _instrução_ são versões ajustadas para seguir pedidos em linguagem natural. Alguns são distribuídos abertamente e podem ser executados na própria máquina, como a família Qwen2.5, usada neste trabalho @qwen2024. Para caber em equipamentos modestos, esses modelos costumam ser _quantizados_: os seus parâmetros, normalmente guardados com 16 bits, passam a ser guardados com menos bits, como 4, o que reduz a memória necessária com alguma perda de qualidade. A execução local tem uma vantagem própria para a auditoria: o modelo semântico de um cliente, que descreve a estrutura dos seus dados, não precisa ser enviado a um serviço externo.

=== Alucinação e fidelidade

Os modelos de linguagem produzem, com frequência, texto fluente e convincente que não é sustentado pela informação disponível, fenômeno chamado de _alucinação_. Num levantamento abrangente, #cite(<ji2023>, form: "prose") distinguem dois tipos: a alucinação _intrínseca_, em que o texto gerado contradiz a fonte, e a _extrínseca_, em que o texto não pode ser verificado a partir dela. O conceito oposto é a _fidelidade_: um texto é fiel quando tudo o que afirma é sustentado pela fonte. Para uma ferramenta de auditoria, a alucinação é especialmente perigosa, porque uma explicação errada, escrita com segurança, pode levar o dono do modelo a uma correção errada.

=== Geração aumentada por recuperação

A _geração aumentada por recuperação_ (_retrieval-augmented generation_, RAG) é a técnica de buscar, antes de gerar, trechos de uma base de documentos relevantes para o pedido, e entregá-los ao modelo junto com o pedido, para que ele responda com base neles @lewis2020. #cite(<lewis2020>, form: "prose"), que deram nome à técnica, combinam a memória _paramétrica_ do modelo, o que ele aprendeu no treinamento, com uma memória _não paramétrica_, a base de documentos consultada no momento, e relatam respostas mais específicas e factuais que as de um modelo sem recuperação. A técnica tem duas vantagens para este trabalho: a base pode ser a documentação oficial, atualizada, em vez do conhecimento congelado no treinamento do modelo; e a resposta pode ser verificada contra os trechos entregues.

A verificação exige que o modelo diga de onde tirou cada afirmação. #cite(<gao2023>, form: "prose") propuseram uma avaliação automática de respostas com citações e mostraram que mesmo os melhores modelos da época deixavam de ter as suas afirmações completamente sustentadas pelas citações em metade das respostas de um dos conjuntos avaliados. Citar, portanto, não garante fidelidade: a citação torna a verificação possível, mas não a dispensa. Essa distinção é medida no Capítulo 4.

=== Recuperação lexical e densa

A qualidade da geração depende do que a recuperação entrega. Há duas famílias de busca. A _busca lexical_ compara as palavras da consulta com as dos documentos. O seu representante clássico, o BM25, dá a cada documento uma pontuação que cresce com o número de vezes que as palavras da consulta aparecem nele, com peso maior para as palavras raras no conjunto de documentos e com um ajuste pelo tamanho do documento @robertson2009. A _busca densa_ converte a consulta e os documentos em vetores numéricos, chamados _embeddings_, produzidos por um modelo treinado para que textos de significado parecido fiquem próximos; os documentos são ordenados pela proximidade com a consulta. Ela encontra documentos que dizem a mesma coisa com outras palavras, mas pode deixar escapar nomes exatos, como o de uma função. A família de modelos de embedding BGE, da qual vem o modelo usado neste trabalho, é um exemplo recente @xiao2023.

A busca densa não supera a lexical em todos os casos. Numa comparação sobre dezoito conjuntos de dados de domínios diversos, #cite(<thakur2021>, form: "prose") concluíram que o BM25 é uma linha de base robusta quando o sistema é aplicado a um domínio para o qual não foi treinado. As duas famílias também podem ser combinadas: a _fusão recíproca de posições_ soma, para cada documento, o inverso da sua posição em cada uma das listas, e costuma superar cada busca isolada @cormack2009. Por essas razões, este trabalho não escolheu a busca de antemão, mas por medição, como descreve o Capítulo 3.

== Ferramentas existentes <sec-ferramentas>

Existem ferramentas consolidadas para verificar boas práticas em modelos do Power BI, e nenhuma delas é substituída por este trabalho. A mais conhecida é o _Best Practice Analyzer_ (BPA) do Tabular Editor. O Tabular Editor 2 é um editor de modelos tabulares do Analysis Services e do Power BI gratuito e de código aberto, sob licença MIT, mantido por Daniel Otykier e disponível no GitHub @tabular-editor-2; existe também uma versão comercial, o Tabular Editor 3. O BPA verifica o modelo contra um conjunto de regras, lista todos os objetos que violam cada uma, e pode corrigir automaticamente muitos dos problemas que encontra; cada regra é uma condição escrita sobre os objetos do modelo, com uma severidade e uma descrição @tabular-editor-bpa. A Microsoft publica um conjunto de regras para o BPA, organizado em categorias como desempenho, expressões DAX, prevenção de erros, formatação e manutenção @ms-bpa-rules. Este trabalho usou o BPA apenas como referência conceitual e escreveu as suas regras do zero, por duas razões: as regras do BPA são condições avaliadas pelo próprio Tabular Editor, o que acrescentaria à ferramenta uma dependência de outro programa, e o critério deste trabalho exige que cada regra seja sustentada por uma passagem da documentação, verificada antes de a regra ser escrita.

No ambiente do Microsoft Fabric, a biblioteca Python _Semantic Link Labs_, publicada pela Microsoft para uso em notebooks, oferece um analisador de boas práticas e um analisador do VertiPaq para modelos semânticos já publicados @semantic-link-labs. Para a camada de relatório, o _Fab Inspector_, sucessor do PBI Inspector, testa os arquivos do relatório no formato PBIR (_Power BI Enhanced Report Format_) com regras declarativas em JSON (_JavaScript Object Notation_), um formato de texto para dados estruturados, que verificam, por exemplo, a qualidade dos visuais @fab-inspector.

#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr),
    align: (left, left, left, left),
    table.header([*Ferramenta*], [*O que examina*], [*Onde executa*], [*Como apresenta o achado*]),
    [BPA do Tabular Editor], [Modelo semântico], [Tabular Editor 2 (gratuito, código aberto) ou 3, com o modelo aberto], [Regra violada, severidade e descrição da regra; correção automática em muitos casos],
    [Semantic Link Labs], [Modelo semântico publicado], [Notebook do Microsoft Fabric], [Resultado do analisador de boas práticas e do analisador do VertiPaq],
    [Fab Inspector], [Camada de relatório (PBIR)], [Máquina local, integração contínua ou serviço], [Resultado de regras declarativas em JSON],
    [Este trabalho], [Modelo semântico no arquivo `model.bim`], [Máquina local, sem publicar o modelo e sem acessar os dados], [Explicação e recomendação geradas para o achado, com a citação da passagem da documentação que o sustenta],
  ),
  caption: [Ferramentas de verificação de boas práticas no Power BI],
) <tab-ferramentas>
#fonte[Elaborado pelo autor a partir da documentação de cada ferramenta.]

A @tab-ferramentas resume as diferenças. A contribuição deste trabalho não está em verificar mais regras que essas ferramentas, e sim em três características. Cada regra é aceita por um critério explícito, que exige uma passagem citável da documentação e evidência suficiente no arquivo. Cada achado vem acompanhado de uma explicação redigida para o caso concreto, com a citação verificável da passagem que o sustenta. E tanto as regras quanto as explicações foram avaliadas contra julgamento humano, com os resultados publicados: na documentação consultada das ferramentas acima, não se encontrou medição publicada da precisão das suas regras.
