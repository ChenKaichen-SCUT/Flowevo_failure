"""Explicit PUBLIC allowlist; API-key byte scan includes every export payload."""
import argparse,json,hashlib,sqlite3,re
from pathlib import Path
import zstandard as zstd
from flowevo_sw.checkpointing import read_json,atomic_json,canonical

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--api-key-file',required=True);p.add_argument('--runs',nargs='+',required=True);a=p.parse_args();root=Path(a.root).resolve();key=Path(a.api_key_file).read_bytes().strip();out=root/'output/results';out.mkdir(exist_ok=True,parents=True);mapping=[]
    def safe(b):
        if key and key in b:raise RuntimeError('SECRET_FOUND_IN_EXPORT')
        if re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',b):raise RuntimeError('CREDENTIAL_PATTERN_FOUND')
        return b
    def write_zst(name,records):
        h=hashlib.sha256()
        with (out/name).open('wb') as raw:
            with zstd.ZstdCompressor(level=9).stream_writer(raw) as z:
                for record in records:
                    b=safe((canonical(record)+'\n').encode());h.update(b);z.write(b)
        return h.hexdigest()
    episodes=[]
    for f in sorted((root/'runs-private/episodes').glob('*.json')):
        if '.prefix.' in f.name or not any(f.name.startswith(r+'.') for r in a.runs):continue
        d=read_json(f)
        if d.get('status') not in ('EPISODE_LOCKED','MISSING'):continue
        episodes.append(d);mapping.append({'private_file':'episodes/'+f.name,'private_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'public_record_id':d['job_id'],'exposed_test':d['spec']['split']=='test'})
    write_zst('episodes_full_sanitized.jsonl.zst',episodes)
    write_zst('steps.jsonl.zst',({'job_id':d['job_id'],'exposed_test':d['spec']['split']=='test',**s} for d in episodes for s in d.get('steps',[])))
    with sqlite3.connect(f'file:{root/"runs-private/ledger.sqlite"}?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row;ledger=[dict(r) for r in c.execute('SELECT * FROM requests ORDER BY started')]
    def requests():
        for row in ledger:
            rid=row['id'];request_path=root/'runs-private/requests'/(rid+'.request.json');response_path=root/'runs-private/requests'/(rid+'.json')
            request=read_json(request_path) if request_path.exists() else None;response=read_json(response_path) if response_path.exists() else None
            # Stored payloads have no headers or credentials, and no private evaluator fields.
            row=dict(row);row['response_path']=response_path.name
            record={'ledger':row,'request':request,'response':response}
            for path in (request_path,response_path):
                if path.exists():mapping.append({'private_file':'requests/'+path.name,'private_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'public_record_id':rid})
            yield record
    request_hash=write_zst('requests_sanitized.jsonl.zst',requests())
    atomic_json(out/'export_mapping.json',{'records':mapping,'requests_decompressed_sha256':request_hash,'note':'Completed TEST trajectories are exposed; unused future TEST material excluded. Only own generated logs are exported, not vendor datasets/JARs.'})
    # Publish train/dev metadata and split hashes; never the full unused TEST manifest.
    dest=root/'output/data/manifests';dest.mkdir(parents=True,exist_ok=True)
    for name in ('all_tasks.json','train.jsonl','dev.jsonl','exclusions.jsonl','split_hashes.json'):
        data=safe((root/'data/manifests'/name).read_bytes());(dest/name).write_bytes(data)
    atomic_json(root/'output/artifacts/publication_manifest.json',{'files':{str(f.relative_to(root/'output')):hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file()},'classification':'PUBLIC_SANITIZED','raw_logs_location':'../runs-private (PRIVATE, not pushed)','credentials_location':'../secrets (SECRET, not pushed)','actual_key_scan_passed':True})
    print({'episodes_exported':len(episodes),'requests_exported':len(ledger)})
if __name__=='__main__':main()
