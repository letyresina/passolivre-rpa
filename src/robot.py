"""Triagem em lote: Python 3.10+, somente biblioteca padrão."""
import csv
import json
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {'id', 'cep', 'referencia', 'tipo', 'descricao', 'bloqueio_total'}
TYPES = {'buraco', 'desnivel', 'obstaculo', 'piso_tatil_danificado'}

class LookupFailure(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def normalize_cep(value):
    value = value.strip()
    if not re.fullmatch(r'[0-9]{8}|[0-9]{5}-[0-9]{3}', value):
        raise ValueError('CEP ausente ou formato inválido')
    return value.replace('-', '')


class ViaCEP:
    def __init__(self, mode='online', audit=None, opener=urlopen, sleeper=time.sleep):
        if mode not in {'online', 'demo', 'falha'}:
            raise ValueError('Modo inválido')
        self.mode, self.audit = mode, audit or (lambda **kw: None)
        self.opener, self.sleeper = opener, sleeper
        self.cache = {}
        self.snapshot = json.loads((ROOT / 'data/viacep_snapshot.json').read_text('utf-8')) if mode == 'demo' else {}

    def lookup(self, cep):
        if cep in self.cache:
            return self.cache[cep]
        if self.mode == 'demo':
            if cep not in self.snapshot['responses']:
                raise LookupFailure('CEP não está no conjunto de demonstração offline')
            result = dict(self.snapshot['responses'][cep])
        else:
            result = None
            for attempt in range(1, 4):
                try:
                    if self.mode == 'falha':
                        raise URLError('Indisponibilidade simulada')
                    req = Request(f'https://viacep.com.br/ws/{cep}/json/', headers={'User-Agent': 'PassoLivre-RPA/1.0'})
                    with self.opener(req, timeout=5) as response:
                        result = json.loads(response.read(65536).decode('utf-8'))
                    if not isinstance(result, dict):
                        raise ValueError('Resposta não é objeto JSON')
                    break
                except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                    self.audit(evento='consulta_falhou', tentativa=attempt, codigo=type(exc).__name__)
                    if attempt == 3:
                        raise LookupFailure('Consulta indisponível após 3 tentativas') from exc
                    self.sleeper(0.3 * attempt)
            self.sleeper(0.15)
        if result.get('erro') not in (True, 'true'):
            if not all(isinstance(result.get(k), str) and result[k] for k in ('cep', 'localidade', 'uf')):
                raise LookupFailure('Resposta da API incompleta')
            try:
                if normalize_cep(result['cep']) != cep:
                    raise LookupFailure('CEP retornado diverge do solicitado')
            except ValueError as exc:
                raise LookupFailure('CEP inválido na resposta') from exc
        self.cache[cep] = result
        return result


def process(input_path=None, output_dir=None, logs_dir=None, mode='online', client=None):
    input_path = Path(input_path or ROOT / 'data/ocorrencias.csv')
    output_dir = Path(output_dir or ROOT / 'output')
    logs_dir = Path(logs_dir or ROOT / 'logs')
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    events = []
    audit_path = logs_dir / f'{run_id}.jsonl'
    def audit(**event):
        item = {'data_hora': now(), 'execucao': run_id, **event}
        events.append(item)
        with audit_path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    audit(evento='inicio', modo=mode)
    try:
        with input_path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter=';', strict=True)
            if not FIELDS.issubset(reader.fieldnames or []):
                raise ValueError('Cabeçalho CSV inválido: faltam colunas obrigatórias')
            rows = list(reader)
        if not rows or len(rows) > 1000:
            raise ValueError('O lote deve ter entre 1 e 1000 registros')
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        audit(evento='falha_lote', codigo=type(exc).__name__, mensagem='Arquivo ausente, ilegível ou inválido; resultado anterior preservado')
        raise ValueError('Não foi possível ler o lote. Confira arquivo, colunas e codificação UTF-8.') from exc
    api = client or ViaCEP(mode=mode, audit=audit)
    results, seen = [], set()
    for index, row in enumerate(rows, 1):
        item = {'linha': index, 'id': (row.get('id') or '').strip(), 'status': 'pendente', 'motivo': '',
                'prioridade': '', 'origem_endereco': '', 'cep': (row.get('cep') or '').strip(),
                'tipo': (row.get('tipo') or '').strip(), 'referencia': (row.get('referencia') or '').strip(),
                'descricao': (row.get('descricao') or '').strip()}
        try:
            if None in row or any(v is None for v in row.values()):
                raise ValueError('Quantidade de colunas inválida')
            if not re.fullmatch(r'PL-[0-9]{3}', item['id']):
                raise ValueError('Identificador inválido; use PL-001')
            if item['id'] in seen:
                item.update(status='duplicado', motivo='ID repetido no lote; primeira ocorrência prevalece')
            else:
                # Reserva o ID na primeira aparição, mesmo que ela tenha pendência.
                seen.add(item['id'])
                cep = normalize_cep(item['cep'])
                if item['tipo'] not in TYPES:
                    raise ValueError('Tipo de ocorrência inválido')
                if len(item['descricao']) < 10:
                    raise ValueError('Descrição ausente ou muito curta (mínimo 10 caracteres)')
                if not item['referencia']:
                    raise ValueError('Falta número ou ponto de referência para localizar a ocorrência')
                blocked = (row.get('bloqueio_total') or '').strip().lower()
                if blocked not in {'sim', 'nao'}:
                    raise ValueError('Bloqueio total deve ser sim ou nao')
                address = api.lookup(cep)
                item['origem_endereco'] = 'snapshot offline' if mode == 'demo' else 'ViaCEP online'
                if address.get('erro') in (True, 'true'):
                    raise ValueError('CEP não encontrado no ViaCEP')
                item.update(cep=address['cep'], logradouro=address.get('logradouro', ''),
                            bairro=address.get('bairro', ''), cidade=address['localidade'], uf=address['uf'])
                if not item['logradouro']:
                    raise ValueError('CEP sem logradouro; é preciso informar a rua para revisão')
                item.update(status='apto', motivo='Pronto para análise humana',
                            prioridade='alta' if blocked == 'sim' else 'normal')
        except ValueError as exc:
            item['motivo'] = str(exc)
        except LookupFailure as exc:
            item.update(status='falha_consulta', motivo=str(exc), origem_endereco='falha simulada' if mode == 'falha' else 'consulta falhou')
        results.append(item)
        # Somente identificadores válidos no log, sem texto livre nem endereços.
        audit(evento='item_finalizado', linha=index, id=item['id'] if re.fullmatch(r'PL-[0-9]{3}', item['id']) else 'invalido',
              status=item['status'], motivo=item['motivo'])
    counts = Counter(x['status'] for x in results)
    summary = {'total': len(results), **{s: counts[s] for s in ('apto', 'pendente', 'duplicado', 'falha_consulta')},
               'prioridade_alta': sum(x['prioridade'] == 'alta' for x in results)}
    audit(evento='fim', resumo=summary)
    report = {'execucao': run_id, 'gerado_em': now(), 'modo': mode,
              'aviso': 'Ocorrências fictícias. Não representam problemas reais nos endereços. Nenhum envio a órgãos públicos.',
              'resumo': summary, 'itens': results, 'eventos': events}
    # Snapshot substituído atomicamente: reexecutar não acumula ocorrências.
    temporary = output_dir / f'.{run_id}.tmp'
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(output_dir / 'resultado.json')
    return report
