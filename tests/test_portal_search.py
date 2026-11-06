import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from test_skill import toolkit


class PortalSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.ws=toolkit.Workspace(Path(self.temp.name));self.ws.initialize()
        self.sid=self.ws.mutate({'op':'portal-search-start','role':'Data Analyst','location':'Toronto','posted_within':'7'})['search_id']
        self.ws.mutate({'op':'portal-search-begin','search_id':self.sid})

    def tearDown(self): self.temp.cleanup()

    def candidate(self, source='LinkedIn', **kwargs):
        row={'title':'Junior Data Analyst','company':'Fixture','description':'Analyze data','location':'Toronto',
             'source_url':'https://www.linkedin.com/jobs/view/123' if source=='LinkedIn' else 'https://ca.indeed.com/viewjob?jk=123',
             'discovery':{'published_at':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()},
             'application_route':{'type':'external','url':'https://careers.example.invalid/jobs/123','employer_verified':True,'on_platform_available':False,'evidence':'Apply button leads to matching employer and role on the ATS; no on-platform option.','checked_at':toolkit.utc()}}
        row.update(kwargs);return row

    def record(self, rows, source='LinkedIn'):
        return self.ws.mutate({'op':'portal-search-results','search_id':self.sid,'source':source,'jobs':rows})

    def finish_source(self, source, status='complete'):
        return self.ws.mutate({'op':'portal-source-finish','search_id':self.sid,'source':source,'status':status,'note':'Synthetic bounded source check'})

    def test_only_verified_external_jobs_enter_ranked_list(self):
        rows=[self.candidate()]
        for kind in ['easy_apply','indeed_apply','unknown']:
            rows.append(self.candidate(application_route={'type':kind}))
        result=self.record(rows)
        self.assertEqual((result['accepted'],result['excluded']),(1,3))
        run=self.ws.read()['searches'][self.sid]
        self.assertEqual(len(run['job_ids']),1)
        self.assertIn('search_relevance',next(iter(run['listings'].values())))

    def test_on_platform_even_with_external_link_is_excluded(self):
        candidate=self.candidate();candidate['application_route']['on_platform_available']=True
        self.assertEqual(self.record([candidate])['excluded'],1)
        self.assertEqual(self.ws.read()['jobs'],{})

    def test_destination_and_verification_are_checked(self):
        for destination in ['https://smartapply.indeed.com/job/123','https://www.linkedin.com/jobs/view/123','http://careers.example.invalid/jobs/123']:
            row=self.candidate();row['application_route']['url']=destination
            self.assertEqual(self.record([row])['excluded'],1)
        row=self.candidate();row['application_route']['checked_at']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        self.assertEqual(self.record([row])['excluded'],1)
        with self.assertRaises(ValueError): self.record([self.candidate(source_url='https://linkedin.com.evil.invalid/job')])

    def test_both_sources_required_and_blocked_source_is_partial(self):
        self.finish_source('LinkedIn')
        with self.assertRaises(ValueError): self.ws.mutate({'op':'portal-search-finish','search_id':self.sid})
        self.finish_source('Indeed','blocked')
        self.assertEqual(self.ws.mutate({'op':'portal-search-finish','search_id':self.sid})['status'],'partial')

    def test_duplicate_employer_job_keeps_both_citations(self):
        self.record([self.candidate()]);self.record([self.candidate('Indeed')],'Indeed')
        run=self.ws.read()['searches'][self.sid]
        self.assertEqual(len(run['job_ids']),1)
        self.assertEqual(len(next(iter(run['listings'].values()))['portal_sources']),2)
        self.finish_source('LinkedIn');self.finish_source('Indeed')
        self.assertEqual(self.ws.mutate({'op':'portal-search-finish','search_id':self.sid})['status'],'complete')

    def test_dates_filter_without_score_cutoff_and_no_generic_bypass(self):
        row=self.candidate(title='Unrelated role',description='Test',location='Other city')
        self.assertEqual(self.record([row])['accepted'],1)
        listing=next(iter(self.ws.read()['searches'][self.sid]['listings'].values()))
        self.assertEqual(listing['search_relevance']['score'],0)
        self.assertEqual(self.record([self.candidate(discovery={})])['excluded'],1)
        with self.assertRaises(ValueError): self.ws.mutate({'op':'search-finish','search_id':self.sid,'status':'complete'})
        with self.assertRaises(ValueError): self.ws.mutate({'op':'search-results','search_id':self.sid,'jobs':[self.candidate()],'coverage':{}})


if __name__=='__main__':unittest.main()
