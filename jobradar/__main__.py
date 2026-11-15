import argparse,sys,traceback
from pathlib import Path
from .core import ROOT,CONFIG,PROMPT,scan,list_jobs,mark,import_history,export_csv,dashboard,connect,cfg_load
from .generator import evaluate,import_jd

def main():
    p=argparse.ArgumentParser(prog='jobradar',description='Manual targeted job discovery + local model v4.1 drafts')
    sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('scan',help='run a single network scan now')
    sub.add_parser('run',help='scan on demand, generate dashboard, and open it')
    sub.add_parser('doctor',help='verify Ollama and local model')
    s=sub.add_parser('add-job',help='register a job URL without scraping');s.add_argument('--url',required=True);s.add_argument('--title',required=True);s.add_argument('--company',required=True);s.add_argument('--location',required=True);s.add_argument('--jd-file')
    s=sub.add_parser('list',help='show seen openings');s.add_argument('--limit',type=int,default=40);s.add_argument('--status')
    s=sub.add_parser('report',help='generate local offline dashboard');s.add_argument('--open',action='store_true')
    s=sub.add_parser('mark',help='set exact application status');s.add_argument('id');s.add_argument('status');s.add_argument('--note',default='')
    s=sub.add_parser('history-import',help='import actual application records CSV');s.add_argument('csv')
    s=sub.add_parser('export',help='export seen jobs to CSV');s.add_argument('--output',default=str(ROOT/'output'/'jobs.csv'))
    s=sub.add_parser('evaluate',help='evaluate against active prompt, draft package only for APPLY');s.add_argument('id');s.add_argument('--force-reviewed',action='store_true',help='after human-reviewed material change for previously rejected application');s.add_argument('--reason',default='',help='at least 20 chars describing changed candidate evidence/requisition')
    s=sub.add_parser('jd',help='replace incomplete JD with actual full job description');s.add_argument('id');s.add_argument('txt')
    sub.add_parser('prompt',help='display currently active prompt and hash')
    s=sub.add_parser('prompt-set',help='replace prompt with versioned Markdown file; keep archive');s.add_argument('markdown')
    s=sub.add_parser('watch-add',help='append a title query under custom searches');s.add_argument('phrase')
    s=sub.add_parser('watch-remove',help='remove custom title phrase');s.add_argument('phrase')
    sub.add_parser('watch-list',help='show current monitored title phrases')
    sub.add_parser('status',help='database and scan status')
    a=p.parse_args()
    try:
        if a.cmd=='doctor':
            from .doctor import doctor
            if not doctor():sys.exit(1)
        elif a.cmd=='run':
            result=scan()
            import webbrowser
            target=dashboard();webbrowser.open(target.resolve().as_uri())
            if result['errors']:print('PARTIAL SCAN ERROR:',result['errors'][:4])
        elif a.cmd=='add-job':
            from .core import record,compare_url
            import hashlib
            if not a.url.startswith('https://'):raise ValueError('Provide an HTTPS URL')
            jd=Path(a.jd_file).read_text(encoding='utf-8') if a.jd_file else ''
            jid='manual:'+hashlib.sha256(compare_url(a.url).encode()).hexdigest()[:20]
            item={'id':jid,'source':'manual','source_ref':a.url,'url':a.url,'title':a.title,'company':a.company,'location':a.location,'description':jd,'data_quality':'user supplied; verify official listing'}
            con=connect();result=record(con,item,['Manual'],baseline=False);con.commit();con.close()
            print('Imported:',result,jid)
        elif a.cmd=='scan':
            result=scan()
            if result['errors']:sys.exit(2)
        elif a.cmd=='list':list_jobs(a.limit,a.status)
        elif a.cmd=='mark':mark(a.id,a.status,a.note)
        elif a.cmd=='history-import':import_history(a.csv)
        elif a.cmd=='export':export_csv(a.output)
        elif a.cmd=='jd':import_jd(a.id,a.txt)
        elif a.cmd=='evaluate':evaluate(a.id,a.force_reviewed,a.reason)
        elif a.cmd=='report':
            target=dashboard()
            if a.open:
                import webbrowser;webbrowser.open(target.as_uri())
        elif a.cmd=='watch-list':
            for g in cfg_load()['searches']:
                print(g['name']+': '+', '.join(g['queries']))
        elif a.cmd in ('watch-add','watch-remove'):
            import json
            if not a.phrase.strip() or len(a.phrase)>120:raise ValueError('phrase must be 1-120 characters')
            cfg=cfg_load()
            g=next((x for x in cfg['searches'] if x['name']=='Custom'),None)
            if g is None:
                g={'name':'Custom','queries':[]};cfg['searches'].append(g)
            if a.cmd=='watch-add' and a.phrase not in g['queries']:g['queries'].append(a.phrase)
            if a.cmd=='watch-remove' and a.phrase in g['queries']:g['queries'].remove(a.phrase)
            CONFIG.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print('Updated watches:',a.phrase)
        elif a.cmd=='prompt-set':
            import hashlib,shutil
            source=Path(a.markdown).expanduser().resolve()
            if not source.is_file():raise ValueError('No such markdown file: '+str(source))
            body=source.read_text(encoding='utf-8')
            import re
            if not re.search(r'v\d+\.\d+',body[:700],flags=re.I) or len(body)<3000:
                raise ValueError('File does not resemble a complete versioned master prompt (>=3000 chars and version header)')
            archive=PROMPT.parent/'archive';archive.mkdir(exist_ok=True)
            oldsha=hashlib.sha256(PROMPT.read_bytes()).hexdigest()
            shutil.copy2(PROMPT,archive/('ACTIVE_'+oldsha[:12]+'.md'))
            if source!=PROMPT:shutil.copy2(source,PROMPT)
            print('Activated:',source.name,'SHA256:',hashlib.sha256(PROMPT.read_bytes()).hexdigest())
        elif a.cmd=='prompt':
            import hashlib
            body=PROMPT.read_bytes()
            print(f'ACTIVE: {PROMPT}\nSHA256: {hashlib.sha256(body).hexdigest()}\nFirst line: {body.decode("utf-8").splitlines()[0]}')
        elif a.cmd=='status':
            con=connect()
            print('Repo:',ROOT,'\nConfig:',CONFIG,'\nActive prompt:',PROMPT)
            for row in con.execute('SELECT status,count(*) n FROM jobs GROUP BY status'):
                print(row['status'],row['n'])
            row=con.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 1').fetchone()
            if row:print('Last scan:',dict(row))
            else:print('No scan yet')
            con.close()
    except (ValueError,RuntimeError,OSError) as e:
        print('ERROR:',e,file=sys.stderr)
        sys.exit(1)
if __name__=='__main__':main()
