"""Scan worktree, staged diff and every reachable Git blob, including zstd bodies.

Never print matched credentials. Intended before and after the final commit.
"""
import argparse,subprocess,re,io,json,hashlib
from pathlib import Path
import zstandard as zstd

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',default='.');p.add_argument('--api-key-file',required=True);p.add_argument('--secret-file',action='append',default=[]);a=p.parse_args();repo=Path(a.repo).resolve()
    secrets=[Path(path).read_bytes().strip() for path in [a.api_key_file]+a.secret_file]
    patterns=[rb'gh[pousr]_[A-Za-z0-9]{25,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',rb'sk-[A-Za-z0-9]{24,}']
    counts={'worktree_files':0,'git_blobs':0,'compressed_bodies':0}
    def plain(data,label):
        if any(s and s in data for s in secrets) or any(re.search(pat,data) for pat in patterns):raise RuntimeError('CREDENTIAL_MATCH '+label)
    def scan(data,label):
        plain(data,label)
        if data.startswith(b'\x28\xb5\x2f\xfd'):
            counts['compressed_bodies']+=1
            with zstd.ZstdDecompressor().stream_reader(io.BytesIO(data)) as r:
                overlap=b''
                while True:
                    chunk=r.read(1024*1024)
                    if not chunk:break
                    body=overlap+chunk;plain(body,label+' [decompressed]');overlap=body[-max(1024,max(map(len,secrets))):]
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    names=set(git('ls-files','-z').decode().split('\0'))|set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
    forbidden={'api.txt','.env','test_manifest.private.jsonl'}
    for name in sorted(names-{''}):
        path=repo/name
        if path.name in forbidden or {'secrets','runs-private','vendor'}.intersection(Path(name).parts):raise RuntimeError('FORBIDDEN_PUBLIC_PATH '+name)
        if path.is_file():scan(path.read_bytes(),name);counts['worktree_files']+=1
    scan(git('diff','--cached','--binary'),'staged diff')
    object_ids=git('rev-list','--objects','HEAD').decode().splitlines()
    proc=subprocess.Popen(['git','-C',str(repo),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    for line in object_ids:
        oid=line.split(' ',1)[0];proc.stdin.write((oid+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().split();size=int(header[2]);data=proc.stdout.read(size);assert proc.stdout.read(1)==b'\n'
        if header[1]=='blob':scan(data,'history object '+oid);counts['git_blobs']+=1
    proc.stdin.close();proc.wait();assert proc.returncode==0
    result={'status':'PASSED','head':git('rev-parse','HEAD').decode().strip(),'counts':counts,'actual_key_bytes_scanned':True,'staged_diff_scanned':True,'reachable_history_scanned':True,'decompressed_payloads_scanned':True,'matched_secret_material_printed':False}
    print(json.dumps(result))
if __name__=='__main__':main()
