"""Verify the public-restoration path without a model client or JVM.

This checks saved real JVM receipts; it does not claim a fresh environment replay.
The full Linux/JVM verifier remains root_cause_verify.py.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
from root_cause_audit import read, js

BASE = 'a0f6e0816c23a4abcb646a5fb018e786c2a6be95'
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='..')
    parser.add_argument('--recomputed-output', help='Directory produced by historical analyze_results.py; defaults to <root>/recompute/output')
    args = parser.parse_args()
    root = Path(args.root).resolve();out = root/'output';inp = root/'input-snapshot'
    recomputed=Path(args.recomputed_output).resolve() if args.recomputed_output else root/'recompute/output'
    manifest = read(out/'artifacts/root_cause_input_manifest.json')
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((inp/name).read_bytes()).hexdigest()==expected, name
    checks = {'snapshot_files_verified':len(manifest['files']), 'historical_statistics':{}}
    for name in ('summary.json','episodes.csv','costs.csv'):
        expected = subprocess.check_output(['git','show',BASE+':results/'+name],cwd=out)
        actual = (recomputed/'results'/name).read_bytes()
        if expected==actual:
            checks['historical_statistics'][name]='BYTE_IDENTICAL'
        else:
            assert name=='summary.json'
            lhs=json.loads(expected);rhs=json.loads(actual)
            cost_a=lhs['costs'].pop('estimated_peak_usd');cost_b=rhs['costs'].pop('estimated_peak_usd')
            assert lhs==rhs and math.isclose(cost_a,cost_b,rel_tol=0,abs_tol=1e-12)
            checks['historical_statistics'][name]={'status':'IDENTICAL_EXCEPT_SQLITE_FLOAT_SUM','historical_usd_delta':cost_b-cost_a}
    references=read(out/'artifacts/root_cause_private_reference.json')
    for name, expected in references['files'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==expected, name
    checks['matches_saved_private_analysis']=sorted(references['files'])
    def rows(name):
        with (out/'results'/name).open(encoding='utf-8',newline='') as stream:
            return list(csv.DictReader(stream))
    taxonomy=rows('failure_taxonomy.csv');steps=rows('trajectory_decision_audit.csv')
    assert len(taxonomy)==252 and len(steps)==7453
    assert len({x['job_id'] for x in taxonomy})==252
    assert len({(x['job_id'],x['step']) for x in steps})==7453
    counts=collections.Counter(x['job_id'] for x in steps)
    for row in taxonomy:
        assert counts[row['job_id']]==int(row['steps'])
    checks['episodes']=252;checks['actions']=7453
    receipts=read(out/'artifacts/root_cause_counterfactual_receipts.json')
    assert len(receipts)==18 and len({r['job_id'] for r in receipts})==14
    for receipt in receipts:
        assert receipt['split'] in ('train','dev') and receipt['api_calls']==0 and receipt['prefix_verified']
        assert len(receipt['alternative'])<=3 and len(receipt['factual'])<=3
        episode=read(inp/'episodes'/(receipt['job_id']+'.json'));n=receipt['prefix_len']
        start=digest(episode['steps'][n]['before'])
        for branch in receipt['branches']:
            assert branch['start_hash']==start
            previous=start
            for step in branch['steps']:
                assert step['before_hash']==previous;previous=step['after_hash']
        for i,step in enumerate(receipt['branches'][0]['steps']):
            original=episode['steps'][n+i]
            assert original['executed_action']==step['action']
            assert original['observation_hash']==step['after_hash']
    checks['saved_real_JVM_receipts']='18 pairs / 36 branches; public prefix and factual suffix hashes match archived episodes'
    checks['new_JVM_execution_in_this_check']=False
    with sqlite3.connect((inp/'ledger.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True) as connection:
        totals=list(connection.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    assert totals==manifest['ledger_before']
    checks['historical_ledger']=totals;checks['new_DeepSeek_API_calls']=0;checks['new_API_cost_CNY']=0
    checks['api_key_file_read']=False;checks['scheduler_started']=False
    checks['python']=sys.version;checks['verified_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks['status']='PASSED_PUBLIC_RESTORATION_AND_SAVED_RECEIPTS'
    (out/'artifacts/root_cause_public_reproduction.json').write_text(js(checks),encoding='utf-8')
    print(js(checks))

if __name__=='__main__':
    main()
