# Roteiro de demonstração — até 3 minutos

Antes de gravar: extraia o ZIP, abra o painel e teste o modo online. Não mostre pastas pessoais. Pode gravar tudo em casa no computador.

**0:00–0:20 | Problema e papel da automação**
“O PassoLivre apoia a organização de relatos sobre barreiras nas calçadas. Conferir cada endereço e organizar esses relatos manualmente é repetitivo. Nosso RPA faz a triagem em lote. Estes 15 relatos são fictícios para teste.”

**0:20–0:40 | Entrada**
Abra `data/ocorrencias.csv` em um editor ou Excel. Mostre as colunas, os 15 registros, o PL-001 repetido e os campos incompletos. “O CEP complementa o endereço; a referência ajuda a localizar o ponto.”

**0:40–1:25 | Execução real**
No painel, selecione “Consulta real · ViaCEP” e clique em Executar automação. Mostre a conclusão e um endereço completado. “O robô percorre o lote, valida campos e consulta a API. Reutiliza respostas para CEPs repetidos.”

**1:25–1:55 | Regras e integração com o MVP**
Mostre prioridade alta e filtre pendências e duplicatas. “Bloqueio total relatado gera prioridade para análise humana. O ID repetido é ignorado. CEP inválido ou não encontrado e campos faltantes ficam pendentes. O painel de gestão consome o JSON real gerado pelo robô.”

**1:55–2:35 | Falha e auditoria**
Troque para “Teste de falha” e execute (confirme a simulação). “Agora provocamos indisponibilidade da API para demonstrar resiliência. Há três tentativas e a falha é registrada; o lote continua.” Abra a auditoria e mostre uma tentativa e um item finalizado. Não diga que o ViaCEP caiu de verdade.

**2:35–2:55 | Fechamento**
“Python faz o processamento, a página local apresenta a fila e os logs permitem rastrear a execução. Não há envio à prefeitura. A automação independe do detector de Applied.”

Não apresente execução offline como chamada real. Se a internet estiver indisponível durante a gravação, diga que usa respostas previamente capturadas e mostre a identificação OFFLINE; idealmente registre também uma consulta real em outro momento.
