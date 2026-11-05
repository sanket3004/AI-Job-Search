import tempfile
import unittest
from pathlib import Path
from test_skill import toolkit


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.ws=toolkit.Workspace(Path(self.temp.name));self.ws.initialize()
        self.jid=self.ws.mutate({'op':'job-add','title':'Analyst','company':'Fixture','url':'https://example.invalid/job','source':'Test','description':'Fixture role'})['job_id']
        self.configure()
        self.cid=self.start()

    def tearDown(self): self.temp.cleanup()

    def configure(self, auto=False, enabled=True):
        return self.ws.mutate({'op':'email-config','account':'candidate@example.invalid','enabled':enabled,'auto_apply':auto})

    def start(self):
        return self.ws.mutate({'op':'email-check-start','account':'candidate@example.invalid','job_ids':[self.jid],'scope':'Synthetic fixtures only'})['check_id']

    def record(self, **kwargs):
        data={'op':'email-record','check_id':self.cid,'message_id':'18abc123','received_at':'2026-01-01T12:00:00Z','sender':'careers@example.invalid','subject':'Application update','summary':'Employer declined the application.','evidence':'We will not move forward with this application.','match_reason':'Exact fixture reference.','job_id':self.jid,'suggested_status':'Rejected','match_confidence':'confirmed','classification_confidence':'confirmed'}
        data.update(kwargs);return self.ws.mutate(data)

    def test_review_default_and_deduplication(self):
        result=self.record()
        self.assertEqual(result['review'],'pending')
        self.assertEqual(self.ws.read()['jobs'][self.jid]['status'],'Saved')
        self.assertTrue(self.record()['duplicate'])
        self.ws.mutate({'op':'email-apply','email_id':result['email_id'],'job_id':self.jid,'note':'Checked evidence'})
        self.assertEqual(self.ws.read()['jobs'][self.jid]['status'],'Rejected')
        with self.assertRaises(ValueError):
            self.ws.mutate({'op':'email-apply','email_id':result['email_id'],'note':'Repeat'})

    def test_auto_only_confirmed_match_and_classification(self):
        self.configure(auto=True);self.cid=self.start()
        uncertain=self.record(classification_confidence='uncertain')
        self.assertEqual(uncertain['review'],'pending')
        unmatched=self.record(message_id='18abc124',job_id=None,match_confidence='uncertain')
        self.assertEqual(unmatched['review'],'pending')
        result=self.record(message_id='18abc125')
        self.assertEqual(result['review'],'applied')
        self.assertEqual(self.ws.read()['jobs'][self.jid]['status'],'Rejected')

    def test_changed_permission_invalidates_run(self):
        self.configure(enabled=False)
        with self.assertRaises(ValueError): self.record()
        with self.assertRaises(ValueError): self.start()
        self.configure()
        with self.assertRaises(ValueError): self.record()
        with self.assertRaises(ValueError):
            self.ws.mutate({'op':'email-check-start','account':'other@example.invalid','job_ids':[self.jid],'scope':'Test'})

    def test_old_or_regressive_messages_cannot_overwrite(self):
        self.configure(auto=True);self.cid=self.start()
        self.record(suggested_status='Interview')
        older=self.record(message_id='18abc124',received_at='2025-12-31T12:00:00Z')
        regression=self.record(message_id='18abc125',received_at='2026-01-02T12:00:00Z',suggested_status='Application received')
        self.assertEqual(older['review'],'pending');self.assertEqual(regression['review'],'pending')
        self.assertEqual(self.ws.read()['jobs'][self.jid]['status'],'Interview')
        with self.assertRaises(ValueError): self.ws.mutate({'op':'email-apply','email_id':older['email_id'],'note':'Try stale'})

    def test_conflicting_final_outcomes_and_unknown_require_review(self):
        self.configure(auto=True);self.cid=self.start();self.record()
        offer=self.record(message_id='18abc124',received_at='2026-01-02T12:00:00Z',suggested_status='Offer')
        unknown=self.record(message_id='18abc125',suggested_status='Unknown')
        self.assertEqual(offer['review'],'pending')
        with self.assertRaises(ValueError): self.ws.mutate({'op':'email-apply','email_id':unknown['email_id'],'note':'Unknown'})
        self.ws.mutate({'op':'email-dismiss','email_id':unknown['email_id'],'note':'No actionable status'})
        self.assertEqual(self.ws.read()['email_tracking']['messages'][unknown['email_id']]['review'],'dismissed')

    def test_invalid_evidence_scope_dates_and_finished_checks(self):
        for values in [{'evidence':''},{'message_id':'<rfc-id@example.invalid>'},{'job_id':'unknown'},{'received_at':'2026-01-01'},{'suggested_status':'Approved'}]:
            with self.assertRaises(ValueError): self.record(**values)
        self.assertEqual(self.ws.read()['email_tracking']['messages'],{})
        self.ws.mutate({'op':'email-check-finish','check_id':self.cid,'status':'partial','note':'Test limit reached'})
        with self.assertRaises(ValueError): self.record()

    def test_under_review_preserves_browser_workflow(self):
        self.configure(auto=True);self.cid=self.start()
        result=self.record(suggested_status='Under review')
        state=self.ws.read()
        self.assertEqual(result['review'],'applied')
        self.assertEqual(state['jobs'][self.jid]['email_update']['status'],'Under review')
        self.assertEqual(state['jobs'][self.jid]['status'],'Saved')
        self.assertTrue(state['email_tracking']['messages'][result['email_id']]['source_url'].startswith('https://mail.google.com/'))


if __name__=='__main__': unittest.main()
