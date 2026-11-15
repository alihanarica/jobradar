import json,sys,subprocess,urllib.request,urllib.error
from .core import cfg_load,PROMPT
def doctor():
 c=cfg_load();opt=c['llm'];print('Provider:',opt['provider'],'| Model:',opt['model'],'| Cloud allowed:',opt['allow_cloud']);print('Active prompt:',len(PROMPT.read_bytes()),'bytes')
 if sys.platform=='darwin':
  try:
   mem=int(subprocess.check_output(['sysctl','-n','hw.memsize'],text=True).strip())/1024**3
   print('Mac unified memory:',round(mem,1),'GiB')
   if mem<16:print('WARNING: 8B model + 32K context may exceed available memory.')
  except Exception:pass
 try:
  with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=5) as r:out=json.load(r)
  names=[m.get('name','') for m in out.get('models',[])]
  print('Ollama online. Models:',names)
  if opt['model'] not in names:print('Model missing. Run: ollama pull',opt['model']);return False
  return True
 except Exception as e:
  print('Ollama unreachable. Install/open https://ollama.com/download, then: ollama pull',opt['model']);print(e);return False
