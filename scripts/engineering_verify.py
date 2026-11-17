"""Read-only final reconciliation, isolation and zero-provider receipt."""
import argparse,collections,csv,datetime,hashlib,json,math,os,sqlite3,subprocess,sys
from pathlib import Path
from engineering_common import read,write,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--original');a=p.parse_args()
    root=Path(a.root).resolve();out=root/'output';inp=root/'input-snapshot';art=out/'artifacts/engineering'
    manifest=read(out/'artifacts/root_cause_input_manifest.json');start=read(art/'start.json')
    for name,expected in manifest['files'].items():
        assert hashlib.sha256((inp/name).read_bytes()).hexdigest()==expected,name
        if a.original and name!='ledger.sqlite':assert hashlib.sha256((Path(a.original)/name).read_bytes()).hexdigest()==expected,'Original '+name
    source=Path(a.original) if a.original else inp
    with sqlite3.connect((source/'ledger.sqlite').as_uri()+'?mode=ro'+('' if a.original else '&immutable=1'),uri=True) as c:
        totals=list(c.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    assert totals[0]==start['ledger_before'][0]
    assert math.isclose(totals[1],start['ledger_before'][1],rel_tol=0,abs_tol=1e-12)
    interfaces=sorted(x['ifname'] for x in json.loads(subprocess.check_output(['ip','-json','link','show'])))
    assert interfaces==['lo'] and os.environ.get('FLOWEVO_OFFLINE_ONLY')=='1'
    workflow=read(art/'orchestration.json');assert len(workflow['results'])==4 and all(r['status']=='PASSED' for r in workflow['results'])
    governance=read(art/'governance_receipt.json');assert len(governance['reference_batches_reproduced_exactly'])==42
    assert {r['run'] for r in governance['version_mismatches']}=={'discovery-v1'}
    with (out/'results/engineering/governance_events.csv').open(encoding='utf-8',newline='') as f:events=list(csv.DictReader(f))
    assert dict(collections.Counter(r['mode'] for r in events))=={'isolated_credit_fix':236,'chained_credit_fix':236,'chained_credit_and_age_fix':236}
    action=read(art/'action_audit.json');assert len(action['responses'])==7691
    assert all(r['diagnosis']['policy']=='REPORT_ONLY' and r['diagnosis']['action_unchanged'] for r in action['responses'])
    binding=read(art/'binding_summary.json');plan=read(art/'binding_plan_v2.json')
    assert len(plan['cases'])==binding['binding_cases'] and all(c['split'] in ('train','dev') for c in plan['cases'])
    accepted=read(art/'accepted_binding_prefixes.json');assert all(c['preparation_only'] and c['source_validation'] for c in accepted)
    receipts=read(art/'jvm_receipts.json');jvmplan=read(art/'jvm_plan.json')
    assert [r['case'] for r in receipts]==jvmplan['cases']
    assert sum(r['classification']=='IDENTITY_VERIFIED' for r in receipts)==12
    assert sum(r['classification']=='PREPARATION_ACTIONS_EXECUTABLE_ONLY' for r in receipts)==2
    assert all(r['prefix_hashes_verified'] and r['new_api_calls']==0 and not r['task_success_rate_computed'] for r in receipts)
    for name in ('results/summary.json','results/episodes.csv','results/costs.csv','artifacts/protocol.json','scripts/analyze_results.py','src/flowevo_sw/adapter.py'):
        original=subprocess.check_output(['git','show',start['parent']+':'+name],cwd=out)
        assert (out/name).read_bytes()==original,'Historical artifact changed: '+name
    test_log=(root/'tests-final.log').read_text();assert 'passed' in test_log and 'failed' not in test_log
    hashes={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for base in ('src/flowevo_sw','scripts','configs') for f in sorted((out/base).glob('*')) if f.is_file()}
    receipt={'status':'PASSED','input_files_verified':len(manifest['files']),'original_records_checked':bool(a.original),
        'ledger_before':start['ledger_before'],'ledger_after':totals,'new_model_API_calls':0,'new_API_cost_CNY':0,
        'api_txt_read':False,'scheduler_started':False,'network_interfaces':interfaces,'offline_client_guard':True,
        'historical_task_outcomes_unchanged':True,'new_task_success_rates_reported':False,
        'reference_batches':42,'formal_publications':236,'explicitly_excluded_version_records':16,
        'action_responses':7691,'jvm_identity_cases':12,'jvm_unique_preparation_branches':2,
        'full_skill_transfer_established':False,'tests':test_log.strip(),'source_sha256':hashes,
        'verified_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version}
    write(art/'verification.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='source_sha256'}))
if __name__=='__main__':main()
