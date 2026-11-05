import hashlib
import http.client
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from test_skill import ROOT, load, toolkit

dashboard = load('dashboard', ROOT / 'skills' / 'careerpilot' / 'scripts' / 'dashboard.py')


class DashboardTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.ws = toolkit.Workspace(Path(self.temp.name) / 'private')
        self.ws.initialize()
        self.server = dashboard.DashboardServer(self.ws.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.prefix = '/' + self.server.token + '/'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def get(self, route, method='GET', headers=None, prefix=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, (self.prefix if prefix else '') + route, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_live_state_reads_same_workspace_without_writes(self):
        initial = hashlib.sha256(self.ws.db_path.read_bytes()).hexdigest()
        status, headers, raw = self.get('api/state')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['state']['profile'], {})
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(hashlib.sha256(self.ws.db_path.read_bytes()).hexdigest(), initial)
        self.ws.mutate({'op':'profile-save', 'profile':{'name':'Synthetic Candidate'}})
        self.assertEqual(json.loads(self.get('api/state')[2])['state']['profile']['name'], 'Synthetic Candidate')

    def test_token_host_and_cross_site_protection(self):
        self.assertEqual(self.get('/api/state', prefix=False)[0], 404)
        self.assertEqual(self.get('api/state', headers={'Host':'external.example'})[0], 403)
        self.assertEqual(self.get('api/state', headers={'Origin':'https://external.example'})[0], 403)
        self.assertEqual(self.get('api/state', headers={'Sec-Fetch-Site':'cross-site'})[0], 403)
        self.assertEqual(self.get('api/state', headers={'Origin':self.server.origin})[0], 200)

    def test_static_assets_are_allowlisted_and_have_csp(self):
        for route in ['', 'app.js', 'style.css']:
            status, headers, body = self.get(route)
            self.assertEqual(status, 200)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            self.assertNotIn("'unsafe-inline'", headers['Content-Security-Policy'])
            self.assertTrue(body)
        for route in ['../toolkit.sqlite3','%2e%2e/toolkit.sqlite3','api/../toolkit.sqlite3','toolkit.sqlite3']:
            self.assertEqual(self.get(route)[0], 404)

    def test_mutations_are_not_available(self):
        for method in ['POST','PUT','PATCH','DELETE']:
            self.assertEqual(self.get('api/state', method)[0], 405)
        self.assertEqual(self.ws.read()['profile_revision'], 0)

    def test_registered_document_download_and_tamper_detection(self):
        jid = self.ws.mutate({'op':'job-add','title':'Synthetic Role','company':'Fixture','description':'Test','source':'Fixture','url':'https://example.invalid/job'})['job_id']
        source = Path(self.temp.name) / 'resume.html'
        source.write_text('<script>test()</script>', encoding='utf-8')
        self.ws.mutate({'op':'document-add','job_id':jid,'kind':'resume','path':str(source)})
        doc = self.ws.read()['jobs'][jid]['documents'][0]
        route = f'api/document?job={jid}&sha={doc["sha256"]}'
        status, headers, body = self.get(route)
        self.assertEqual(status, 200)
        self.assertEqual(body, source.read_bytes())
        self.assertEqual(headers['Content-Type'], 'application/octet-stream')
        self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
        (self.ws.root/doc['path']).write_text('tampered',encoding='utf-8')
        self.assertEqual(self.get(route)[0],409)
        self.assertEqual(self.get('api/document?job=unknown&sha=../../toolkit.sqlite3')[0],404)

    def test_export_and_unavailable_database(self):
        status, headers, raw = self.get('api/export')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), self.ws.read())
        self.assertIn('attachment;',headers['Content-Disposition'])
        self.ws.db_path.rename(self.ws.root/'moved.sqlite3')
        self.assertEqual(self.get('api/state')[0], 503)
        self.assertFalse(self.ws.db_path.exists())

    def test_missing_workspace_is_not_created(self):
        with self.assertRaises(sqlite3.OperationalError):
            dashboard.DashboardServer(Path(self.temp.name)/'missing',0)
        self.assertFalse((Path(self.temp.name)/'missing').exists())


if __name__ == '__main__':
    unittest.main()
