from __future__ import annotations
import csv, hashlib, json, re, sqlite3, logging, shutil, subprocess, sys, webbrowser
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from .sources import freehire_search,ats_board,jobspy_search

LOG=logging.getLogger('jobradar')
ROOT=Path(__file__).resolve().parent.parent
CONFIG=ROOT/'config.json'
DB=ROOT/'data'/'jobs.sqlite3'
PROMPT=ROOT/'prompts'/'ACTIVE.md'
ALLOWED={'BASELINE','DISCOVERED','EVALUATED','PREPARED ONLY','SUBMITTED CONFIRMED','PREVIOUS REJECTION','ACTIVE PROCESS','WITHDRAWN','EXPLICIT STOP REQUEST','SKIP','CLARIFY','OFFER','CLOSED'}

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def cfg_load():
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    assert isinstance(cfg['searches'],list)
    return cfg

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.executescript('''
    CREATE TABLE IF NOT EXISTS jobs(
      id TEXT PRIMARY KEY, source TEXT NOT NULL, source_ref TEXT,
      url TEXT, comparison_url TEXT, catalog_url TEXT, title TEXT, company TEXT, location TEXT,
      countries TEXT, cities TEXT, work_mode TEXT, description TEXT, posted_at TEXT,
      source_first_seen TEXT, local_first_seen TEXT, local_last_seen TEXT, changed_at TEXT,
      description_sha256 TEXT, status TEXT DEFAULT 'DISCOVERED',
      requisition TEXT DEFAULT '', matches TEXT DEFAULT '[]', priority TEXT DEFAULT 'REVIEW',
      data_quality TEXT, prompt_sha256 TEXT DEFAULT '', package_dir TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY AUTOINCREMENT,started TEXT,finished TEXT,success INTEGER,found INTEGER,added INTEGER,changed INTEGER,errors TEXT);
    CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,at TEXT,kind TEXT,details TEXT);
    CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,company TEXT,title TEXT,location TEXT,requisition TEXT,comparison_url TEXT,status TEXT,at TEXT,notes TEXT);
    CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs(local_first_seen);
    CREATE INDEX IF NOT EXISTS idx_activity_job ON activity(job_id);
    ''')
    return con

def compare_url(raw):
    if not raw:return ''
    p=urlsplit(raw.strip())
    if p.scheme not in ('http','https'):return ''
    clean=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True)
           if not (k.lower().startswith('utm_') or k.lower() in ('ref','source','trk','tracking','gh_src','lever-source','fbclid','gclid'))]
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path.rstrip('/'),urlencode(clean),'')).strip()

def normalize(s):
    return re.sub(r'\s+',' ',re.sub(r'[^\w ]+',' ',(s or '').lower(),flags=re.UNICODE)).strip()

def location_fit(job,cfg):
 from .v2_support import location_fit as f
 return f(job,cfg)
def interest(job,cfg):
 from .v2_support import interest as f
 return f(job,cfg)

def shortlist_history(con,job):
    """Flag plausible duplicates; never assume different req is same or a reapplication is safe."""
    url=compare_url(job.get('url',''))
    norm_c=normalize(job.get('company',''))
    norm_t=normalize(job.get('title',''))
    records=[]
    for h in con.execute("SELECT id,company,title,requisition,comparison_url,status,at FROM history"):
        same_url=bool(url and h['comparison_url'] and url==h['comparison_url'])
        near=(norm_c and norm_c==normalize(h['company']) and norm_t==normalize(h['title']))
        if same_url or near:records.append(dict(h)|{'match_type':'EXACT_URL' if same_url else 'CLOSE_TITLE'})
    # Also jobs with manual marks, even if they weren't imported into history.
    for h in con.execute("SELECT id,company,title,comparison_url,status FROM jobs WHERE status IN ('SUBMITTED CONFIRMED','PREVIOUS REJECTION','ACTIVE PROCESS','WITHDRAWN','EXPLICIT STOP REQUEST')"):
        if h['id']==job['id']:continue
        same_url=bool(url and h['comparison_url'] and url==h['comparison_url'])
        near=(norm_c and norm_c==normalize(h['company']) and norm_t==normalize(h['title']))
        if same_url or near:records.append(dict(h)|{'match_type':'EXACT_URL' if same_url else 'CLOSE_TITLE'})
    return records

