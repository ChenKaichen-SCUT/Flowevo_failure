"""Credential-pattern scan without opening any API-key file.

Reuses historical scan_publication.py's signature set and zstd streaming method.
No claim of a fresh exact-secret-byte scan: the old receipt remains historical.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zstandard as zstd

PATTERNS = (rb'gh[pousr]_[A-Za-z0-9]{25,}', rb'github_pat_[A-Za-z0-9_]{30,}',
            rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----', rb'sk-[A-Za-z0-9]{24,}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    counts = {'worktree_files':0, 'git_blobs':0, 'compressed_bodies':0}
    def git(*parts):
        return subprocess.check_output(['git', '-C', str(repo), *parts])
    def plain(data, label):
        if any(re.search(pattern, data) for pattern in PATTERNS):
            raise RuntimeError('CREDENTIAL_PATTERN_MATCH '+label)
    def scan(data, label):
        plain(data, label)
        if data.startswith(b'\x28\xb5\x2f\xfd'):
            counts['compressed_bodies'] += 1
            with zstd.ZstdDecompressor().stream_reader(io.BytesIO(data)) as reader:
                overlap = b''
                while True:
                    chunk = reader.read(1024*1024)
                    if not chunk:
                        break
                    body = overlap + chunk
                    plain(body, label+' [decompressed]')
                    overlap = body[-1024:]
    names = set(git('ls-files','-z').decode().split('\0')) | set(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
    hashes = {}
    for name in sorted(names-{''}):
        path = repo / name
        if path.name in {'api.txt','.env','test_manifest.private.jsonl'} or {'secrets','runs-private','input-snapshot','vendor'}.intersection(Path(name).parts):
            raise RuntimeError('FORBIDDEN_PUBLIC_PATH '+name)
        if path.is_file():
            body = path.read_bytes()
            scan(body, name)
            hashes[name] = hashlib.sha256(body).hexdigest()
            counts['worktree_files'] += 1
    scan(git('diff','--cached','--binary'), 'staged diff')
    proc = subprocess.Popen(['git','-C',str(repo),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    for line in git('rev-list','--objects','HEAD').decode().splitlines():
        oid = line.split(' ',1)[0]
        proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
        header = proc.stdout.readline().decode().split()
        body = proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n'
        if header[1]=='blob':
            scan(body,'history object '+oid);counts['git_blobs'] += 1
    proc.stdin.close();assert proc.wait()==0
    print(json.dumps({'status':'PASSED','head':git('rev-parse','HEAD').decode().strip(),
        'counts':counts,'api_key_file_read':False,'actual_key_bytes_scanned_this_phase':False,
        'scope':'Credential signatures across worktree, staged diff, reachable blobs and decompressed payloads; not a guarantee against arbitrary unknown secrets.',
        'historical_exact_key_scan':'artifacts/publication_scan.json (unchanged frozen receipt)',
        'worktree_sha256':hashes},sort_keys=True))

if __name__=='__main__':
    main()
