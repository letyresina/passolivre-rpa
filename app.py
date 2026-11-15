"""Servidor local do painel de gestão e entrada CLI do robô."""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from src.robot import ROOT, process

LOCK = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200, content_type='application/json; charset=utf-8'):
        if not isinstance(data, bytes):
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/':
            return self.reply((ROOT / 'assets/painel.html').read_bytes(), content_type='text/html; charset=utf-8')
        if path == '/api/result':
            output = ROOT / 'output/resultado.json'
            return self.reply(json.loads(output.read_text('utf-8')) if output.exists() else {'itens': [], 'resumo': {}, 'modo': 'sem execução'})
        return self.reply({'erro': 'Rota não encontrada'}, 404)

    def do_POST(self):
        # Restringe execução ao painel local. Não serve o diretório do computador.
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        if host not in allowed or self.headers.get('Origin') not in {None, f'http://{host}'} or self.headers.get('X-PassoLivre') != 'painel':
            return self.reply({'erro': 'Origem não autorizada'}, 403)
        if self.path != '/api/run':
            return self.reply({'erro': 'Rota não encontrada'}, 404)
        if not LOCK.acquire(blocking=False):
            return self.reply({'erro': 'Uma execução já está em andamento'}, 409)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 1024:
                raise ValueError('Requisição inválida')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or payload.get('modo') not in {'online', 'demo', 'falha'}:
                raise ValueError('Modo inválido')
            return self.reply(process(mode=payload['modo']))
        except (ValueError, OSError):
            return self.reply({'erro': 'Execução não concluída. Confira o CSV e a pasta logs. O resultado anterior foi preservado.'}, 400)
        finally:
            LOCK.release()

    def log_message(self, fmt, *args):
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PassoLivre RPA: gestão de ocorrências')
    parser.add_argument('--processar', action='store_true', help='Processa sem abrir o painel')
    parser.add_argument('--modo', choices=['online', 'demo', 'falha'], default='online')
    parser.add_argument('--porta', type=int, default=8765)
    parser.add_argument('--sem-navegador', action='store_true')
    args = parser.parse_args()
    if args.processar:
        try:
            result = process(mode=args.modo)
        except (ValueError, OSError) as exc:
            parser.exit(1, f'Falha: {exc}\n')
        print(json.dumps(result['resumo'], ensure_ascii=False, indent=2))
    else:
        with ThreadingHTTPServer(('127.0.0.1', args.porta), Handler) as server:
            print(f'PassoLivre em http://127.0.0.1:{args.porta} — Ctrl+C para encerrar', flush=True)
            if not args.sem_navegador:
                webbrowser.open(f'http://127.0.0.1:{args.porta}')
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print('\nPainel encerrado.')