def event(con,id,kind,details=''):
    con.execute('INSERT INTO activity(job_id,at,kind,details) VALUES(?,?,?,?)',(id,now(),kind,details))

def record(con,job,tags=None,baseline=False):
    ok,fit=interest(job,cfg_load())
    if not ok:return 'filtered'
    jid=str(job.get('id') or '')
    if not jid or not job.get('title'):return 'filtered'
    descr=job.get('description') or ''
    h=hashlib.sha256(descr.encode('utf-8')).hexdigest()
    prev=con.execute('SELECT id, description_sha256,status FROM jobs WHERE id=?',(jid,)).fetchone()
    tags=tags or []
    if prev:
        changed=prev['description_sha256']!=h and bool(descr)
        if changed:
            con.execute('UPDATE jobs SET description=?,description_sha256=?,changed_at=?,local_last_seen=?,matches=?,data_quality=? WHERE id=?',
                (descr,h,now(),now(),json.dumps(tags,ensure_ascii=False),job.get('data_quality',''),jid))
            event(con,jid,'JD_CHANGED','Source description content changed, not proof of new requisition')
        else:
            con.execute('UPDATE jobs SET local_last_seen=? WHERE id=?',(now(),jid))
        return 'changed' if changed else 'known'
    flag='BASELINE' if baseline else 'DISCOVERED'
    cmp=compare_url(job.get('url',''))
    con.execute('''INSERT INTO jobs(id,source,source_ref,url,comparison_url,catalog_url,title,company,location,
            countries,cities,work_mode,description,posted_at,source_first_seen,local_first_seen,
            local_last_seen,changed_at,description_sha256,status,requisition,matches,priority,data_quality)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (jid,job.get('source',''),job.get('source_ref',''),job.get('url',''),cmp,job.get('catalog_url',''),
             job.get('title',''),job.get('company',''),job.get('location',''),
             json.dumps(job.get('countries') or []),json.dumps(job.get('cities') or []),job.get('work_mode',''),descr,
             job.get('posted_at',''),job.get('source_first_seen',''),now(),now(),'',h,flag,job.get('external_id',''),
             json.dumps(tags,ensure_ascii=False),fit,job.get('data_quality','')))
    event(con,jid,'BASELINE' if baseline else 'DISCOVERED','; '.join(tags))
    duplicates=shortlist_history(con,job)
    if duplicates:event(con,jid,'HISTORY_REVIEW',json.dumps(duplicates,ensure_ascii=False)[:2500])
    return 'baseline' if baseline else 'new'

def scan(quiet=False):
 from .v2_support import himalayas_search,jobicy_search
 cfg=cfg_load();con=connect();start=now()
 first=con.execute('SELECT COUNT(*) FROM runs WHERE found>0').fetchone()[0]==0
 stats={'found':0,'new':0,'baseline':0,'changed':0,'known':0,'filtered':0,'errors':[]}
 refs={}
 def collect(jobs,source):
  for job in jobs:
   stats['found']+=1
   if job.get('id'):refs.setdefault(job['id'],(job,[]))[1].append(source)
 queries=[q for group in cfg['searches'] for q in group['queries']][:cfg.get('max_queries_per_scan',35)]
 if cfg.get('sources',{}).get('freehire'):
  for i,q in enumerate(queries,1):
   if not quiet:print(f'[{i}/{len(queries)}] freehire: {q}',flush=True)
   try:collect(freehire_search(cfg,q),'freehire')
   except Exception as e:stats['errors'].append(f'freehire {q}: {e}')
 for b in cfg.get('ats_boards',[]):
  if b.get('enabled'):
   try:collect(ats_board(b),'ATS '+b.get('company',''))
   except Exception as e:stats['errors'].append(f'ATS {b.get("board")}: {e}')
 for name,enabled,fun in [('Himalayas',cfg.get('sources',{}).get('himalayas'),himalayas_search),('Jobicy',cfg.get('sources',{}).get('jobicy'),jobicy_search)]:
  if enabled:
   for q in ('Chief of Staff','AI Transformation','Commercial Director'):
    try:collect(fun(q),name)
    except Exception as e:stats['errors'].append(f'{name} {q}: {e}')
 if not refs and stats['errors']:
  con.execute('INSERT INTO runs(started,finished,success,found,added,changed,errors) VALUES(?,?,?,?,?,?,?)',(start,now(),0,0,0,0,json.dumps(stats['errors'])));con.commit();con.close()
  if not quiet:print('SCAN FAILED',stats['errors'][:3]);return stats
 for job,tags in refs.values():stats[record(con,job,list(set(tags)),baseline=first)]+=1
 con.execute('INSERT INTO runs(started,finished,success,found,added,changed,errors) VALUES(?,?,?,?,?,?,?)',(start,now(),int(not stats['errors']),stats['found'],stats['new'],stats['changed'],json.dumps(stats['errors'])))
 con.commit();con.close()
 if not quiet:print('SCAN',json.dumps(stats,ensure_ascii=False))
 return stats

def list_jobs(limit=30,status=None):
    con=connect()
    sql='SELECT id,title,company,location,priority,status,local_first_seen,url FROM jobs'
    vals=[]
    if status:sql+=' WHERE status=?';vals.append(status)
    sql+=' ORDER BY local_first_seen DESC LIMIT ?';vals.append(limit)
    rows=con.execute(sql,vals).fetchall()
    con.close()
    for r in rows:
        print(f'{r["id"]} | {r["status"][:18]:18} | {r["company"][:22]:22} | {r["title"][:45]:45} | {r["location"][:30]:30}')
    return rows

def get_job(con,key):
    row=con.execute('SELECT * FROM jobs WHERE id=?',(key,)).fetchone()
    if row:return row
    matches=con.execute('SELECT * FROM jobs WHERE id LIKE ? LIMIT 2',(key+'%',)).fetchall()
    if len(matches)==1:return matches[0]
    raise ValueError('Job not found or ambiguous ID; use `list` to get full ID')

def mark(key,status,note=''):
    status=status.upper().strip()
    if status not in ALLOWED:raise ValueError('Invalid status: '+status)
    if status=='SUBMITTED CONFIRMED' and not note:
        raise ValueError('To mark SUBMITTED CONFIRMED you must supply --note with actual submission evidence/date.')
    con=connect();job=get_job(con,key)
    con.execute('UPDATE jobs SET status=? WHERE id=?',(status,job['id']))
    event(con,job['id'],'STATUS',json.dumps({'status':status,'note':note},ensure_ascii=False))
    if status in ('SUBMITTED CONFIRMED','PREVIOUS REJECTION','ACTIVE PROCESS','WITHDRAWN','EXPLICIT STOP REQUEST'):
        con.execute('INSERT INTO history(company,title,location,requisition,comparison_url,status,at,notes) VALUES(?,?,?,?,?,?,?,?)',
                (job['company'],job['title'],job['location'],job['requisition'],job['comparison_url'],status,now(),note))
    con.commit();con.close();print('Status updated:',job['id'],status)

def import_history(path):
    con=connect();n=0
    with open(path,newline='',encoding='utf-8-sig') as f:
        for h in csv.DictReader(f):
            status=h.get('status','HISTORY UNKNOWN').upper()
            if status not in ALLOWED and status!='HISTORY UNKNOWN':raise ValueError('History invalid status: '+status)
            existing=con.execute('SELECT 1 FROM history WHERE company=? AND title=? AND status=? AND at=? LIMIT 1',
                   (h.get('company',''),h.get('title',''),status,h.get('date','') or '')).fetchone()
            if existing:continue
            con.execute('''INSERT INTO history(company,title,location,requisition,comparison_url,status,at,notes)
                         VALUES(?,?,?,?,?,?,?,?)''',
                        (h.get('company',''),h.get('title',''),h.get('location',''),h.get('requisition',''),
                         compare_url(h.get('url','')),status,h.get('date','') or now(),h.get('notes','')))
            n+=1
    con.commit();con.close();print(n,'history rows imported')

def export_csv(dest):
    con=connect();rows=con.execute('SELECT id,company,title,location,status,priority,url,posted_at,source_first_seen,local_first_seen,matches FROM jobs ORDER BY local_first_seen DESC').fetchall();con.close()
    with open(dest,'w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f)
        writer.writerow(['id','company','title','location','status','location_review','url','source_posted_at','freehire_first_seen','local_first_seen','matches'])
        for r in rows:writer.writerow(tuple(r))
    print('Saved',dest)

def dashboard(dest=None):
 from .dashboard_v2 import dashboard as run_dashboard
 return run_dashboard(dest)
