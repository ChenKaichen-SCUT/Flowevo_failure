import hashlib,json,os
from pathlib import Path

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'))

def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()

def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8') as f:
        f.write(canonical(obj));f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
