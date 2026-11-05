import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_skill import ROOT, toolkit

sys.path.insert(0, str(ROOT / 'skills/careerpilot/scripts'))
from private_settings import Settings, deliver, send_telegram, site_origin
from account_fill import fill


@unittest.skipUnless(os.name == 'nt', 'Windows DPAPI integration')
class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ws = toolkit.Workspace(self.root)
        self.ws.initialize()
        self.settings = Settings(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def site(self, **extra):
        return self.settings.save(dict(kind='site', url='https://careers.example.invalid/path',
            username='fixture@example.invalid', password='Synthetic-Secret-123!', allow_login=True, allow_signup=True, **extra))

    def test_encrypted_storage_redaction_and_exact_origin(self):
        self.site()
        self.assertNotIn(b'Synthetic-Secret', self.settings.path.read_bytes())
        self.assertNotIn('Synthetic-Secret', json.dumps(self.settings.public()))
        self.assertNotIn('Synthetic-Secret', json.dumps(self.ws.read()))
        self.assertEqual(self.settings.credentials('https://careers.example.invalid/login')['password'], 'Synthetic-Secret-123!')
        for url in ['http://careers.example.invalid', 'https://other.careers.example.invalid', 'https://careers.example.invalid.evil.invalid', 'https://careers.example.invalid:8443']:
            with self.assertRaises(ValueError):
                self.settings.credentials(url)

    def test_unique_generated_signup_password_and_revocation(self):
        self.settings.save({'kind':'signup', 'email':'fixture@example.invalid'})
        for host in ['one', 'two']:
            self.settings.save({'kind':'site', 'url':f'https://{host}.invalid', 'allow_login':False, 'allow_signup':True})
        one = self.settings.credentials('https://one.invalid', 'signup')
        two = self.settings.credentials('https://two.invalid', 'signup')
        self.assertNotEqual(one['password'], two['password'])
        self.assertEqual(one, self.settings.credentials('https://one.invalid', 'signup'))
        with self.assertRaises(ValueError):
            self.settings.credentials('https://one.invalid', 'login')
        self.settings.save({'kind':'remove-site', 'url':'https://one.invalid'})
        with self.assertRaises(ValueError):
            self.settings.credentials('https://one.invalid', 'signup')

    def paused(self):
        jid=self.ws.mutate({'op':'job-add','title':'Fixture','company':'Fixture','description':'Test','source':'Test','url':'https://example.invalid/job'})['job_id']
        self.ws.mutate({'op':'select','job_id':jid})
        result=self.ws.mutate({'op':'pause','job_id':jid,'reason':'OTP secret 123456', 'next_action':'Resolve privately'})
        return jid, result['request_id']

    def test_pause_survives_delivery_failure_and_retry_deduplicates(self):
        jid, rid=self.paused()
        state=self.ws.read()
        self.assertEqual(state['jobs'][jid]['status'], 'Needs attention')
        self.assertEqual(state['assistance'][rid]['delivery'], 'failed')
        self.ws.mutate({'op':'assistance-retry','request_id':rid})
        with patch('private_settings.send_telegram') as send:
            deliver(self.root, rid)
            deliver(self.root, rid)
            send.assert_called_once()
            self.assertNotIn('123456', send.call_args.args[1])
        self.assertEqual(self.ws.read()['assistance'][rid]['delivery'],'sent')
        self.ws.mutate({'op':'resume','job_id':jid,'note':'Verified manually'})
        self.assertEqual(self.ws.read()['assistance'][rid]['status'],'resolved')
        self.assertEqual(self.ws.read()['jobs'][jid]['status'],'Preparing')

    def test_notification_error_never_exposes_token(self):
        token='123456:'+'a'*30
        self.settings.save({'kind':'telegram','token':token,'chat_id':'123456','enabled':True})
        with patch('private_settings.build_opener', side_effect=OSError('https://secret/'+token)):
            with self.assertRaises(ValueError) as caught:
                send_telegram(self.root, 'Test')
        self.assertNotIn(token,str(caught.exception))
        self.assertNotIn(token,json.dumps(self.settings.public()))

    def test_browser_fill_checks_destination_and_does_not_submit(self):
        self.site()
        class Locator:
            def count(self): return 1
            def evaluate(self, script): return page.action
            def fill(self, value): page.values.append(value)
        class Page:
            url='https://careers.example.invalid/login'
            action='https://evil.invalid/collect'
            values=[]
            def locator(self, selector): return Locator()
        page=Page()
        with self.assertRaises(ValueError):
            fill(page, self.settings, page.url, 'login', {'password':'#password'})
        self.assertEqual(page.values, [])
        page.action=page.url
        result=fill(page,self.settings,page.url,'login',{'username':'#user','password':'#password'})
        self.assertFalse(result['submitted'])
        self.assertEqual(len(page.values),2)


if __name__ == '__main__':
    unittest.main()
