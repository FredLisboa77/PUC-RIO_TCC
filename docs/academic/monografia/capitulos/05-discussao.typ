#import "../abnt.typ": fonte

= Discussão e ameaças à validade <cap-discussao>

Este capítulo interpreta os resultados do Capítulo 4, examina o que pode tê-los distorcido e delimita o que a ferramenta não faz. A intenção é que o leitor saiba exatamente até onde cada número vale.

== O que os resultados mostram <sec-o-que-mostram>

Lidos em conjunto, os resultados contam uma história coerente sobre as três camadas da ferramenta.

A *detecção* se sustenta. Seis das nove regras não emitiram nenhum falso positivo, e a precisão total, de 0,88, ficou acima do limiar de 0,7 fixado no planejamento. O único caso abaixo do limiar, a MOD-003, falhou num ponto específico e identificável: tabelas que o Power BI ou o autor criam desconectadas de propósito. Quatro dos seis erros tinham sinal estrutural no arquivo e foram corrigidos; os outros dois expõem um limite real do que se pode decidir lendo apenas a definição do modelo. Esse resultado é o que o critério de detectabilidade prometia: regras poucas, mas confiáveis, com os casos de erro explicados e não escondidos.

A *recuperação* não é o gargalo. A decisão de pôr sempre a passagem âncora da regra como primeiro trecho do contexto garantiu que o modelo de linguagem tivesse, em todos os achados, a passagem que sustenta o problema, e a leitura humana confirmou que todas as 61 explicações citaram uma passagem pertinente. A escolha do tipo de busca, que ocupou boa parte do projeto, afetou apenas os trechos complementares, e ali o defeito que mais pesou foi a construção da consulta de uma regra, não o tipo de busca.

A *geração* é o ponto fraco. Com a passagem certa nas mãos, o modelo de 7 bilhões de parâmetros escreveu uma explicação fiel em pouco mais da metade dos casos, e só pouco mais de um terço das explicações pode ser entregue sem edição. Os erros não são aleatórios: concentram-se em duas regras e repetem padrões, como o erro de tradução de "comprimir" e a leitura invertida da recomendação sobre o valor vazio. Isso tem duas leituras. A pessimista é que um modelo local desse porte ainda não redige explicações técnicas confiáveis sem supervisão. A útil é que erros sistemáticos são tratáveis: um glossário de termos na instrução, exemplos de resposta correta para as regras mais problemáticas ou um modelo maior são caminhos concretos, discutidos no Capítulo 6.

Por fim, a avaliação mostrou que a verificação automática da fidelidade, que confere números e nomes, não substitui a leitura humana: as infidelidades reais são de sentido. Esse resultado mudou a própria ferramenta, que passou a avisar o usuário de que a ausência de alerta não garante a correção do texto. A consequência prática é que a ferramenta deve ser usada como apoio a um analista, que revisa as explicações, e não como um auditor autônomo. O achado e a recomendação padrão de cada regra, que não dependem do modelo de linguagem, são a parte em que se pode confiar sem revisão.

== Ameaças à validade <sec-ameacas>

Uma _ameaça à validade_ é qualquer fator que possa tornar uma conclusão do estudo incorreta ou menos geral do que parece. A literatura de engenharia de software experimental organiza essas ameaças em quatro tipos @wohlin2012. A validade de _construto_ pergunta se as medidas medem o que se diz que medem. A validade _interna_ pergunta se o resultado se deve ao que se estudou ou a outro fator, como um viés na anotação. A validade _externa_ pergunta até onde o resultado se generaliza para além dos casos estudados. A validade de _conclusão_ pergunta se a análise dos dados sustenta as conclusões tiradas. As subseções seguintes examinam cada uma.

=== Validade de construto

A precisão de uma regra depende do que se aceita como violação. Para que o julgamento não fosse uma questão de gosto, o anotador julgou cada candidato contra a pergunta da passagem âncora da regra, e não contra a sua opinião sobre boas práticas. A precisão medida é, portanto, a precisão em relação ao que a documentação da Microsoft recomenda; quem discordar da documentação num caso concreto pode discordar do veredito.

A medida que escolheu o método de busca tem um viés conhecido: as consultas de avaliação foram montadas com os termos da própria regra, os mesmos que aparecem na passagem âncora. Isso facilita a tarefa e produziu o efeito teto descrito no Capítulo 4. O acerto de 1,00 entre os cinco primeiros resultados mede a recuperação dado o vocabulário da regra, e não a capacidade de responder a uma pergunta livre de um usuário.

O item "utilizável como está" condensa três julgamentos num só, e um "não" em qualquer item basta para recusar a explicação. É uma régua deliberadamente exigente: uma explicação com uma única palavra mal traduzida conta como não utilizável, embora um leitor atento ainda pudesse aproveitá-la. A proporção de 0,38 deve ser lida como a fração de explicações que dispensam qualquer edição, e não como a fração de explicações úteis.

=== Validade interna

A ameaça mais séria é o *anotador único*. O gabarito das regras e a rubrica da geração foram feitos pelo autor da ferramenta, sem um segundo anotador e, portanto, sem medida de concordância entre anotadores. O protocolo previa um segundo anotador às cegas em dois dos sete projetos; a decisão de não fazê-lo foi tomada e registrada, e a limitação é declarada aqui. Três cuidados a atenuam, sem eliminá-la. A anotação foi cega: a planilha listava todos os candidatos sem indicar quais a ferramenta marcara, e a planilha da rubrica não mostrava nenhum dos sinais automáticos. A justificativa foi obrigatória nos vereditos negativos e indeterminados. E os julgamentos foram conferidos contra a documentação.

