"""Create a fresh independent audit snapshot; never read credentials or call models.

Use the historical restore_public_run.py first when original logs are unavailable.
Only completed historical run families are copied. Existing destinations are refused.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time

COMMIT = 'a0f6e0816c23a4abcb646a5fb018e786c2a6be95'
DIRECTORIES = ('episodes', 'compilations', 'banks', 'diagnoses', 'probes', 'dev_local', 'requests')
RUNS = ('discovery-v1', 'discovery-v2', 'selected-train-v1', 'dev-baseline-v1',
        'batch-sensitivity-1-v1', 'batch-sensitivity-8-v1', 'main-order-17-v1',
        'main-order-29-v1', 'control-order-17-v1')
ROOT_FILES = ('M0.json', 'resource_samples.jsonl', 'selected_probes.json',
              'train-probes-v1.index.json', 'train-probes-v1.selection.json',
              'learning-v2.mechanisms.json', 'discovery-v1.superseded.json')

def copy_record(source, destination):
    if source.is_symlink():
        raise ValueError('Refusing symlink: '+str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='..')
    parser.add_argument('--source', required=True, help='Original or publicly restored runs-private')
    args = parser.parse_args()
    root, source = Path(args.root).resolve(), Path(args.source).resolve()
    target = root / 'input-snapshot'
    manifest = root / 'output/artifacts/root_cause_input_manifest.json'
    if target.exists():
        raise FileExistsError('Refusing to overwrite '+str(target))
    if not (source / 'ledger.sqlite').is_file():
        raise FileNotFoundError('Source must contain the historical ledger')
    # This artifact describes the current reproduction's input bytes. Keep the
    # committed receipt as provenance before replacing it for a fresh reproduction.
    if manifest.exists():
        prior = manifest.with_suffix('.published.json')
        if prior.exists():
            raise FileExistsError('Refusing to overwrite prior manifest '+str(prior))
        shutil.copy2(manifest, prior)
    target.mkdir()
    for directory in DIRECTORIES:
        src = source / directory
        if not src.exists():
            continue
        for path in sorted(src.rglob('*')):
            if path.is_symlink():
                raise ValueError('Refusing symlink '+str(path))
            if path.is_file() and path.suffix == '.json':
                copy_record(path, target / path.relative_to(source))
    roots = {source / name for name in ROOT_FILES}
    for run in RUNS:
        roots.add(source / (run + '.plan.json'))
        roots.update(source.glob(run + '.*.final_bank.json'))
    for path in sorted(roots):
        if path.is_file():
            copy_record(path, target / path.name)
    with sqlite3.connect((source / 'ledger.sqlite').as_uri()+'?mode=ro', uri=True) as connection:
        with sqlite3.connect(target / 'ledger.sqlite') as backup:
            connection.backup(backup)
            # Consolidated backup: subsequent immutable=1 reads need no sidecars.
            backup.execute('PRAGMA journal_mode=DELETE')
            totals = list(backup.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    files = {str(path.relative_to(target)).replace(os.sep, '/'):hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(target.rglob('*')) if path.is_file()}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({'source_commit':COMMIT,
        'source':'Independent copy of supplied original/publicly restored historical logs; no credentials',
        'ledger_before':totals, 'files':files, 'created_epoch':time.time()}, sort_keys=True), encoding='utf-8')
    for path in sorted(target.rglob('*'), reverse=True):
        path.chmod(path.stat().st_mode & ~0o222)
    target.chmod(target.stat().st_mode & ~0o222)
    print(json.dumps({'snapshot_files':len(files), 'historical_ledger':totals, 'new_api_calls':0}))

if __name__ == '__main__':
    main()
