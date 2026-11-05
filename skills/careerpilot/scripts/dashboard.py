"""Local dashboard with public-feed discovery; no application submission API."""
import argparse
import hashlib
import json
import secrets
import sqlite3
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit
from job_search import SearchManager, rankings
from private_settings import Settings, deliver, send_telegram, telegram_chats
from toolkit import Workspace

ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'dashboard'
STATIC = {'': ('index.html', 'text/html'), 'app.js': ('app.js', 'text/javascript'),
          'style.css': ('style.css', 'text/css')}


def read_state(root):
    # mode=ro avoids creating a database or changing canonical state.
    db = sqlite3.connect((root / 'toolkit.sqlite3').as_uri() + '?mode=ro', uri=True, timeout=5)
    try:
        row = db.execute('SELECT value FROM state WHERE id=1').fetchone()
        if not row:
            raise ValueError('No saved workspace state')
        state = json.loads(row[0])
        if state.get('schema_version') != 1:
            raise ValueError('Unsupported workspace schema')
        return state
    finally:
        db.close()


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, root, port=8765):
        self.root = Path(root).expanduser().resolve()
        read_state(self.root)
        self.token = secrets.token_urlsafe(32)
        self.search = SearchManager(self.root)
        super().__init__(('127.0.0.1', port), DashboardHandler)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.url = f'{self.origin}/{self.token}/'


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Do not write session tokens, URLs, or candidate data to access logs.

    def respond(self, status, body, content_type='text/plain; charset=utf-8', filename=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        if filename:
            self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(filename, safe=''))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        server = self.server
        if self.headers.get('Host') != urlsplit(server.origin).netloc:
            return self.respond(403, 'Invalid dashboard host')
        origin = self.headers.get('Origin')
        if (origin and origin != server.origin) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self.respond(403, 'Cross-site access denied')
        parsed = urlsplit(self.path)
        prefix = f'/{server.token}/'
        if not parsed.path.startswith(prefix):
            return self.respond(404, 'Open the dashboard URL printed by the launcher.')
        route = parsed.path[len(prefix):]
        try:
            if route in STATIC:
                filename, mime = STATIC[route]
                return self.respond(200, (ASSETS / filename).read_bytes(), mime + '; charset=utf-8')
            if route == 'api/settings':
                return self.respond(200, json.dumps(Settings(server.root).public()), 'application/json')
            if route not in {'api/state', 'api/export', 'api/document'}:
                return self.respond(404, 'Not found')
            state = read_state(server.root)
            if route == 'api/state':
                return self.respond(200, json.dumps({'state': state, 'workspace': str(server.root),
                    'rankings': rankings(state), 'active_search': server.search.active}, ensure_ascii=False), 'application/json; charset=utf-8')
            if route == 'api/export':
                return self.respond(200, json.dumps(state, indent=2, ensure_ascii=False), 'application/json; charset=utf-8', 'job-workspace.json')
            query = parse_qs(parsed.query)
            job = state['jobs'].get(query.get('job', [''])[0], {})
            sha = query.get('sha', [''])[0]
            doc = next((d for d in job.get('documents', []) if d['sha256'] == sha), None)
            if not doc:
                return self.respond(404, 'Registered document not found')
            path = (server.root / doc['path']).resolve()
            if not path.is_relative_to(server.root / 'artifacts') or not path.is_file():
                return self.respond(404, 'Document missing or outside workspace artifacts')
            if path.stat().st_size > 25_000_000:
                return self.respond(409, 'Document changed; ask your agent to register it again')
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != doc['sha256']:
                return self.respond(409, 'Document changed; ask your agent to register it again')
            return self.respond(200, data, 'application/octet-stream', doc['original_name'])
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            return self.respond(503, 'Workspace unavailable. Check the workspace and refresh; no changes were made.')

    def do_POST(self):
        server = self.server
        action = self.path.removeprefix(f'/{server.token}/api/')
        if self.path not in {f'/{server.token}/api/{a}' for a in ('search','settings','telegram-test','telegram-chats','assistance-retry','assistance-resume','email-config','email-apply','email-dismiss')}:
            return self.respond(405, 'This action is not available from this dashboard.')
        if (self.headers.get('Host') != urlsplit(server.origin).netloc
                or self.headers.get('Origin') != server.origin
                or self.headers.get('X-CareerPilot-Request') != action
                or self.headers.get('Sec-Fetch-Site') == 'cross-site'):
            return self.respond(403, 'This action must be started from this dashboard.')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(415, 'Send a JSON request.')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                return self.respond(413, 'Request is too large or empty.')
            self.connection.settimeout(10)
            query = json.loads(self.rfile.read(size))
            if not isinstance(query, dict):
                raise ValueError('Request must be an object.')
            if action in {'email-config','email-apply','email-dismiss'}:
                result = Workspace(server.root).mutate(dict(query, op=action))
            elif action == 'settings':
                result = Settings(server.root).save(query)
            elif action == 'telegram-chats':
                result = telegram_chats(server.root, query.get('token', ''))
            elif action == 'telegram-test':
                send_telegram(server.root, 'CareerPilot test: phone notifications are connected. Open Chrome Remote Desktop when assistance is needed.')
                result = {'sent': True}
            elif action == 'assistance-retry':
                Workspace(server.root).mutate({'op':'assistance-retry', 'request_id':query.get('request_id')})
                result = deliver(server.root, query.get('request_id'))
            elif action == 'assistance-resume':
                result = Workspace(server.root).mutate({'op':'resume', 'job_id':query.get('job_id'), 'note':query.get('note')})
            else:
                result = server.search.start(query)
            return self.respond(202, json.dumps(result), 'application/json; charset=utf-8')
        except ValueError as exc:
            return self.respond(400, str(exc))
        except RuntimeError as exc:
            return self.respond(409, str(exc))
        except (OSError, sqlite3.Error):
            return self.respond(503, 'Could not complete this action. Check the workspace and try again.')

    def unsupported(self):
        self.respond(405, 'This action is not available from the dashboard.')

    do_PUT = unsupported
    do_DELETE = unsupported
    do_PATCH = unsupported


def serve(root, port=8765, open_browser=False):
    server = DashboardServer(root, port)
    print(json.dumps({'dashboard': server.url, 'workspace': str(server.root),
                      'mode': 'search-and-review', 'stop': 'Ctrl+C in this terminal'}), flush=True)
    try:
        if open_browser:
            webbrowser.open(server.url)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    serve(args.workspace, args.port, args.open)
