"""Encrypted, deduplicated file snapshot and authenticated, non-overwriting restore.

Requires Python >=3.10 and cryptography. No provider/model/network code.
"""
import argparse, collections, gzip, hashlib, io, json, os, re, shutil, stat, tarfile, tempfile, time
from pathlib import Path, PurePosixPath
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b'FEVOBK1\n'
BLOCK = 1024 * 1024

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(BLOCK), b''): h.update(b)
    return h.hexdigest()

def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')

def key(path):
    value = bytes.fromhex(Path(path).read_text(encoding='ascii').strip())
    if len(value) != 32: raise ValueError('Recovery key must be exactly 32 bytes')
    return value

class Parts:
    def __init__(self, directory, limit=128*1024*1024):
        self.directory=Path(directory);self.limit=limit;self.items=[];self.current=None
        self.total=hashlib.sha256();self.total_size=0
    def write(self, data):
        original=len(data);view=memoryview(data)
        while view:
            if self.current is None:
                name='flowevo-server-snapshot.part%04d'%(len(self.items)+1)
                self.current=(self.directory/name).open('xb');self.name=name
                self.hash=hashlib.sha256();self.size=0
            piece=view[:self.limit-self.size];self.current.write(piece)
            self.hash.update(piece);self.total.update(piece);self.size+=len(piece);self.total_size+=len(piece)
            view=view[len(piece):]
            if self.size==self.limit:self.finish_part()
        return original
    def finish_part(self):
        if self.current:
            self.current.close();self.items.append({'name':self.name,'size':self.size,'sha256':self.hash.hexdigest()});self.current=None
    def flush(self):
        if self.current:self.current.flush()

class EncryptWriter:
    def __init__(self, parts, secret):
        self.parts=parts;nonce=os.urandom(12);self.header=MAGIC+nonce
        self.enc=Cipher(algorithms.AES(secret),modes.GCM(nonce)).encryptor()
        self.enc.authenticate_additional_data(self.header);parts.write(self.header)
    def write(self, data):
        self.parts.write(self.enc.update(data));return len(data)
    def flush(self):self.parts.flush()
    def finish(self):
        self.parts.write(self.enc.finalize());self.parts.write(self.enc.tag);self.parts.finish_part()

