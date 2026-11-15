# PassoLivre RPA — Triagem de ocorrências de acessibilidade

Automação acadêmica em Python que recebe um lote de denúncias fictícias, consulta endereços no ViaCEP, verifica os dados e disponibiliza a fila de análise no painel local de gestão do PassoLivre. Independente do detector de Applied: não requer modelo de IA nem deploy.

**Dados de demonstração:** as 15 ocorrências e referências são inventadas. Os CEPs e endereços são reais e não representam locais com problemas confirmados. Nenhum relato é enviado a órgão público. Prioridade alta significa prioridade de análise, não urgência oficial ou diagnóstico técnico.

## Equipe

- **Leticia Resina** — RM 98069
- **Sabrina Flores** — RM 550781
- **Gabriel Riqueto** — RM 98685

## Comece aqui

1. Instale **Python 3.10 ou superior** no computador. Não há pacotes para instalar com pip.
2. Extraia o ZIP inteiro. Não execute arquivos dentro do ZIP.
3. No Windows, abra `iniciar_windows.bat`. Ou, no terminal, na pasta do projeto: `python app.py` (no macOS/Linux, use `python3 app.py`).
4. O navegador abre em **http://127.0.0.1:8765**. Se não abrir, copie esse endereço para o navegador no mesmo computador.
5. Escolha **Consulta real · ViaCEP** e clique em **Executar automação**. É preciso internet; o lote pode demorar em caso de novas tentativas.
6. Veja os endereços, filtre as pendências e abra a auditoria no final do painel.
7. Para encerrar, use Ctrl+C no terminal.

Se a porta estiver ocupada, execute `python app.py --porta 8766`.

O painel é local; não abre no celular pelo endereço do computador. O ZIP deve ser extraído e executado em um computador com Python.

## Processo manual substituído

Antes: consultar individualmente cada CEP, copiar rua/bairro/cidade, conferir campos e IDs repetidos e organizar a fila em uma planilha. Depois: iniciar uma execução e revisar apenas o resultado da triagem. O arquivo CSV é a entrada simulada de um canal de relatos; sua criação não é uma funcionalidade de Applied.

## Regras e 15 registros

| Linhas do CSV (sem cabeçalho) | Cenário | Resultado esperado com API disponível |
|---|---|---|
| 1–10 | Registros completos, com 5 CEPs distintos | 10 aptos; 3 com prioridade alta |
| 11 | Repetição de PL-001 | 1 duplicata ignorada |
| 12 | CEP vazio | Pendente |
| 13 | CEP com letras | Pendente |
| 14 | CEP 99999999, não encontrado | Pendente |
| 15 | Sem descrição | Pendente |

Total esperado: **15 lidos, 10 aptos, 4 pendentes, 1 duplicado, 0 falhas de consulta**. A contagem online depende da disponibilidade e dos dados atuais do serviço.

- Campos: `id;cep;referencia;tipo;descricao;bloqueio_total` (CSV UTF-8, separador ponto e vírgula).
- ID: PL-001 até PL-999. A primeira aparição do ID prevalece, mesmo se tiver pendência; os seguintes são duplicados. Não usamos somente CEP para deduplicar, porque vários problemas podem existir na mesma rua.
- CEP: oito dígitos ou formato 00000-000. Consulta somente CEPs válidos.
- Tipo: `buraco`, `desnivel`, `obstaculo` ou `piso_tatil_danificado`. Presença de piso tátil por si só não é defeito.
- Descrição: mínimo de 10 caracteres. Referência (número ou ponto de referência) obrigatória; os exemplos são fictícios.
- Bloqueio total: `sim` sinaliza prioridade `alta`, `nao` sinaliza `normal`; somente registros aptos recebem prioridade.
- CEP sem logradouro fica pendente para informar a rua. O CEP não oferece o ponto exato nem confirma a veracidade do relato.
- O robô não verifica se a referência está fisicamente na rua consultada e não conclui se a calçada está acessível. A decisão final é humana.

## Arquitetura e integração verificável

`data/ocorrencias.csv` → `src/robot.py` → consulta HTTPS ao ViaCEP → `output/resultado.json` → endpoint local `/api/result` → `assets/painel.html`.

O painel é o componente de gestão do MVP para esta entrega. Ele lê o resultado real do robô; não é uma captura ou tela com números fixos. Não há integração implementada com o site de Applied: os dois componentes compartilham o tema PassoLivre e têm execução independente.

## Exceções e recuperação

- API: timeout de 5 segundos por tentativa e até 3 tentativas com espera crescente; falha vira `falha_consulta` e o lote continua. Reexecute após recuperar a rede.
- Respostas válidas são reutilizadas em cache durante o lote, evitando chamadas repetidas. Não existe fallback silencioso para dados salvos.
- Erro de CEP inexistente vira pendência, não falha de rede.
- Arquivo ausente, cabeçalho incorreto, codificação inválida ou lote vazio interrompem a execução com log; o resultado anterior é preservado.
- Reexecuções substituem o snapshot de resultado, sem acumular registros; logs de cada execução têm identificadores únicos.
- Dados de entrada não são alterados. A escrita final do JSON é atômica.

## Modos de execução

- **online**: consulta real; é o modo recomendado para gravar a integração com a API.
- **demo**: usa `data/viacep_snapshot.json`, com respostas previamente capturadas e origem/data registradas; interface mostra OFFLINE. Não é uma consulta real naquele momento.
- **falha**: provoca indisponibilidade antes de cada consulta, sem fazer requisições; demonstra exceções e logs. Esperado: 11 falhas de consulta, 3 pendências de validação, 1 duplicata.

Sem painel: `python app.py --processar --modo online`.
Para reproduzir sem internet: `python app.py --processar --modo demo`.

## Testes

`python -m unittest discover -s tests -v`

Os testes usam respostas controladas para repetibilidade. Cobrem lote com 15 itens, regras, duplicidade, reexecução, recuperação na terceira tentativa, falha de API sem interromper o lote, CSV ausente/inválido, preservação do resultado anterior e logs sem endereço/texto livre.
As evidências verificadas nesta preparação estão em `docs/VALIDACAO.md`.

## Segurança e LGPD

Sem nomes de denunciantes, e-mails, telefones, imagens ou credenciais. O ViaCEP recebe apenas o CEP; descrições e referências ficam no computador. Os logs contêm ID técnico, linha, horário UTC, status e mensagens controladas. O servidor escuta somente 127.0.0.1 e não lista arquivos do computador. Não há uso de shell pelo servidor nem entrada de URL arbitrária. Dados reais podem ser pessoais ou sensíveis pelo contexto; esta versão é demonstrativa, sem autenticação, e não deve ser publicada como serviço de produção.

## Estrutura

- `app.py`: servidor local e CLI.
- `src/robot.py`: validação, consulta, triagem, auditoria e saída.
- `data/`: CSV com 15 itens e snapshot explicitamente offline.
- `assets/painel.html`: componente de gestão que consome o resultado.
- `docs/`: processo, BPMN, roteiro, evidências e guia técnico.
- `logs/`: amostra auditável e logs gerados.
- `output/`: resultado mais recente para o painel.
- `tests/`: testes automatizados.

## Referência externa

ViaCEP: https://viacep.com.br/ — endpoint `https://viacep.com.br/ws/{cep}/json/`. A documentação informa erro HTTP 400 para formato inválido e campo `erro` para CEP não encontrado. Respeite o serviço: lote pequeno, cache em memória e sem consultas massivas.
