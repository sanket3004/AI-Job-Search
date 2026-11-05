import importlib.util
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

toolkit = load('toolkit', ROOT / 'skills' / 'ai-job-toolkit' / 'scripts' / 'toolkit.py')
installer = load('installer', ROOT / 'tools' / 'install_skill.py')
packager = load('packager', ROOT / 'tools' / 'package_skill.py')

class SkillTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work'
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.ws = toolkit.Workspace(self.root / 'private')
        self.ws.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def run_op(self, op, **data):
        return self.ws.mutate({'op': op, **data})

    def job(self, number=1):
        return self.run_op('job-add', title='Analyst', company='Example', url=f'https://example.org/jobs/{number}', description='SQL experience', source='Test fixture')['job_id']

    def ready(self, jid):
        self.run_op('select', job_id=jid)
        self.run_op('start', job_id=jid)
        self.checkpoint(jid)
        self.run_op('ready', job_id=jid)

    def checkpoint(self, jid, **overrides):
        c = dict(page_url='https://example.org/apply', step='Review', answers=[{'field':'Name','value':'Test Candidate','source':'Synthetic test profile'}], unresolved=[], complete=True, observation='Synthetic test: final review visible')
        c.update(overrides)
        self.run_op('checkpoint', job_id=jid, checkpoint=c)

    def authorize(self, jid):
        return self.run_op('authorize', job_ids=[jid], user_instruction='Synthetic test approval for this job only', expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())['authorization_id']

    def test_fresh_profile_and_restart_persistence(self):
        self.assertEqual(self.ws.read()['profile'], {})
        self.run_op('profile-save', profile={'name':'Test Candidate'})
        self.assertEqual(toolkit.Workspace(self.ws.root).read()['profile']['name'], 'Test Candidate')
        self.ws.initialize()
        self.assertEqual(self.ws.read()['profile_revision'], 1)

    def test_duplicate_posting_tracking_params(self):
        jid = self.job()
        result = self.run_op('job-add', title='Duplicate', company='Example', url='https://example.org/jobs/1?utm_source=foo#description', description='same', source='Test')
        self.assertTrue(result['duplicate'])
        self.assertEqual(result['job_id'], jid)

    def test_blocked_job_does_not_block_other_jobs(self):
        first, second = self.job(), self.job(2)
        for jid in [first, second]:
            self.run_op('select', job_id=jid)
        self.run_op('start', job_id=first)
        self.run_op('pause', job_id=first, reason='Unknown authorization answer', next_action='Ask candidate')
        self.run_op('start', job_id=second)
        self.assertEqual(self.ws.read()['jobs'][first]['status'], 'Needs attention')
        self.assertEqual(self.ws.read()['jobs'][second]['status'], 'Filling')
        with self.assertRaises(ValueError):
            self.run_op('start', job_id=first)

    def test_incomplete_or_stale_checkpoint_cannot_be_ready(self):
        jid = self.job()
        self.run_op('select', job_id=jid)
        self.run_op('start', job_id=jid)
        self.checkpoint(jid, unresolved=['Required phone'])
        with self.assertRaises(ValueError):
            self.run_op('ready', job_id=jid)
        self.checkpoint(jid)
        self.run_op('profile-save', profile={'name':'Changed Candidate'})
        with self.assertRaises(ValueError):
            self.run_op('ready', job_id=jid)

    def test_prepare_only_does_not_submit(self):
        jid = self.job()
        self.ready(jid)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=jid, authorization_id='invented')
        self.assertEqual(self.ws.read()['jobs'][jid]['status'], 'Ready for review')

    def test_authorization_is_scoped_consumed_and_uncertain_not_retried(self):
        a, b = self.job(), self.job(2)
        self.ready(a)
        self.ready(b)
        grant = self.authorize(a)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=b, authorization_id=grant)
        self.run_op('submit-begin', job_id=a, authorization_id=grant)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=a, authorization_id=grant)
        self.run_op('uncertain', job_id=a, evidence='Synthetic browser timeout')
        with self.assertRaises(ValueError):
            self.run_op('start', job_id=a)
        self.run_op('resolve', job_id=a, result='not_submitted', evidence='Synthetic portal shows no application')
        self.run_op('start', job_id=a)
        self.checkpoint(a)
        self.run_op('ready', job_id=a)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=a, authorization_id=grant)

    def test_document_tampering_invalidates_grant(self):
        jid = self.job()
        source = self.root / 'resume.txt'
        source.write_text('Synthetic resume', encoding='utf-8')
        self.run_op('document-add', job_id=jid, kind='resume', path=str(source))
        self.ready(jid)
        grant = self.authorize(jid)
        doc = self.ws.read()['jobs'][jid]['documents'][0]
        (self.ws.root / doc['path']).write_text('Changed content', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=jid, authorization_id=grant)

    def test_changed_answers_invalidate_grant(self):
        jid = self.job()
        self.ready(jid)
        grant = self.authorize(jid)
        self.checkpoint(jid, answers=[{'field':'Name','value':'Different name','source':'Synthetic correction'}])
        self.run_op('ready', job_id=jid)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=jid, authorization_id=grant)

    def test_revoke_and_expired_authorization(self):
        jid = self.job()
        self.ready(jid)
        grant = self.authorize(jid)
        self.run_op('revoke', authorization_id=grant)
        with self.assertRaises(ValueError):
            self.run_op('submit-begin', job_id=jid, authorization_id=grant)
        with self.assertRaises(ValueError):
            self.run_op('authorize', job_ids=[jid], user_instruction='test', expires_at='2000-01-01T00:00:00+00:00')

    def test_rollback_and_confirmation_evidence(self):
        jid = self.job()
        self.ready(jid)
        grant = self.authorize(jid)
        self.run_op('submit-begin', job_id=jid, authorization_id=grant)
        with self.assertRaises(ValueError):
            self.run_op('submitted', job_id=jid, evidence='')
        self.assertEqual(self.ws.read()['jobs'][jid]['status'], 'Submitting')
        self.run_op('submitted', job_id=jid, evidence='Synthetic confirmation: Application received #TEST')
        self.assertEqual(self.ws.read()['jobs'][jid]['status'], 'Submitted')

    def test_contact_requires_published_email_evidence_and_report_escapes(self):
        jid = self.job()
        contact = {'name':'Test Recruiter','company':'Example','role':'Recruiter','relevance':'Team match','source_url':'https://example.org/team','relationship':'likely','email':'recruiter@example.org'}
        with self.assertRaises(ValueError):
            self.run_op('contact-add', job_id=jid, contact=contact)
        self.run_op('note', job_id=jid, text='<script>alert(1)</script>')
        report = Path(self.ws.report()['report']).read_text(encoding='utf-8')
        self.assertNotIn('<script>', report)
        self.assertIn('&lt;script&gt;', report)

    def test_install_and_archive_have_only_portable_skill_files(self):
        destination = self.root / 'installed' / 'ai-job-toolkit'
        installer.install(destination)
        self.assertTrue((destination / 'SKILL.md').is_file())
        self.assertTrue(installer.install(destination)['unchanged'])
        (destination / 'SKILL.md').write_text('User change', encoding='utf-8')
        with self.assertRaises(ValueError):
            installer.install(destination)
        archive = self.root / 'skill.zip'
        packager.package(archive)
        with zipfile.ZipFile(archive) as z:
            self.assertIn('ai-job-toolkit/SKILL.md', z.namelist())
            self.assertTrue(all(n.startswith('ai-job-toolkit/') for n in z.namelist()))
            self.assertFalse(any('__pycache__' in n or n.endswith(('.sqlite3','.pyc')) for n in z.namelist()))

if __name__ == '__main__':
    unittest.main()
