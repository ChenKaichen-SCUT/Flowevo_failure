"""Restore only this repository's sanitized audit records for offline analysis.

No network or model calls. Refuses an existing audit directory.
"""
import argparse,io,json,sqlite3,hashlib
from pathlib import Path
import zstandard as zstd

def records(path):
    with path.open('rb') as f, zstd.ZstdDecompressor().stream_reader(f) as reader:
        for line in io.TextIOWrapper(reader,encoding='utf-8'):
            yield json.loads(line)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();src=root/'output/results';dest=root/'runs-private'
    if dest.exists():raise RuntimeError('Refusing to overwrite existing runs-private')
    dest.mkdir();(dest/'episodes').mkdir();(dest/'requests').mkdir()
    for d in records(src/'episodes_full_sanitized.jsonl.zst'):
        (dest/'episodes'/(d['job_id']+'.json')).write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
    for r in records(src/'learning_governance_sanitized.jsonl.zst'):
        path=(dest/r['relative_path']).resolve()
        if not path.is_relative_to(dest):raise ValueError('Invalid archive path')
        data=r['text'].encode('utf-8');assert hashlib.sha256(data).hexdigest()==r['private_sha256']
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    rows=[]
    for r in records(src/'requests_sanitized.jsonl.zst'):
        row=r['ledger'];rows.append(row)
        for field,suffix in (('request','.request.json'),('response','.json')):
            if r[field] is not None:(dest/'requests'/(row['id']+suffix)).write_text(json.dumps(r[field],ensure_ascii=False),encoding='utf-8')
    with sqlite3.connect(dest/'ledger.sqlite') as c:
        columns=list(rows[0]);numeric={'reserved','cost','started','finished'}
        c.execute('CREATE TABLE requests ('+','.join('"'+k+'" '+('REAL' if k in numeric else 'TEXT') for k in columns)+')')
        c.executemany('INSERT INTO requests VALUES ('+','.join('?' for _ in columns)+')',[[r[k] for k in columns] for r in rows])
    print(json.dumps({'episodes':len(list((dest/'episodes').glob('*.json'))),'requests':len(rows),'provider_calls':0,'purpose':'Offline audit only. Published TEST is already exposed.'}))
if __name__=='__main__':main()
