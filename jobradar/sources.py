"""Public, read-only job discovery adapters. Never submit applications."""
from __future__ import annotations
import json, logging, re, time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from html import unescape

LOG=logging.getLogger('jobradar')
UA='JobRadar/1.0 (personal research; contact via official site)'


def fetch_json(url, params=None, timeout=25):
    if params:
        url = url + ('&' if '?' in url else '?') + urlencode(params)
    if urlsplit(url).scheme != 'https':
        raise ValueError('Only HTTPS remote sources are allowed')
    for attempt in range(3):
        try:
            req = Request(url, headers={'User-Agent':UA,'Accept':'application/json'})
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read(12_000_000).decode('utf-8'))
        except HTTPError as e:
            if e.code in (429,500,502,503,504) and attempt<2:
                delay=min(12,2**attempt+1)
                LOG.warning('HTTP %s; retrying in %ss: %s',e.code,delay,urlsplit(url).netloc)
                time.sleep(delay)
                continue
            raise
        except (URLError,TimeoutError):
            if attempt<2:
                time.sleep(2**attempt)
                continue
            raise


def html_text(s):
    if not s:return ''
    s=re.sub(r'<(?:br\s*/?|/p|/li|/div|/h[1-6])\s*>','\n',str(s),flags=re.I)
    s=re.sub(r'<[^>]*>',' ',s)
    return re.sub(r'\n{3,}','\n\n',unescape(s)).strip()


def norm_freehire(j):
    slug = str(j.get('public_slug') or '').strip()
    if not slug:return None
    return {'id':'freehire:'+slug,'source':'freehire','source_ref':slug,
            'url':j.get('apply_url') or j.get('url') or 'https://freehire.me/jobs/'+slug,
            'catalog_url':'https://freehire.me/jobs/'+slug,
            'title':j.get('title') or '', 'company':j.get('company') or '',
            'location':j.get('location') or '', 'countries':j.get('countries') or [],
            'cities':j.get('cities') or [],'work_mode':j.get('work_mode') or '',
            'description':html_text(j.get('description') or ''),
            'posted_at':j.get('posted_at') or '', 'source_first_seen':j.get('created_at') or '',
            'closed_at':j.get('closed_at'),'external_id':j.get('external_id') or '',
            'data_quality':'catalogue; verify official link'}


def freehire_search(cfg, search_text):
    root=cfg['api_base'].rstrip('/')
    if not root.startswith('https://freehire.me/api/v1') and not root.startswith('http://127.0.0.1:'):
        raise ValueError('Unexpected API host in config')
    # Agents endpoint returns the full vacancy description rather than a preview.
    params={'q':('\"'+search_text+'\"' if ' ' in search_text.strip() else search_text),'q_fields':'title','open_within_days':cfg.get('lookback_days',14),
            'description_format':'markdown','sort':'created_at','order':'desc',
            'limit':min(100,max(1,cfg.get('max_per_query',100))),'offset':0}
    found=[]
    while True:
        r=fetch_json(root+'/agent/jobs/search',params)
        if not isinstance(r,dict) or not isinstance(r.get('data'),list):
            raise ValueError('Invalid freehire search response')
        ignored=(r.get('meta') or {}).get('ignored_params') or []
        if ignored:
            LOG.warning('freehire ignored params: %s',ignored)
        for item in r['data']:
            if x:=norm_freehire(item):found.append(x)
        total=int((r.get('meta') or {}).get('total',len(found)))
        params['offset']+=len(r['data'])
        if not r['data'] or params['offset']>=min(total,10000) or params['offset']>=cfg.get('max_per_query',100):
            break
        time.sleep(0.4)
    return found