Ainda assim, houve *contaminação*. Antes de o gabarito ser montado, os achados das regras em P1 a P7 já tinham sido vistos, e parte deles revista, durante o desenvolvimento. Ver a saída da ferramenta antes de anotar tende a favorecê-la. O protocolo respondeu congelando as regras numa marca de versão, mas a marca foi criada no fim da anotação, e não no início; como nenhuma regra mudou no intervalo, ela marca o código efetivamente medido.

Depois da primeira medição, 12 julgamentos foram revistos com base na documentação. As revisões foram registradas, cada uma com o motivo e o julgamento original, e andaram nos dois sentidos: algumas a favor da ferramenta, como as três divisões protegidas da DAX-001, e outras contra, como a tabela de negócio sem relacionamento da MOD-003. Mesmo documentadas, revisões feitas depois de ver o resultado são uma ameaça e ficam declaradas.

As correções da MOD-003 e da PERF-001 foram motivadas pelos próprios casos de teste. Por isso o seu efeito foi relatado como análise de erros, e não como resultado; o resultado oficial é o das regras congeladas. Validar as correções exigiria anotar um projeto que as regras ainda não viram, o que não foi feito.

Há ainda uma ameaça sutil na construção do gabarito. Os candidatos que o anotador julgou foram listados a partir do mesmo analisador do `model.bim` que alimenta as regras. Um objeto que o analisador não lê fica de fora dos dois lados, e um eventual problema nele não aparece nem como acerto nem como erro.

Na recuperação, a regra de decisão sobre o tipo de busca usou todas as 70 consultas, das quais as 9 consultas por regra pesam cerca de 41% da média. Considerando só as consultas por achado, que são as que a ferramenta de fato faz, a busca densa teria vencido. A regra foi fixada antes da medição e mantida; a divergência fica registrada como uma escolha que poderia ter sido outra.

=== Validade externa

Os sete projetos avaliados são amostras públicas da Microsoft, escolhidas pela licença aberta e pela reprodutibilidade. Amostras feitas para demonstrar o produto podem ser mais limpas que modelos corporativos reais, o que reduz o número de achados e pode favorecer a precisão.

O número de casos por regra é pequeno. A MOD-001 e a MOD-007 tiveram um achado cada; a MOD-002 e a MOD-005, nenhum. Os intervalos de Wilson do Capítulo 4 mostram o quanto isso limita as conclusões por regra: para essas regras, a avaliação mostra apenas que elas não erraram nos poucos casos que encontraram. Além disso, a PERF-003 responde por 16 dos 46 achados confirmados, e a PERF-001 por metade das explicações avaliadas, de modo que os números agregados refletem sobretudo essas duas regras.

A geração foi avaliada com um único modelo de linguagem, de 7 bilhões de parâmetros, quantizado, numa única GPU de 6 GB. Os resultados não se estendem a modelos maiores, nem a outros modelos do mesmo porte. A base de documentação foi coletada em outubro de 2026; a documentação do Microsoft Learn é atualizada continuamente, e uma passagem âncora pode mudar ou sair do ar.

=== Validade de conclusão e reprodutibilidade

As proporções foram apresentadas com intervalos de confiança, e nenhuma conclusão do trabalho depende de uma diferença pequena entre duas proporções. Onde a diferença era pequena, como na escolha da busca, a decisão foi tomada por uma regra fixada antes e declarada como tal.

A reprodutibilidade tem uma limitação própria: o Ollama não é determinístico, mesmo com temperatura 0 e semente fixa. Duas execuções sobre o mesmo projeto produzem os mesmos achados e o mesmo número de explicações, mas textos e algumas citações diferentes. Para que a avaliação pudesse ser conferida, as respostas avaliadas foram guardadas em cache, e repetir a rodada reproduz exatamente os textos julgados. Os projetos P1 a P7 são públicos, e os vereditos, os resultados e o código de medição estão versionados no repositório; os textos do Microsoft Learn usados como contexto não estão, porque os termos de uso do site não permitem redistribuí-los, mas podem ser coletados de novo pelo código do projeto. O P8 não pode ser reproduzido por terceiros, e por isso nenhuma métrica depende dele.

== Limites de escopo <sec-escopo>

Além das ameaças à validade, a ferramenta tem limites deliberados de escopo, definidos no planejamento e mantidos até o fim.

- *Formato do modelo.* A ferramenta lê só o `model.bim`, em TMSL. Projetos salvos em TMDL e arquivos PBIX precisam ser salvos antes como PBIP em TMSL. O próprio recurso de projetos do Power BI Desktop ainda está em pré-visualização @learn-pbip.
- *Camada de relatório.* As páginas e os visuais não são lidos. Por isso nenhuma regra pode afirmar que uma coluna não é usada, como mostrou a rejeição da PERF-005, e problemas próprios do relatório, como o excesso de visuais numa página, não são detectados.
- *Regras de Power Query M.* O grupo de regras sobre as consultas em M saiu do produto mínimo, e nenhuma regra examina a preparação dos dados.
- *DAX dependente de contexto.* Sem um analisador sintático completo do DAX, as regras que dependem do contexto de avaliação de uma fórmula ficaram de fora, porque uma heurística nesses casos erraria com frequência.
- *Medidas em tempo de execução.* A ferramenta não mede o tamanho real das colunas nem o tempo das consultas, o que exigiria carregar o modelo com os dados; as regras de desempenho apontam riscos conhecidos, não lentidão medida.
- *Segurança em nível de linha.* A ferramenta lê as expressões de filtro dos papéis de segurança, mas não foi verificado na prática se o Power BI Desktop sempre as grava no `model.bim`.
