# Teste do glossário na instrução da geração — protocolo

**Data:** 15/10/2026 · **Branch:** `revisao-monografia` · **Estatuto:** análise de erros
(o glossário foi escrito a partir dos erros dos mesmos 61 achados em que é medido; não
substitui o resultado oficial da geração, `geracao-2026-10-14.json`).

Este documento foi versionado **antes** de qualquer rodada com o glossário. Nada abaixo
muda depois de ver os textos gerados.

## Pergunta

Os erros sistemáticos da geração (Capítulo 4) vêm do limite do modelo
(`qwen2.5:7b-instruct`, Q4_K_M) ou da falta de especificação na instrução? Se um glossário
de termos na instrução de sistema reduz esses erros, a segunda explicação ganha peso.

## O que muda e o que fica igual

**Muda só a instrução de sistema:** `SISTEMA` de `core/analise/prompt.py` seguido do
glossário abaixo. **Fica igual:** modelo, temperatura, semente, esquema JSON, validação da
citação, os 61 achados e o contexto de cada um (âncora + complementares por BM25, que é
determinístico). O código de produção não muda: um invólucro do cliente do LLM troca a
mensagem de sistema antes do cache, e o cache, indexado pelo conteúdo completo, guarda as
respostas novas sem tocar nas originais.

### Glossário (texto exato acrescentado à instrução)

```
GLOSSÁRIO — use estes sentidos ao ler os trechos em inglês e ao escrever em português:
- compress, compression: comprimir, compressão — reduzir o espaço que os dados ocupam. Nunca traduza como "compreender".
- VertiPaq: o mecanismo que armazena os dados do modelo comprimidos em memória.
- calculated column: coluna calculada — coluna criada no modelo por uma fórmula DAX.
- BLANK: o valor vazio do DAX, que representa ausência de dado. Uma medida que devolve BLANK não é um erro: em geral é o comportamento desejado, porque os visuais omitem os grupos vazios.
- DAX: a linguagem das medidas, das colunas calculadas e das tabelas calculadas do modelo.
- Power Query: a ferramenta de preparação dos dados, cujas fórmulas são escritas na linguagem M, e não em DAX. Funções DAX como YEAR, FORMAT ou RELATED não existem no Power Query.
- denormalize: desnormalizar — juntar numa só tabela as tabelas de uma mesma dimensão; tabelas de fatos não entram nessa junção.
```

Cada entrada responde a um padrão de erro da rubrica original: "compreende"/"descompressão"
(PERF-001), BLANK tratado como defeito (DAX-001), sintaxe DAX no Power Query (PERF-001,
MOD-007), fato fundido com dimensões e "normalizada" no lugar de desnormalizada (MOD-006).
O ponto cego da MOD-003 (relacionar tabelas desconectadas de propósito) é da regra, não de
terminologia, e não tem entrada.

## Procedimento

1. **Rodada com glossário** sobre P1–P7, com cache, em `eval/geracao/auditorias-glossario/`.
   Achado que sair sem explicação (`sem_fundamentacao`) conta como "não utilizável" na
   versão com glossário.
2. **Reexecução da instrução original sem cache**, em `eval/geracao/auditorias-reexecucao/`,
   só para o indicador léxico (passo 5). Não é anotada.
3. **Planilha cega** `eval/gabarito/rubrica-glossario-P1-P7.xlsx`: as 61 explicações novas
   e 20 originais sorteadas, embaralhadas, com identificador opaco (`R01`…`R81`) e sem
   indicar a versão. Sorteio e ordem: `random.Random(20261015)`; primeiro `sample` de 20 ids
   originais em ordem alfabética, depois `shuffle` das 81 linhas. A chave (código → versão,
   achado) fica em `eval/geracao/glossario/chave.json`, fora do git até o fim da anotação.
   Instruções e itens da rubrica idênticos aos da avaliação original.
4. **Anotação** pelo Fred, sem abrir a chave.
5. **Medida.**
   - **Principal — utilizável como está**, pareado nos 61 achados: veredito original (CSV
     oficial de 14/10) × veredito da versão com glossário. Teste exato de McNemar, bilateral,
     sobre os pares discordantes.
   - **Secundárias:** pertinente, fiel e recomendação correta, pelo mesmo teste; todas por
     regra, com Wilson.
   - **Consistência do anotador:** nas 20 reanotadas, concordância simples e kappa de Cohen
     entre a primeira anotação e a reanotação, por item e para utilizável.
   - **Indicador léxico (descritivo):** nas 31 explicações da PERF-001, quantas contêm
     "compreend" ou "descompress" (sem diferenciar maiúsculas), na rodada original, na
     reexecução sem cache e na rodada com glossário. A reexecução estima quanto o número
     varia só pelo não determinismo do Ollama.

## Regra de decisão (fixada antes)

O glossário **melhora** a geração se a proporção de explicações utilizáveis subir e o
McNemar exato der p < 0,05. Caso contrário, o resultado é **inconclusivo** quanto a
utilizável, e os itens secundários são relatados sem decisão. Se a concordância do anotador
consigo mesmo em utilizável ficar abaixo de 0,80 nas 20 reanotadas, a comparação é declarada
frágil no texto, qualquer que seja o p.

## Limitações declaradas desde já

- Análise de erros: glossário escrito a partir dos erros que mede.
- Mesmo anotador da avaliação original, que conhece os textos originais; a mistura cega e a
  reanotação de 20 atenuam, sem eliminar.
- Diferenças entre as versões incluem a variação entre execuções do Ollama; o indicador
  léxico dá uma medida dela só para o erro de tradução.
- Fatos do glossário que não estejam nos trechos citados são julgados pela rubrica original
  (fiel = sustentado pelos trechos citados ou pelos fatos do achado).
