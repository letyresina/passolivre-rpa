# PDD - Processo de triagem

Início: operador inicia a execução local. Entrada: CSV UTF-8 com 15 relatos fictícios.

1. Ler e validar cabeçalho, codificação e tamanho do lote. Se falhar, registrar falha e preservar resultado anterior.
2. Para cada linha (laço sequencial), validar ID. ID já visto: marcar duplicado. A primeira aparição prevalece.
3. Validar CEP, tipo, descrição, referência e bloqueio total. Falha de regra: marcar pendente, registrar e continuar.
4. Consultar ViaCEP usando HTTPS (somente CEP). Cache em memória evita consulta repetida. Até 3 tentativas com timeout e espera crescente para falhas transitórias.
5. Após esgotar tentativas: marcar falha_consulta e continuar. CEP não encontrado ou sem rua: pendente.
6. Registro validado e com rua: apto para análise humana. Bloqueio total relatado: prioridade alta; demais: normal.
7. Auditar cada linha. Ao fim, calcular totais e substituir atomicamente resultado.json.
8. O painel local consome o resultado via /api/result e oferece filtros de situação. Fim.

Saídas: snapshot JSON do lote e arquivo JSONL de auditoria por execução. Reexecutar substitui a fila, sem duplicar o armazenamento; histórico técnico permanece nos logs.

O arquivo processo.bpmn é BPMN 2.0 descritivo, com diagrama DI. A atividade com marcador de múltiplas instâncias representa o processamento sequencial das linhas; regras internas são detalhadas acima. Não é um fluxo para executar em motor BPMN.
