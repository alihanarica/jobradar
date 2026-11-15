import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from jobradar import core,sources,generator

class TestSources(unittest.TestCase):
    def test_freehire_search_integration_mock(self):
        calls=[]
        def fake(url,params):
            calls.append((url,params.copy()))
            return {'data':[{'public_slug':'test-1','title':'Head of AI Transformation','company':'Acme','location':'Istanbul, Turkey',
                             'description':'A'*330,'url':'https://jobs.acme.com/id/1','created_at':'2026-10-17T00:00:00Z'}],
                    'meta':{'total':1,'limit':100,'offset':0}}
        cfg=core.cfg_load()
        with patch('jobradar.sources.fetch_json',fake):
            jobs=sources.freehire_search(cfg,'AI Transformation')
        self.assertEqual(jobs[0]['id'],'freehire:test-1')
        self.assertTrue(calls[0][0].endswith('/agent/jobs/search'))
        self.assertEqual(calls[0][1]['q_fields'],'title')
        self.assertEqual(calls[0][1]['sort'],'created_at')
    def test_url_tracking(self):
        self.assertEqual(core.compare_url('https://EXAMPLE.com/apply/123/?utm_source=linkedin&job=77#x'),'https://example.com/apply/123?job=77')
    def test_location(self):
        cfg=core.cfg_load()
        self.assertEqual(core.location_fit({'location':'Riyadh','countries':[],'work_mode':''},cfg),'TARGET')
        self.assertEqual(core.location_fit({'location':'Berlin','countries':['DE'],'work_mode':'remote'},cfg),'OUTSIDE')
        self.assertEqual(core.location_fit({'location':'Paris','countries':['FR'],'work_mode':''},cfg),'OUTSIDE')
    def test_ats_greenhouse(self):
        with patch('jobradar.sources.fetch_json',return_value={'jobs':[{'id':123,'title':'Director of Strategy','absolute_url':'https://boards.greenhouse.io/x/jobs/123','location':{'name':'Istanbul'},'content':'<p>Role</p>'}]}):
            r=sources.ats_board({'provider':'greenhouse','board':'somecompany','company':'Acme','enabled':True})
        self.assertEqual(r[0]['id'],'greenhouse:somecompany:123')
        self.assertIn('Role',r[0]['description'])
    def test_ats_slug_restriction(self):
        with self.assertRaises(ValueError):sources.ats_board({'provider':'greenhouse','board':'https://evil.example/steal','enabled':True})

class TestLedger(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.patch_db=patch.object(core,'DB',Path(self.t.name)/'db.sqlite');self.patch_db.start()
        self.con=core.connect()
        self.j={'id':'freehire:ex1','source':'freehire','source_ref':'ex1','title':'Head of AI Transformation',
            'company':'Acme','location':'Istanbul, Turkey','countries':['TR'],'cities':['Istanbul'],
            'work_mode':'','url':'https://test.example/apply/999','description':'Business strategy and company data',
            'posted_at':'','source_first_seen':'','data_quality':'test'}
    def tearDown(self):
        self.con.close();self.patch_db.stop();self.t.cleanup()
    def test_baseline_dedup_and_change(self):
        self.assertEqual(core.record(self.con,self.j,['AI'],baseline=True),'baseline')
        self.assertEqual(core.record(self.con,self.j,['AI'],baseline=False),'known')
        self.j['description']='Different business strategy and data'
        self.assertEqual(core.record(self.con,self.j,['AI'],baseline=False),'changed')
        self.assertEqual(self.con.execute('SELECT count(*) FROM jobs').fetchone()[0],1)
    def test_history_exact_and_close(self):
        self.con.execute('INSERT INTO history(company,title,location,comparison_url,status,at) VALUES(?,?,?,?,?,?)',
                         ('Acme','Head of AI Transformation','Istanbul','https://test.example/apply/999','SUBMITTED CONFIRMED','2026-10-01'))
        match=core.shortlist_history(self.con,self.j)
        self.assertEqual(match[0]['match_type'],'EXACT_URL')

class TestModelContract(unittest.TestCase):
    def test_skip_without_package(self):
        self.assertEqual(generator.parse_model_json('{"decision":"SKIP","reason_tr":"no rights"}')['decision'],'SKIP')
        with self.assertRaises(ValueError):generator.parse_model_json('{"decision":"APPLY"}')
    def test_invalid(self):
        with self.assertRaises(ValueError):generator.parse_model_json('not json')

if __name__=='__main__':unittest.main()

class TestScanLifecycle(unittest.TestCase):
    def test_first_successful_scan_is_baseline_second_is_new(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(core,'DB',Path(d)/'scan.db'), patch('jobradar.core.freehire_search') as search:
                conf=core.cfg_load()
                conf['searches']=[{'name':'Test','queries':['AI Transformation']}]
                conf['ats_boards']=[]
                conf['sources']={'freehire':True,'himalayas':False,'jobicy':False}
                conf['notify_mac']=False
                with patch('jobradar.core.cfg_load',return_value=conf):
                    first={'id':'freehire:base','source':'freehire','source_ref':'base','url':'https://a.example/1',
                        'title':'Head of AI Transformation','company':'A','location':'Istanbul','countries':['TR'],
                        'cities':['Istanbul'],'description':'Test JD','work_mode':''}
                    later=dict(first,id='freehire:new',source_ref='new',url='https://a.example/2')
                    search.side_effect=[[first],[first,later]]
                    a=core.scan(quiet=True)
                    b=core.scan(quiet=True)
                self.assertEqual(a['baseline'],1)
                self.assertEqual(a['new'],0)
                self.assertEqual(b['new'],1)
                con=core.connect()
                self.assertEqual(con.execute('SELECT status FROM jobs WHERE id="freehire:new"').fetchone()[0],'DISCOVERED')
                con.close()

class TestDraftGuard(unittest.TestCase):
    def test_stop_request_history_blocks_generation_before_model_call(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(core,'DB',Path(d)/'guard.db'):
                con=core.connect()
                job={'id':'freehire:stop','source':'freehire','source_ref':'stop','url':'https://a.example/99',
                    'title':'Country Manager','company':'Veeam','location':'Istanbul','countries':['TR'],
                    'cities':['Istanbul'],'description':'A'*300,'work_mode':''}
                core.record(con,job)
                con.execute('INSERT INTO history(company,title,status,at) VALUES(?,?,?,?)',('Veeam','Country Manager','EXPLICIT STOP REQUEST','2026-10-16'))
                con.commit();con.close()
                with self.assertRaisesRegex(RuntimeError,'STOP'):
                    generator.evaluate('freehire:stop',model_fn=lambda *a: (_ for _ in ()).throw(AssertionError('MODEL MUST NOT BE CALLED')))
