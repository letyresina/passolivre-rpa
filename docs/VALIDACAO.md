# Evidências de validação

## Resultado funcional

- Consulta real ao ViaCEP executada para o lote completo; saída em `evidencia_online.json`.
- Contagem observada online: 15 lidos; 10 aptos; 4 pendentes; 1 duplicado; 0 falhas; 3 com prioridade alta.
- Modo offline reproduziu os mesmos totais usando respostas capturadas, sem chamadas externas.
- 8 testes automatizados aprovados (comando: `python -m unittest discover -s tests -v`).
- Integração HTTP local: GET `/` 200; POST `/api/run` no modo demo retornou os totais; GET `/api/result` consumiu os 15 itens gerados.
- Requisição com origem externa rejeitada com HTTP 403; modo inválido rejeitado com HTTP 400.
- Modo de falha provocado via endpoint: 15 lidos; 0 aptos; 3 pendentes; 1 duplicado; 11 falhas de consulta. Saída em `evidencia_falha.json`.
- JavaScript executado em DOM simulado: renderização de 15 linhas, filtro com 4 pendências e botão de execução/atualização funcionaram.

## Limites desta verificação

Não foi possível abrir o Chromium neste ambiente devido à restrição de criação de sockets do navegador. Portanto não há captura visual do painel nem validação visual em navegador real. Os endpoints e a lógica de interação foram testados separadamente. Abra no computador antes de gravar e confira a apresentação.

O PDF técnico foi renderizado e inspecionado visualmente em seis páginas. Os nomes completos, RMs e links da entrega ainda precisam ser preenchidos. Não foi realizada publicação no GitHub nem envio no Teams.
