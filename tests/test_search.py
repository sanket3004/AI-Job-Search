import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from test_skill import ROOT, toolkit
sys.path.insert(0, str(ROOT / 'skills' / 'careerpilot' / 'scripts'))
import job_search as search


def candidate(title='Data Analyst', location='New York', index=1, age=1):
    return {'title': title, 'company':'Synthetic Employer', 'description':'SQL data analysis and reporting.',
            'url':f'https://example.invalid/job/{index}', 'location':location, 'source':'Fixture',
            'discovery':{'remote':False, 'published_at':(datetime.now(timezone.utc)-timedelta(days=age)).isoformat() if age is not None else None}}


class FakeClient:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [candidate(),candidate('Data Assistant','Berlin',2),candidate('Data Analyst','New York',3,40)]

    def collect(self, key):
        return self.rows if key == 'remotive' else [], {'source':key,'status':'complete','fetched_at':search.utc(),'count':len(self.rows) if key == 'remotive' else 0,'scope':'Synthetic fixture','warning':''}


class SearchTests(unittest.TestCase):
    def setUp(self):
        (ROOT/'work').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'work')
        self.root=Path(self.temp.name)
        self.ws=toolkit.Workspace(self.root)
        self.ws.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def run_search(self, **options):
        manager=search.SearchManager(self.root,FakeClient())
        run=manager.start({'role':'Data Analyst','location':'New York',**options})
        manager.thread.join(timeout=5)
        self.assertFalse(manager.thread.is_alive())
        return self.ws.read()['searches'][run['search_id']]

    def test_low_ranked_jobs_survive_and_dates_filter_without_score_cutoff(self):
        run=self.run_search(posted_within='7')
        self.assertEqual(len(run['job_ids']),2)
        scores=[j['search_relevance']['score'] for j in run['listings'].values()]
        self.assertTrue(any(s<45 for s in scores))
        self.assertTrue(any(s>=75 for s in scores))
        self.assertEqual(run['status'],'complete')
        self.assertTrue(all(j['status']=='Saved' for j in self.ws.read()['jobs'].values()))

    def test_each_run_is_separate_and_deduplicated_jobs_keep_application_state(self):
        first=self.run_search()
        jid=first['job_ids'][0]
        self.ws.mutate({'op':'select','job_id':jid})
        second=self.run_search(posted_within='7')
        state=self.ws.read()
        self.assertNotEqual(first['id'],second['id'])
        self.assertEqual(len(state['searches']),2)
        self.assertEqual(len(state['jobs']),3)
        self.assertEqual(state['jobs'][jid]['status'],'Selected')
        self.assertEqual(state['searches'][first['id']]['listings'],first['listings'])
        self.assertTrue(first['created_at'])

    def test_date_windows_unknown_dates_and_exact_boundary(self):
        now=datetime(2026,11,5,12,tzinfo=timezone.utc)
        query=search.validate_query({'role':'Analyst','location':'Remote','posted_within':'1'})
        job=candidate()
        job['discovery']['published_at']=(now-timedelta(hours=24)).isoformat()
        self.assertTrue(search.within_window(job,query,now))
        job['discovery']['published_at']=(now-timedelta(hours=24,seconds=1)).isoformat()
        self.assertFalse(search.within_window(job,query,now))
        job['discovery']['published_at']=None
        self.assertFalse(search.within_window(job,query,now))
        query['include_unknown_dates']=True
        self.assertTrue(search.within_window(job,query,now))
        query['posted_within']='any'
        self.assertTrue(search.within_window(job,query,now))

    def test_date_formats_and_invalid_dates(self):
        self.assertIsNone(search.posting_date('unknown'))
        self.assertIsNone(search.posting_date(None))
        self.assertEqual(search.posting_date(0),'1970-01-01T00:00:00+00:00')
        self.assertEqual(search.posting_date('2026-11-05T10:00:00-05:00'),'2026-11-05T15:00:00+00:00')
        self.assertEqual(search.posting_date('2026-11-05'),'2026-11-05T00:00:00+00:00')

    def test_relevance_explains_unknown_remote_eligibility(self):
        j=candidate(location='USA');j['discovery']['remote']=True
        rating=search.relevance(j,'Data Analyst','New York')
        self.assertEqual(rating['location_note'],'Remote geography needs review')
        self.assertEqual(rating['breakdown']['Location text (40 max)'],10)
        self.assertEqual(search.relevance(j,'Data Analyst','United States')['breakdown']['Location text (40 max)'],40)

    def test_invalid_queries(self):
        for data in [None,{}, {'role':'','location':'Remote'}, {'role':'Data','location':'x','posted_within':[]}, {'role':'x','location':'x','include_unknown_dates':'yes'}]:
            with self.assertRaises(ValueError): search.validate_query(data)

    def test_feed_normalization_strips_html_preserves_dates_and_links(self):
        data={'title':'<b>Analyst</b>','company_name':'Demo','description':'<p>Data</p><script>bad()</script>','location':'Berlin','created_at':1793880000,'url':'https://example.invalid/role','remote':False}
        job=search.normalize_job('arbeitnow',data)
        self.assertEqual(job['title'],'Analyst')
        self.assertNotIn('bad()',job['description'])
        self.assertEqual(job['url'],data['url'])
        self.assertIsNotNone(job['discovery']['published_at'])
        data['url']='javascript:alert(1)'
        with self.assertRaises(ValueError):search.normalize_job('arbeitnow',data)

    def test_cache_and_pagination_preserve_all_feed_rows(self):
        calls=[]
        def fetch(endpoint):
            calls.append(endpoint)
            return {'jobs':[{'jobTitle':'Analyst','companyName':'Demo','jobDescription':'Data','jobGeo':'Anywhere','url':f'https://example.invalid/{len(calls)}'}], 'nextCursor':'token+next' if len(calls)==1 else None}
        client=search.FeedClient(self.root,fetch)
        rows,coverage=client.collect('jobicy')
        self.assertEqual(len(rows),2)
        self.assertIn('cursor=token%2Bnext',calls[1])
        self.assertEqual(coverage['pages'],2)
        again,cached=client.collect('jobicy')
        self.assertEqual(again,rows)
        self.assertTrue(cached['cached'])
        self.assertEqual(len(calls),2)

    def test_partial_failure_retains_earlier_rows_and_reports_limit(self):
        calls=[]
        def fetch(endpoint):
            calls.append(endpoint)
            if len(calls)>1:raise OSError('Synthetic failure')
            return {'jobs':[{'jobTitle':'Analyst','companyName':'Demo','url':'https://example.invalid/1'}], 'nextCursor':'more'}
        rows,coverage=search.FeedClient(self.root,fetch).collect('jobicy')
        self.assertEqual(len(rows),1)
        self.assertEqual(coverage['status'],'partial')
        self.assertTrue(coverage['warning'])

    def test_no_arbitrary_feed_urls_and_no_redirects(self):
        with self.assertRaises(ValueError):search.fetch_json('http://127.0.0.1/private')
        with self.assertRaises(ValueError):search.fetch_json('https://jobicy.com/other')
        with self.assertRaises(ValueError):search.NoRedirects().redirect_request(None,None,None,None,None,None)

    def test_concurrent_search_is_rejected(self):
        entered=threading.Event();release=threading.Event()
        class Blocking(FakeClient):
            def collect(self,key):
                entered.set();release.wait(timeout=5);return super().collect(key)
        manager=search.SearchManager(self.root,Blocking())
        try:
            manager.start({'role':'Data','location':'Remote'})
            self.assertTrue(entered.wait(timeout=2))
            with self.assertRaises(RuntimeError):manager.start({'role':'Data','location':'Remote'})
        finally:
            release.set();manager.thread.join(timeout=5)


if __name__=='__main__':unittest.main()
