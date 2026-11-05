"""Local AI Job Toolkit. Python 3.10+, no third-party dependencies."""
import argparse
import csv
import io
import json
import re
import secrets
import sqlite3
import webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATES = ['Saved', 'Shortlisted', 'Preparing', 'Needs attention', 'Ready for review', 'Submitted', 'Interview', 'Rejected', 'Offer', 'Withdrawn']
DEFAULT_PROFILE = dict(name='', email='', location='', roles='', skills='', experience='', preferences='')
DEFAULT_SETTINGS = dict(provider='Unconfigured', model='', endpoint='', submission='Prepare only')

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

def initialize(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL, location TEXT, url TEXT, description TEXT, status TEXT NOT NULL, notes TEXT, created TEXT NOT NULL, updated TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, message TEXT NOT NULL, created TEXT NOT NULL)')
        for key, value in [('profile', DEFAULT_PROFILE), ('settings', DEFAULT_SETTINGS)]:
            db.execute('INSERT OR IGNORE INTO config VALUES (?,?)', (key, json.dumps(value)))

def skill_matches(profile, job):
    skills = list(dict.fromkeys(s.strip() for s in re.split(r'[,;\n]', profile.get('skills', '')) if s.strip()))
    text = ' '.join([job['title'], job['description'] or '']).casefold()
    found = [s for s in skills if re.search(r'(?<!\w)' + re.escape(s.casefold()) + r'(?!\w)', text)]
    return dict(score=round(len(found) * 100 / len(skills)) if skills else None, matched=found, unmatched=[s for s in skills if s not in found])

def make_server(path, port=8765):
    initialize(path)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, data, status=200, mime='application/json; charset=utf-8'):
            body = data.encode('utf-8') if isinstance(data, str) else json.dumps(data).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def trusted_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.trusted_host():
                return self.respond({'error': 'Invalid host'}, 403)
            route = urlparse(self.path).path
            if route == '/api/state':
                with connect(path) as db:
                    config = {r['key']: json.loads(r['value']) for r in db.execute('SELECT * FROM config')}
                    jobs = [dict(r) for r in db.execute('SELECT * FROM jobs ORDER BY id DESC')]
                    for job in jobs:
                        job.update(skill_matches(config['profile'], job))
                    activity = [dict(r) for r in db.execute('SELECT * FROM activity ORDER BY id DESC LIMIT 20')]
                return self.respond(dict(**config, jobs=jobs, activity=activity, states=STATES, token=token))
            if route == '/api/export':
                with connect(path) as db:
                    rows = list(db.execute('SELECT * FROM jobs ORDER BY id'))
                    out = io.StringIO(newline='')
                    fields = ['id', 'title', 'company', 'location', 'url', 'description', 'status', 'notes', 'created', 'updated']
                    writer = csv.writer(out)
                    writer.writerow(fields)
                    for row in rows:
                        writer.writerow([("'" + str(row[k])) if str(row[k] or '').lstrip().startswith(('=', '+', '-', '@')) else row[k] for k in fields])
                return self.respond(out.getvalue(), mime='text/csv; charset=utf-8')
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if route not in files:
                return self.respond({'error': 'Not found'}, 404)
            filename, mime = files[route]
            self.respond((ROOT / 'public' / filename).read_text(encoding='utf-8'), mime=mime)

        def do_POST(self):
            if not self.trusted_host() or self.headers.get('X-Toolkit-Token') != token:
                return self.respond({'error': 'Request not authorized. Reload the dashboard.'}, 403)
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 2_000_000:
                    raise ValueError('Request must be between 1 byte and 2 MB.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object.')
                route = urlparse(self.path).path
                with connect(path) as db:
                    message = ''
                    if route in ['/api/profile', '/api/settings']:
                        key = route.split('/')[-1]
                        defaults = DEFAULT_PROFILE if key == 'profile' else DEFAULT_SETTINGS
                        value = {k: str(data.get(k, v)).strip()[:30000] for k, v in defaults.items()}
                        if key == 'settings':
                            if value['submission'] != 'Prepare only':
                                raise ValueError('Automatic submission is not connected yet. Prepare only is available.')
                            if value['provider'] not in ['Unconfigured', 'Claude', 'OpenAI', 'Local model']:
                                raise ValueError('Unknown provider.')
                        db.execute('UPDATE config SET value=? WHERE key=?', (json.dumps(value), key))
                        message = f'{key.capitalize()} updated'
                    elif route == '/api/jobs':
                        title, company = str(data.get('title', '')).strip(), str(data.get('company', '')).strip()
                        if not title or not company:
                            raise ValueError('Job title and company are required.')
                        url = str(data.get('url', '')).strip()
                        if url and (urlparse(url).scheme not in ['https', 'http'] or not urlparse(url).netloc):
                            raise ValueError('Enter a full http or https job URL.')
                        if url and db.execute('SELECT 1 FROM jobs WHERE url=?', (url,)).fetchone():
                            raise ValueError('This job URL is already in your workspace.')
                        db.execute('INSERT INTO jobs (title,company,location,url,description,status,notes,created,updated) VALUES (?,?,?,?,?,?,?,?,?)', (title[:300], company[:300], str(data.get('location', ''))[:300], url[:3000], str(data.get('description', ''))[:80000], 'Saved', '', now(), now()))
                        message = f'Added {title[:100]} at {company[:100]}'
                    elif route == '/api/jobs/update':
                        status, notes = data.get('status'), str(data.get('notes', '')).strip()[:30000]
                        if status not in STATES:
                            raise ValueError('Unknown application status.')
                        if status == 'Needs attention' and not notes:
                            raise ValueError('Add a note explaining what needs attention.')
                        job = db.execute('SELECT * FROM jobs WHERE id=?', (data.get('id'),)).fetchone()
                        if not job:
                            raise ValueError('Job not found.')
                        db.execute('UPDATE jobs SET status=?,notes=?,updated=? WHERE id=?', (status, notes, now(), job['id']))
                        message = f'{job["company"]}: {status} (recorded manually)'
                    else:
                        return self.respond({'error': 'Not found'}, 404)
                    db.execute('INSERT INTO activity (message,created) VALUES (?,?)', (message, now()))
                self.respond({'ok': True})
            except (ValueError, TypeError, sqlite3.IntegrityError) as exc:
                self.respond({'error': str(exc)}, 400)
            except Exception:
                self.respond({'error': 'Could not save. Your existing records are unchanged.'}, 500)

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = make_server(ROOT / 'data' / 'toolkit.db', args.port)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'AI Job Toolkit: {url}', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
