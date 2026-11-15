"""Role and geographical screening plus public remote job feeds."""
import re,unicodedata,hashlib
from .sources import fetch_json,html_text
COUNTRIES={'TR':'Türkiye','SA':'Suudi Arabistan','AE':'Birleşik Arap Emirlikleri','QA':'Katar','US':'ABD','DE':'Almanya','FR':'Fransa','GB':'Birleşik Krallık','CA':'Kanada','IN':'Hindistan','NL':'Hollanda','SE':'İsveç','CH':'İsviçre','AU':'Avustralya','ES':'İspanya','IT':'İtalya'}
ALIASES={'TR':['turkey','turkiye','türkiye','istanbul','ankara','izmir'],'SA':['saudi arabia','ksa','riyadh','jeddah'],'AE':['united arab emirates','uae','dubai','abu dhabi'],'QA':['qatar','doha'],'US':['united states','usa','california','new york','massachusetts','texas','seattle','boston','chicago'],'DE':['germany','berlin','munich'],'FR':['france','paris'],'GB':['united kingdom','london','england'],'CA':['canada','toronto'],'IN':['india'],'NL':['netherlands','amsterdam'],'SE':['sweden','stockholm'],'CH':['switzerland','zurich'],'AU':['australia'],'ES':['spain'],'IT':['italy']}
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '').casefold().replace('ı','i'))
 return re.sub(r'\s+',' ',re.sub(r'[^\w ]+',' ',''.join(x for x in s if not unicodedata.combining(x)))).strip()
def match(needle,text):
 needle=norm(needle);return bool(needle and re.search(r'(?<!\w)'+re.escape(needle)+r'(?!\w)',norm(text)))
def parse_location(j):
 raw=str(j.get('location') or '');provided=j.get('countries') or []
 if isinstance(provided,str):provided=[provided]
 codes=[str(v.get('code','') if isinstance(v,dict) else v).upper() for v in provided]
 code=next((x for x in codes if x in COUNTRIES),'')
 if not code:
  code=next((c for c,names in ALIASES.items() if any(match(x,raw) for x in names)),'')
 city=''
 cs=j.get('cities') or []
 if cs:city=str(cs[0].get('name','') if isinstance(cs[0],dict) else cs[0])
 if not city:
  first=re.split(r',|\s+[-–—]\s+',raw)[0].strip()
  if norm(first) not in ('remote','remote worker','worldwide','global','anywhere','usa','united states','turkey','turkiye','qatar','saudi arabia','united arab emirates') and not match('remote',first):
   city=first[:65]
 return city,COUNTRIES.get(code,'Bilinmiyor'),code
def location_fit(j,cfg):
 codes=j.get('countries') or []
 if isinstance(codes,list):
  if any(str(x.get('code','') if isinstance(x,dict) else x).upper() in cfg['locations']['countries'] for x in codes):return 'TARGET'
 city,_,code=parse_location(j)
 if code:return 'TARGET' if code in cfg['locations']['countries'] else 'OUTSIDE'
 loc=norm(j.get('location',''));desc=norm((j.get('description') or '')[:6500])
 if any(x in desc for x in ('must reside in the united states','must be based in the united states','only candidates in the united states','us based candidates only')):return 'OUTSIDE'
 if 'remote' in loc or 'worldwide' in loc or 'anywhere' in loc or j.get('work_mode')=='remote':
  return 'REMOTE - eligibility unverified' if cfg['locations'].get('allow_remote_unknown') else 'OUTSIDE'
 return 'LOCATION UNKNOWN' if cfg['locations'].get('accept_location_unknown') else 'OUTSIDE'
def interest(j,cfg):
 title=j.get('title') or ''
 if not title:return False,'MISSING TITLE'
 opts=cfg['interest']
 if any(match(x,title) for x in opts['exclude_any']):return False,'EXCLUDED ROLE'
 patterns=opts['include_any']+[q for group in cfg['searches'] for q in group['queries']]
 if opts.get('strict_title_match') and not any(match(x,title) for x in patterns):return False,'OUTSIDE TARGET ROLES'
 loc=location_fit(j,cfg)
 return (loc!='OUTSIDE'),loc

def himalayas_search(q):
 obj=fetch_json('https://himalayas.app/jobs/api/search',{'q':q,'sort':'recent','page':1})
 out=[]
 for j in obj.get('jobs',[]):
  uid=str(j.get('guid') or j.get('applicationLink') or '');limits=j.get('locationRestrictions') or []
  if not uid:continue
  countries=[str(x.get('code','') if isinstance(x,dict) else x).upper() for x in limits]
  out.append({'id':'himalayas:'+hashlib.sha256(uid.encode()).hexdigest()[:20], 'source':'himalayas','source_ref':uid,'url':j.get('applicationLink') or '',
  'title':j.get('title') or '', 'company':j.get('companyName') or '', 'location':'Remote - '+(', '.join(countries) if countries else 'Worldwide'),
  'countries':countries,'cities':[],'work_mode':'remote','description':html_text(j.get('description')),
  'posted_at':j.get('pubDate') or '', 'data_quality':'Himalayas; remote geo and timezone require independent verification'})
 return out

def jobicy_search(q):
 obj=fetch_json('https://jobicy.com/api/v2/remote-jobs',{'count':100,'tag':q[:50]});out=[]
 for j in obj.get('jobs',[]):
  uid=str(j.get('id') or '')
  if not uid:continue
  out.append({'id':'jobicy:'+uid,'source':'jobicy','source_ref':uid,'url':j.get('url') or '',
   'title':j.get('jobTitle') or '', 'company':j.get('companyName') or '', 'location':'Remote - '+str(j.get('jobGeo') or 'Unknown'),
   'countries':[],'cities':[],'work_mode':'remote','description':html_text(j.get('jobDescription') or j.get('jobExcerpt')),
   'posted_at':j.get('pubDate') or '', 'data_quality':'Jobicy public source; original ATS link may be unavailable'})
 return out
