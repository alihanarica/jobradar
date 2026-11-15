import unittest,tempfile,json,io
from pathlib import Path
from unittest.mock import patch
from jobradar import core,v2_support,dashboard_v2,generator
class V2Tests(unittest.TestCase):
 def setUp(self):self.cfg=core.cfg_load()
 def test_hr_excluded(self):self.assertFalse(v2_support.interest({'title':'Director, HR Business Partner - Product and Engineering','location':'Dubai'},self.cfg)[0])
 def test_cx_included(self):self.assertTrue(v2_support.interest({'title':'Customer Success Director','location':'Riyadh'},self.cfg)[0])
 def test_us_remote_rejected(self):self.assertFalse(v2_support.interest({'title':'Head of AI Transformation','location':'Remote, United States'},self.cfg)[0])
 def test_random_role_excluded(self):self.assertFalse(v2_support.interest({'title':'Chief Nursing Officer','location':'Istanbul'},self.cfg)[0])
 def test_worldwide_needs_review(self):self.assertIn('unverified',v2_support.interest({'title':'Head of AI Transformation','location':'Remote Worldwide'},self.cfg)[1])
 def test_location_split(self):self.assertEqual(v2_support.parse_location({'location':'Dubai, United Arab Emirates'})[:2],('Dubai','Birleşik Arap Emirlikleri'))
 def test_jobicy(self):
  with patch('jobradar.v2_support.fetch_json',return_value={'jobs':[{'id':7,'jobTitle':'Chief of Staff','companyName':'X','jobGeo':'Anywhere','jobDescription':'<p>Hi</p>','url':'https://jobicy.com/jobs/7'}]}):
   self.assertEqual(v2_support.jobicy_search('Chief of Staff')[0]['id'],'jobicy:7')
 def test_himalayas(self):
  with patch('jobradar.v2_support.fetch_json',return_value={'jobs':[{'guid':'g1','title':'Commercial Director','companyName':'X','locationRestrictions':['AE'],'applicationLink':'https://firm.test/1'}]}):
   self.assertEqual(v2_support.himalayas_search('Commercial Director')[0]['countries'],['AE'])
 def test_dashboard_escapes_html(self):
  with tempfile.TemporaryDirectory() as d,patch.object(core,'DB',Path(d)/'jobs.sqlite'):
   c=core.connect();j={'id':'manual:test','title':'Head of AI Transformation <script>alert(1)</script>','company':'X','location':'Istanbul','url':'https://a.test/1','source':'manual','description':'hello'}
   self.assertEqual(core.record(c,j,baseline=True),'baseline');c.commit();c.close()
   dest=Path(d)/'dashboard.html';dashboard_v2.dashboard(dest);t=dest.read_text()
   self.assertNotIn('<script>alert(1)</script>',t);self.assertIn('u003cscript',t)
 def test_local_model_host_restricted(self):
  cfg=json.loads(json.dumps(self.cfg));cfg['llm']['base_url']='https://cloud.test'
  with self.assertRaises(RuntimeError):generator.llm_request(cfg,'A','B')
 def test_local_model_api(self):
  def request(req,timeout):
   self.assertEqual(req.full_url,'http://127.0.0.1:11434/api/chat');self.assertEqual(json.loads(req.data)['format'],'json')
   return io.BytesIO(b'{"message":{"content":"{\\"decision\\":\\"SKIP\\"}"}}')
  with patch('urllib.request.urlopen',side_effect=request):out=generator.llm_request(self.cfg,'prompt','JD')
  self.assertIn('SKIP',out)
