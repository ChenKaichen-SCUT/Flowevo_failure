"""Download public encrypted assets; optional GitHub token, never model APIs."""
import argparse, concurrent.futures, hashlib, json, os, time, urllib.request
from pathlib import Path

BASE='https://api.github.com/repos/ChenKaichen-SCUT/Flowevo_failure'
TAG='server-backup-20261117'
class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        result=super().redirect_request(req,fp,code,msg,headers,newurl)
        if result:result.remove_header('Authorization')
        return result
def api_headers(binary=False):
    result={'Accept':'application/octet-stream' if binary else 'application/vnd.github+json','User-Agent':'FlowEvo-Restore'}
    if os.environ.get('GITHUB_TOKEN'):result['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    return result
OPENER=urllib.request.build_opener(Redirect())
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def download(asset,path):
    error=None
    for attempt in range(3):
        try:
            # API download avoids depending on the HTML page and follows its signed redirect.
            url=asset['url']+'?download=1&retry='+str(attempt)
            req=urllib.request.Request(url,headers=api_headers(True))
            temporary=path.with_name(path.name+'.partial')
            with OPENER.open(req,timeout=120) as response,temporary.open('wb') as f:
                while True:
                    b=response.read(1024*1024)
                    if not b:break
                    f.write(b)
            if temporary.stat().st_size!=asset['size']:raise ValueError('Downloaded size mismatch')
            expected=asset.get('digest','')
            if expected.startswith('sha256:') and sha(temporary)!=expected[7:]:raise ValueError('GitHub asset digest mismatch')
            os.replace(temporary,path);return
        except Exception as exc:error=exc;time.sleep(1+attempt)
    raise RuntimeError('Cannot download '+asset['name']) from error
def main():
    p=argparse.ArgumentParser();p.add_argument('--dest',required=True);a=p.parse_args();dest=Path(a.dest).resolve();dest.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(BASE+'/releases/tags/'+TAG,headers=api_headers())
    with OPENER.open(req,timeout=30) as response:release=json.load(response)
    assets={r['name']:r for r in release['assets']}
    download(assets['backup_manifest.json'],dest/'backup_manifest.json')
    manifest=json.loads((dest/'backup_manifest.json').read_text(encoding='utf8'))
    def one(row):
        name=row['name']
        if Path(name).name!=name or not name.startswith('flowevo-server-snapshot.part'):raise ValueError('Unsafe asset path')
        path=dest/name
        if not path.exists() or path.stat().st_size!=row['size'] or sha(path)!=row['sha256']:download(assets[name],path)
        if sha(path)!=row['sha256']:raise ValueError('Snapshot manifest digest mismatch')
        print('Verified '+name,flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(one,manifest['parts']))
    print('All encrypted parts verified. Use your separately saved RECOVERY_KEY.txt to restore.')
if __name__=='__main__':main()