def collect(roots):
    entries=[];objects={};counts={}
    def record(path):
        s=path.lstat();relative=path.as_posix().lstrip('/')
        row={'path':relative,'mode':stat.S_IMODE(s.st_mode),'mtime_ns':s.st_mtime_ns}
        if path.is_symlink():row.update(type='symlink',target=os.readlink(path))
        elif path.is_dir():row.update(type='directory')
        elif path.is_file():
            h=digest(path);after=path.stat()
            if (s.st_size,s.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError('Source changed during hashing: '+relative)
            row.update(type='file',size=s.st_size,sha256=h);objects.setdefault(h,str(path))
        else:raise ValueError('Unsupported special file: '+relative)
        entries.append(row)
    for root in roots:
        base=Path(root).resolve();before=len(entries);record(base)
        for folder, dirs, files in os.walk(base,followlinks=False):
            dirs.sort();files.sort()
            for name in dirs+files:record(Path(folder)/name)
        counts[str(base)]=len(entries)-before
    paths=[r['path'] for r in entries]
    if len(paths)!=len(set(paths)):raise ValueError('Overlapping snapshot roots')
    return entries,objects,counts

def pack(a):
    output=Path(a.output);output.mkdir(parents=True,exist_ok=True)
    if list(output.glob('flowevo-server-snapshot.part*')):raise FileExistsError('Snapshot parts already exist')
    entries,objects,counts=collect(a.roots)
    manifest={'format':1,'roots':a.roots,'entries':entries,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    body=json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    private=output/'private_manifest.json';private.write_bytes(body);private.chmod(0o600)
    parts=Parts(output);enc=EncryptWriter(parts,key(a.key))
    with gzip.GzipFile(fileobj=enc,mode='wb',compresslevel=3,mtime=0) as gz:
        with tarfile.open(fileobj=gz,mode='w|') as archive:
            item=tarfile.TarInfo('manifest.json');item.size=len(body);item.mode=0o600
            archive.addfile(item,io.BytesIO(body))
            for index,(h,path) in enumerate(objects.items()):
                item=tarfile.TarInfo('objects/'+h);item.size=Path(path).stat().st_size;item.mode=0o600
                with open(path,'rb') as f:archive.addfile(item,f)
                if index and index%10000==0:print('Archived unique objects:',index,flush=True)
    enc.finish()
    # Recheck all original bytes after the archive has been read.
    for row in entries:
        if row['type']=='file' and digest('/'+row['path'])!=row['sha256']:raise RuntimeError('Source changed after snapshot: '+row['path'])
    summary={'format':'FLOWEVO_AES256GCM_GZIP_DEDUP_V1','created_utc':manifest['created_utc'],
      'roots':a.roots,'entries_by_root':counts,'entries':len(entries),'files':sum(r['type']=='file' for r in entries),
      'symlinks':sum(r['type']=='symlink' for r in entries),'source_file_bytes':sum(r.get('size',0) for r in entries),
      'unique_content_objects':len(objects),'unique_content_bytes':sum(Path(p).stat().st_size for p in objects.values()),
      'encrypted_bytes':parts.total_size,'ciphertext_sha256':parts.total.hexdigest(),'private_manifest_sha256':hashlib.sha256(body).hexdigest(),
      'parts':parts.items,'new_model_requests':0,'source_bytes_rechecked':True,
      'excluded':'Operating-system disk image, root SSH keys, shell history and unrelated OS/user directories. All files under the enumerated project roots are included.'}
    dump(output/'backup_manifest.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='parts'},ensure_ascii=False),flush=True)

def decrypt(directory, secret, target):
    directory=Path(directory);summary=json.loads((directory/'backup_manifest.json').read_text())
    expected=summary['parts'];overall=hashlib.sha256()
    for entry in expected:
        name=entry['name']
        if not re.fullmatch(r'flowevo-server-snapshot\.part\d{4}',name):raise ValueError('Invalid part name')
        path=directory/name
        if path.stat().st_size!=entry['size'] or digest(path)!=entry['sha256']:raise ValueError('Part integrity failure: '+name)
    first=directory/expected[0]['name']
    with first.open('rb') as f:header=f.read(len(MAGIC)+12)
    if not header.startswith(MAGIC):raise ValueError('Unknown encrypted archive format')
    tag=b''
    for entry in reversed(expected):
        with (directory/entry['name']).open('rb') as f:
            count=min(16-len(tag),entry['size']);f.seek(-count,2);tag=f.read(count)+tag
        if len(tag)==16:break
    total_size=sum(entry['size'] for entry in expected)
    if len(tag)!=16 or total_size<len(header)+16:raise ValueError('Truncated ciphertext')
    dec=Cipher(algorithms.AES(secret),modes.GCM(header[len(MAGIC):],tag)).decryptor();dec.authenticate_additional_data(header)
    with target.open('xb') as out:
        position=0
        for index,entry in enumerate(expected):
            with (directory/entry['name']).open('rb') as f:
                while True:
                    b=f.read(BLOCK)
                    if not b:break
                    overall.update(b);start=0;end=len(b)
                    if position<len(header):start=len(header)-position
                    end=min(end,total_size-16-position)
                    if end>start:out.write(dec.update(b[start:end]))
                    position+=len(b)
        out.write(dec.finalize())
    if overall.hexdigest()!=summary['ciphertext_sha256']:raise ValueError('Archive digest failure')
    return summary

def safe_path(base, relative):
    p=PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(x in ('..','.') for x in p.parts):raise ValueError('Invalid archived path')
    target=base.joinpath(*p.parts)
    if not target.resolve().is_relative_to(base.resolve()):raise ValueError('Path escapes restore root')
    return target

def mapped_link(row, base, manifest):
    target=row['target']
    if target.startswith('/'):
        for root in manifest['roots']:
            if target==root or target.startswith(root.rstrip('/')+'/'):
                return str(base/target.lstrip('/'))
    return target

def restore(a):
    dest=Path(a.dest).resolve()
    if dest.exists():raise FileExistsError('Restore destination must not already exist')
    dest.mkdir(mode=0o700,parents=True)
    try:
        with tempfile.TemporaryDirectory(prefix='.authenticated-snapshot-',dir=dest) as temp:
            temp=Path(temp);plain=temp/'archive.tar.gz'
            summary=decrypt(a.input,key(a.key),plain)
            cache=temp/'objects';cache.mkdir()
            manifest=None;seen=set()
            with tarfile.open(plain,mode='r|gz') as archive:
                for item in archive:
                    if not item.isfile():raise ValueError('Unexpected non-file archive member')
                    if item.name=='manifest.json':
                        if manifest is not None:raise ValueError('Duplicate manifest')
                        body=archive.extractfile(item).read()
                        if hashlib.sha256(body).hexdigest()!=summary['private_manifest_sha256']:raise ValueError('Manifest hash failure')
                        manifest=json.loads(body);continue
                    if not re.fullmatch(r'objects/[a-f0-9]{64}',item.name):raise ValueError('Invalid object member')
                    h=item.name.split('/')[1]
                    if h in seen:raise ValueError('Duplicate object')
                    seen.add(h);path=cache/h
                    with path.open('xb') as f:shutil.copyfileobj(archive.extractfile(item),f,BLOCK)
                    if digest(path)!=h:raise ValueError('Content object corrupted')
            if manifest is None:raise ValueError('Manifest missing')
            # Authentication and object checks are complete; free the compressed staging file.
            plain.unlink()
            entries=manifest['entries'];paths=[r['path'] for r in entries]
            if len(paths)!=len(set(paths)):raise ValueError('Duplicate restoration path')
            if set(r['sha256'] for r in entries if r['type']=='file')!=seen:raise ValueError('Object inventory mismatch')
            for row in entries:
                target=safe_path(dest,row['path'])
                if row['type']=='directory':target.mkdir(parents=True,exist_ok=True)
            references=collections.Counter(r['sha256'] for r in entries if r['type']=='file')
            for row in entries:
                if row['type']!='file':continue
                target=safe_path(dest,row['path']);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(cache/row['sha256'],target);target.chmod(row['mode']);os.utime(target,ns=(row['mtime_ns'],row['mtime_ns']))
                references[row['sha256']]-=1
                if references[row['sha256']]==0:(cache/row['sha256']).unlink()
            # Symlinks are created last so they cannot redirect archived file writes.
            for row in entries:
                if row['type']=='symlink':
                    target=safe_path(dest,row['path']);target.parent.mkdir(parents=True,exist_ok=True)
                    os.symlink(mapped_link(row,dest,manifest),target)
            for row in reversed(entries):
                if row['type']=='directory':
                    target=dest/row['path'];target.chmod(row['mode']);os.utime(target,ns=(row['mtime_ns'],row['mtime_ns']))
            checked=0
            for row in entries:
                target=dest/row['path']
                if row['type']=='file':
                    if digest(target)!=row['sha256']:raise ValueError('Restored file hash mismatch')
                    checked+=1
                elif row['type']=='symlink' and os.readlink(target)!=mapped_link(row,dest,manifest):raise ValueError('Link mismatch')
            dump(dest/'RESTORE_VERIFICATION.json',{'status':'PASSED','authenticated_decryption':True,'files_verified':checked,
              'entries':len(entries),'symlinks_remapped_within_captured_roots':True,'manifest_sha256':summary['private_manifest_sha256'],
              'new_model_requests':0,'ciphertext_sha256':summary['ciphertext_sha256']})
            print(json.dumps(json.loads((dest/'RESTORE_VERIFICATION.json').read_text())),flush=True)
    except Exception:
        # Keep any partial directory for inspection; never overwrite or recursively delete user paths.
        raise

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('pack');q.add_argument('--key',required=True);q.add_argument('--output',required=True);q.add_argument('roots',nargs='+');q.set_defaults(func=pack)
    q=sub.add_parser('restore');q.add_argument('--key',required=True);q.add_argument('--input',required=True);q.add_argument('--dest',required=True);q.set_defaults(func=restore)
    a=p.parse_args();a.func(a)
if __name__=='__main__':main()
