#import "../abnt.typ": fonte

= Conclusão <cap-conclusao>

Este trabalho desenvolveu e avaliou uma ferramenta que audita projetos do Power BI no formato PBIP. A ferramenta lê a definição do modelo semântico no arquivo `model.bim`, aplica nove regras determinísticas, cada uma sustentada por uma passagem da documentação oficial da Microsoft, e usa um modelo de linguagem executado localmente para explicar cada achado, com a obrigação de citar a documentação recuperada. A divisão de papéis foi a decisão central: as regras decidem se um problema existe, e o modelo de linguagem apenas o explica.

== Respostas às perguntas da avaliação

A *primeira pergunta* era se as regras apontam os problemas certos. Contra um gabarito anotado em sete projetos públicos, as regras atingiram precisão de 0,88 e revocação de 0,88, e seis das nove não emitiram nenhum falso positivo. A única regra abaixo do limiar de precisão fixado no planejamento, a que aponta tabelas sem relacionamento, falhou em tabelas desconectadas de propósito; parte desses casos tinha sinal estrutural no arquivo e foi corrigida, e parte expõe um limite do que a definição do modelo permite decidir. A resposta é afirmativa, com a ressalva de que o número de casos por regra é pequeno.

A *segunda pergunta* era se a recuperação encontra a passagem que sustenta cada achado. Na medição que escolheu o método de busca, a passagem âncora apareceu entre os cinco primeiros resultados em todas as regras, num teste reconhecidamente facilitado pelo vocabulário das consultas. Mais importante, a decisão de pôr a passagem âncora sempre no contexto tornou a resposta independente da busca: todas as 61 explicações avaliadas citaram uma passagem pertinente.

A *terceira pergunta* era se a explicação gerada pode ser entregue sem edição. Aqui a resposta é negativa para o modelo usado: só 52% das explicações foram fiéis à documentação, e só 38% passaram nos três critérios da rubrica. Os erros concentraram-se em duas regras e seguiram padrões sistemáticos. A avaliação mostrou ainda que a verificação automática de números e nomes não detecta essas infidelidades, que são de sentido.

== Considerações finais

O resultado mais útil do trabalho talvez seja o mais simples de enunciar: numa ferramenta de auditoria que usa modelo de linguagem, a confiança deve morar na parte determinística. As regras, escolhidas por um critério explícito e avaliadas contra julgamento humano, entregaram achados confiáveis. A recuperação com a passagem âncora fixa entregou o fundamento certo. O modelo de linguagem local, com o fundamento nas mãos, ainda erra o suficiente para que as suas explicações precisem de revisão. A ferramenta, por isso, foi ajustada para dizer isso ao usuário, e a forma correta de usá-la é como apoio a um analista, que recebe achados confiáveis, a passagem da documentação que os sustenta e um rascunho de explicação a revisar.

O critério de detectabilidade mostrou que fazer menos regras, mas regras sustentáveis, é uma escolha defensável: das 20 a 25 regras previstas, restaram 9, e a regra mais promissora foi rejeitada com uma medição que mostrou por que a sua precisão não poderia ser estabelecida. Declarar esse limite, em vez de contorná-lo, é parte do resultado.

== Trabalhos futuros

Os resultados apontam caminhos concretos, em ordem aproximada de proximidade com o que já existe.

- *Melhorar a geração.* Os erros sistemáticos sugerem intervenções diretas: um glossário de termos técnicos na instrução, para evitar erros como "compreender" no lugar de "comprimir"; exemplos de explicação correta para as regras com mais erros; e a comparação com modelos maiores, locais ou não, medida pela mesma rubrica.
- *Verificar a fidelidade pelo sentido.* A conferência automática de números e nomes precisa de um complemento que avalie se a explicação é sustentada pelo trecho citado, cuja concordância com a leitura humana possa ser medida da mesma forma.
- *Corrigir a consulta da PERF-001*, que hoje atrai páginas de referência de funções, e medir de novo a pertinência dos trechos complementares.
- *Validar as correções das regras* MOD-003 e PERF-001 num projeto que as regras ainda não viram, e acrescentar um segundo anotador numa amostra, com medida de concordância entre anotadores.
- *Ampliar o conjunto de regras* pelo mesmo critério: regras sobre as consultas em Power Query M, como a conversão de texto em número sem cultura definida; as candidatas de DAX que aguardam passagem citável; e, com um analisador sintático completo do DAX, regras que dependem do contexto de avaliação das fórmulas.
- *Ampliar o que a ferramenta lê*: o formato TMDL, a entrada direta de arquivos PBIX e a camada de relatório. Ler o relatório permitiria, entre outras coisas, reavaliar a regra de colunas sem uso, rejeitada justamente por não ter acesso a ele.
- *Medir em vez de inferir o desempenho*, com estatísticas do modelo carregado, como o tamanho real das colunas, para priorizar os achados de desempenho.
- *Verificar na prática* se o Power BI Desktop grava sempre as expressões de segurança em nível de linha no `model.bim`.
