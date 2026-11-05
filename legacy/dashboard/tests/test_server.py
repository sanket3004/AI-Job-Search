import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from server import make_server

class ApiTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / 'data' / 'test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.path = Path(self.temp.name) / 'test.db'
        self.server = make_server(self.path, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.get()['token']

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def get(self):
        with urllib.request.urlopen(self.base + '/api/state') as r:
            return json.load(r)

    def post(self, route, data, token=None):
        req = urllib.request.Request(self.base + route, data=json.dumps(data).encode(), headers={'Content-Type':'application/json','X-Toolkit-Token':self.token if token is None else token})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def add(self, **kwargs):
        return self.post('/api/jobs', dict(title='Data analyst', company='Test company', description='SQL and Python required', **kwargs))

    def test_profile_keyword_boundaries_and_persistence(self):
        self.post('/api/profile', {'skills':'SQL, Python, R'})
        self.assertEqual(self.add()[0], 200)
        state = self.get()
        self.assertEqual(state['jobs'][0]['score'], 67)
        self.assertEqual(state['jobs'][0]['matched'], ['SQL', 'Python'])
        other = make_server(self.path, 0)
        other.server_close()
        self.assertEqual(self.get()['profile']['skills'], 'SQL, Python, R')

    def test_duplicate_url_rejected_without_extra_job(self):
        self.add(url='https://example.org/job/1')
        self.assertEqual(self.add(url='https://example.org/job/1')[0], 400)
        self.assertEqual(len(self.get()['jobs']), 1)

    def test_pausing_requires_reason_and_does_not_block_another_job(self):
        self.add()
        self.add()
        self.assertEqual(self.post('/api/jobs/update', {'id':1,'status':'Needs attention'})[0], 400)
        self.assertEqual(self.post('/api/jobs/update', {'id':1,'status':'Needs attention','notes':'Login required'})[0], 200)
        self.assertEqual(self.post('/api/jobs/update', {'id':2,'status':'Shortlisted'})[0], 200)
        self.assertEqual([j['status'] for j in self.get()['jobs']], ['Shortlisted','Needs attention'])

    def test_permissions_and_invalid_input(self):
        self.assertEqual(self.post('/api/jobs', {}, token='bad')[0], 403)
        self.assertEqual(self.add(url='javascript:alert(1)')[0], 400)
        self.assertEqual(self.post('/api/jobs/update', {'id':1,'status':'Invented'})[0], 400)
        self.assertEqual(self.post('/api/settings', {'submission':'Automatic'})[0], 400)
        self.assertEqual(self.get()['settings']['submission'], 'Prepare only')

    def test_static_page_and_export_escape_formulas(self):
        self.post('/api/jobs', {'title':'=1+1','company':'Export test'})
        with urllib.request.urlopen(self.base + '/api/export') as r:
            self.assertIn("'=1+1", r.read().decode())
        with urllib.request.urlopen(self.base) as r:
            self.assertEqual(r.status, 200)
            self.assertIn("frame-ancestors 'none'", r.headers['Content-Security-Policy'])

if __name__ == '__main__':
    unittest.main()