def ats_board(board):
    """Direct, publicly documented ATS job feeds. board is a tenant identifier, never URL."""
    if not board.get('enabled',False):return []
    ident=board.get('board','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,100}',ident):
        raise ValueError('Invalid ATS board tenant slug')
    provider=board.get('provider')
    company=board.get('company',ident)
    if provider=='greenhouse':
        data=fetch_json('https://boards-api.greenhouse.io/v1/boards/'+ident+'/jobs',{'content':'true'})
        out=[]
        for j in data.get('jobs',[]):
            loc=(j.get('location') or {}).get('name','')
            out.append({'id':f'greenhouse:{ident}:{j.get("id")}', 'source':'greenhouse','source_ref':str(j.get('id')),
                'url':j.get('absolute_url') or '', 'catalog_url':'','title':j.get('title',''),
                'company':company,'location':loc,'countries':[],'cities':[],'work_mode':'',
                'description':html_text(j.get('content') or ''),'posted_at':j.get('updated_at') or '',
                'source_first_seen':'','closed_at':None,'external_id':str(j.get('id')),
                'data_quality':'official board; updated_at is not original posted date'})
        return out
    if provider=='lever':
        data=fetch_json('https://api.lever.co/v0/postings/'+ident,{'mode':'json'})
        out=[]
        for j in data:
            cats=j.get('categories') or {}
            out.append({'id':f'lever:{ident}:{j.get("id")}', 'source':'lever','source_ref':str(j.get('id')),
                'url':j.get('hostedUrl') or j.get('applyUrl') or '', 'catalog_url':'',
                'title':j.get('text',''), 'company':company,'location':cats.get('location',''),
                'countries':[],'cities':[],'work_mode':str(j.get('workplaceType','')),
                'description':html_text(j.get('descriptionPlain') or j.get('description') or ''),
                'posted_at':'','source_first_seen':'','closed_at':None,'external_id':str(j.get('id')),
                'data_quality':'official Lever board'})
        return out
    if provider=='ashby':
        data=fetch_json('https://api.ashbyhq.com/posting-api/job-board/'+ident,{'includeCompensation':'true'})
        out=[]
        for j in data.get('jobs',[]):
            out.append({'id':f'ashby:{ident}:{j.get("id") or j.get("jobUrl")}', 'source':'ashby',
                'source_ref':str(j.get('id') or ''), 'url':j.get('jobUrl') or j.get('applyUrl') or '',
                'catalog_url':'','title':j.get('title',''), 'company':company,
                'location':j.get('location') or '', 'countries':[], 'cities':[],
                'work_mode':'remote' if j.get('isRemote') else '',
                'description':html_text(j.get('descriptionPlain') or j.get('descriptionHtml') or ''),
                'posted_at':j.get('publishedAt') or '', 'source_first_seen':'','closed_at':None,
                'external_id':str(j.get('id') or ''),'data_quality':'official Ashby board'})
        return out
    raise ValueError('Unsupported ATS provider')


def jobspy_search(cfg, query):
    if not cfg['jobspy']['enabled']:return []
    try:
        from jobspy import scrape_jobs
    except ImportError:
        raise RuntimeError('Install optional: pip install -r requirements-jobspy.txt')
    out=[]
    for location in ('Istanbul, Turkey','Riyadh, Saudi Arabia','Dubai, United Arab Emirates','Doha, Qatar'):
        df=scrape_jobs(site_name=cfg['jobspy']['sites'],search_term=query,location=location,
            results_wanted=cfg['jobspy']['results_per_search'],hours_old=72,
            country_indeed='Turkey' if 'Turkey' in location else ('Saudi Arabia' if 'Saudi' in location else 'United Arab Emirates' if 'Dubai' in location else 'Qatar'))
        for _, r in df.iterrows():
            d=r.to_dict()
            uri=str(d.get('job_url') or '')
            if not uri.startswith('https://'):continue
            out.append({'id':'jobspy:'+str(d.get('id') or uri),'source':'jobspy','source_ref':str(d.get('id') or uri),
               'url':uri,'catalog_url':'','title':str(d.get('title') or ''),'company':str(d.get('company') or ''),
               'location':str(d.get('location') or location),'countries':[],'cities':[],'work_mode':'',
               'description':str(d.get('description') or ''),'posted_at':str(d.get('date_posted') or ''),
               'source_first_seen':'','closed_at':None,'external_id':'','data_quality':'aggregator; verify official ATS'})
    return out
