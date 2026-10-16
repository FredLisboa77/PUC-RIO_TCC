#import "../abnt.typ": fonte

= Introdução <cap-introducao>

== Contexto

O Power BI é a plataforma de análise de dados da Microsoft, usada para construir relatórios e painéis a partir de dados de negócio. Por trás de cada relatório há um _modelo semântico_: o conjunto de tabelas, relacionamentos e fórmulas que organiza os dados e que cada gráfico consulta. A correção e o desempenho de tudo o que o relatório mostra dependem desse modelo. Uma fórmula que divide por um valor que pode ser zero, um relacionamento que propaga filtros nos dois sentidos sem necessidade ou uma opção padrão esquecida ligada podem produzir números inesperados, consultas lentas ou um modelo maior do que precisa ser.

Na experiência profissional do autor, esses modelos são construídos, em boa parte, por analistas de negócio, que dominam os dados e as perguntas da empresa, mas nem sempre conhecem as boas práticas de modelagem que a própria Microsoft documenta. A Microsoft mantém essas boas práticas publicadas no Microsoft Learn, o seu portal de documentação, e existem ferramentas que verificam regras sobre um modelo, como o _Best Practice Analyzer_ do Tabular Editor, apresentado no Capítulo 2. Verificar um modelo, porém, é só metade do trabalho: quem recebe um aviso precisa entender por que aquilo é um problema naquele modelo e o que fazer, e a literatura sobre ferramentas de análise mostra que avisos falsos ou mal explicados fazem os usuários abandoná-las @johnson2013 @winters2020.

Dois desenvolvimentos recentes tornam possível uma abordagem nova. O primeiro é o formato PBIP (_Power BI Project_), com o qual o Power BI Desktop passou a gravar um projeto como arquivos de texto, em vez de um arquivo binário fechado, o que permite que um programa leia a definição completa do modelo @learn-pbip. O segundo são os modelos de linguagem de grande porte, capazes de redigir explicações em linguagem natural, e a técnica de geração aumentada por recuperação, que entrega ao modelo de linguagem trechos de documentação para que ele responda com base neles @lewis2020. Esses modelos, porém, inventam com frequência informações que soam convincentes @ji2023, o que é especialmente perigoso numa auditoria.

== Problema

O problema que este trabalho aborda é como auditar automaticamente um modelo semântico do Power BI de modo que cada problema apontado seja *confiável*, por ser detectado de forma reprodutível e fundamentado na documentação oficial, e *compreensível*, por vir acompanhado de uma explicação e de uma recomendação específicas para aquele modelo, sem que o modelo de linguagem usado para explicar possa inventar problemas ou fundamentos.

A tensão está em combinar as duas qualidades. Regras determinísticas são confiáveis e mensuráveis, mas a sua explicação é um texto fixo, igual para todos os casos. Um modelo de linguagem escreve explicações sob medida, mas pode errar com segurança. O trabalho investiga se a divisão de papéis entre as duas técnicas, com as regras decidindo e o modelo de linguagem apenas explicando, com a obrigação de citar a documentação, entrega as duas qualidades, e mede até onde isso funciona.

== Objetivos

O objetivo geral é desenvolver e avaliar uma ferramenta que audite projetos do Power BI no formato PBIP, combinando regras determinísticas ancoradas na documentação oficial da Microsoft com explicações geradas por um modelo de linguagem executado localmente, com citação obrigatória da documentação.

Os objetivos específicos são:

+ ler o modelo semântico de um projeto PBIP a partir do arquivo `model.bim` e convertê-lo numa representação interna normalizada;
+ definir um critério explícito para decidir quais regras de boas práticas podem ser verificadas de forma confiável a partir do arquivo, e implementar as regras que o satisfazem, cada uma sustentada por uma passagem citável do Microsoft Learn;
+ construir uma base de documentação a partir do Microsoft Learn e escolher, por medição, o método de recuperação dos trechos;
+ gerar, para cada achado, uma explicação e uma recomendação com um modelo de linguagem local, validando por código que a resposta cita a documentação fornecida;
+ oferecer a auditoria por linha de comando, por uma interface gráfica e por um relatório em HTML e PDF;
+ avaliar separadamente a detecção, a recuperação e a geração, contra julgamento humano, em projetos públicos.

A avaliação responde a três perguntas, uma para cada camada da ferramenta, retomadas no Capítulo 4:

- *Pergunta 1*: as regras apontam os problemas certos, com que precisão e revocação?
- *Pergunta 2*: a recuperação encontra a passagem da documentação que sustenta cada achado?
- *Pergunta 3*: a explicação gerada é pertinente, fiel à documentação e tecnicamente correta, a ponto de poder ser entregue sem edição?

== Contribuições

O trabalho faz quatro contribuições.

A primeira é um *critério de detectabilidade* para regras de auditoria de modelos, formulado em três testes aplicados antes de escrever qualquer regra: o problema precisa ser decidível no arquivo, precisa haver uma passagem citável da documentação que o sustente e a evidência no arquivo precisa ser suficiente para afirmar o problema sem confundi-lo com casos parecidos. O critério reduziu o conjunto previsto de 20 a 25 regras para 9, e essa redução é tratada como resultado do método, e não como falta de esforço: a regra de maior rendimento esperado foi rejeitada pelo terceiro teste, com a medição que mostrou por quê.

A segunda é uma *arquitetura* em que o modelo de linguagem não detecta problemas, apenas os explica, e em que a passagem da documentação que sustenta cada regra entra sempre no contexto do modelo, de modo que a qualidade da busca afeta só os trechos complementares.

A terceira é uma *avaliação* das três camadas contra julgamento humano, com regras de decisão fixadas antes das medições e com resultados negativos relatados: as regras atingiram precisão de 0,88, todas as explicações citaram uma passagem pertinente, mas só 52% foram fiéis à documentação e 38% puderam ser usadas sem edição, e a conferência automática de fidelidade usada pela ferramenta, que compara números e nomes, mostrou-se incapaz de substituir a leitura humana.

A quarta é a própria *ferramenta*, com o código, os resultados e os gabaritos disponíveis num repositório público, de modo que a avaliação pode ser reproduzida com os mesmos projetos.

== Organização do texto

O Capítulo 2 apresenta os conceitos sobre os quais o trabalho se apoia: o modelo semântico do Power BI, as boas práticas de modelagem, a análise estática e o custo dos falsos positivos, os modelos de linguagem e a geração aumentada por recuperação, além das ferramentas existentes.

O Capítulo 3 descreve o método e a arquitetura da ferramenta: a leitura do arquivo `model.bim`, o critério de detectabilidade, as nove regras, o fluxo da auditoria, a base de documentação, a geração com citação obrigatória e o conjunto de avaliação.

O Capítulo 4 apresenta a avaliação: as medidas usadas, os resultados das regras, da recuperação e da geração, e o estudo de caso de um modelo de autoria própria.

O Capítulo 5 discute os resultados, as ameaças à validade da avaliação e os limites de escopo da ferramenta.

O Capítulo 6 conclui o trabalho e aponta os trabalhos futuros. Os apêndices trazem o catálogo das regras, a rubrica da avaliação das explicações e as instruções para reproduzir os resultados.
