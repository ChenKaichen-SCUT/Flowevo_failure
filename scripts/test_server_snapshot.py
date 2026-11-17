"""Integrity, confidentiality and overwrite checks for retirement recovery."""
import argparse, hashlib, importlib.util, json, os, tempfile, unittest
from pathlib import Path
from cryptography.exceptions import InvalidTag

spec=importlib.util.spec_from_file_location('snapshot',Path(__file__).with_name('server_snapshot.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.src=self.root/'source';self.src.mkdir();(self.src/'a').write_bytes(b'private evidence\x00'*128)
        (self.src/'b').write_bytes((self.src/'a').read_bytes())
        if os.name!='nt':os.symlink(self.src/'a',self.src/'link')
        self.key=self.root/'key';self.key.write_text('13'*32)
        self.parts=self.root/'parts';s.pack(argparse.Namespace(output=str(self.parts),key=str(self.key),roots=[str(self.src)]))
    def tearDown(self):self.temp.cleanup()
    def test_restore_exact_and_independent_copies(self):
        dest=self.root/'restored';s.restore(argparse.Namespace(dest=str(dest),key=str(self.key),input=str(self.parts)))
        restored=dest/str(self.src).lstrip('/')
        self.assertEqual((restored/'a').read_bytes(),(self.src/'a').read_bytes())
        (restored/'a').write_bytes(b'changed')
        self.assertEqual((restored/'b').read_bytes(),(self.src/'b').read_bytes())
        if os.name!='nt':self.assertEqual(os.readlink(restored/'link'),str(restored/'a'))
    def test_wrong_key_rejected_before_extract(self):
        wrong=self.root/'wrong';wrong.write_text('14'*32);dest=self.root/'rejected'
        with self.assertRaises(InvalidTag):s.restore(argparse.Namespace(dest=str(dest),key=str(wrong),input=str(self.parts)))
        self.assertFalse((dest/str(self.src).lstrip('/')).exists())
    def test_tamper_rejected_even_if_public_checksums_replaced(self):
        p=next(self.parts.glob('*.part0001'));body=bytearray(p.read_bytes());body[30]^=1;p.write_bytes(body)
        manifest=json.loads((self.parts/'backup_manifest.json').read_text());h=hashlib.sha256(body).hexdigest()
        manifest['parts'][0]['sha256']=h;manifest['ciphertext_sha256']=h;s.dump(self.parts/'backup_manifest.json',manifest)
        with self.assertRaises(InvalidTag):s.restore(argparse.Namespace(dest=str(self.root/'tamper'),key=str(self.key),input=str(self.parts)))
    def test_refuses_existing_destination_and_traversal(self):
        with self.assertRaises(FileExistsError):s.restore(argparse.Namespace(dest=str(self.src),key=str(self.key),input=str(self.parts)))
        with self.assertRaises(ValueError):s.safe_path(self.root,'../escape')
    def test_authentication_tag_can_cross_parts(self):
        p=next(self.parts.glob('*.part0001'));body=p.read_bytes();p.write_bytes(body[:-7]);q=self.parts/'flowevo-server-snapshot.part0002';q.write_bytes(body[-7:])
        manifest=json.loads((self.parts/'backup_manifest.json').read_text());manifest['parts']=[{'name':f.name,'size':f.stat().st_size,'sha256':s.digest(f)} for f in (p,q)];s.dump(self.parts/'backup_manifest.json',manifest)
        s.restore(argparse.Namespace(dest=str(self.root/'split'),key=str(self.key),input=str(self.parts)))

if __name__=='__main__':unittest.main()
