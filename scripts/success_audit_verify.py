"""Reconcile published source audits against immutable/public records offline."""
import argparse,collections,csv,hashlib,json,os,sqlite3,subprocess,datetime
from pathlib import Path
from success_audit_prepare import read,write,canonical,sha,verify_frozen

PARENT='5ae0dcdf80bf81c4f5acd34d24f75501ddda942b'
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--original',required=True);p.add_argument('--init',action='store_true');a=p.parse_args()
    root=Path(a.root).resolve();out=root/'output';inp=root/'runs-private';original=Path(a.original);art=out/'artifacts/success_audit'
    assert os.environ.get('FLOWEVO_OFFLINE_ONLY')=='1'
    interfaces=sorted(r['ifname'] for r in json.loads(subprocess.check_output(['ip','-json','link','show'])))
    assert interfaces==['lo']
    with sqlite3.connect((original/'ledger.sqlite').as_uri()+'?mode=ro',uri=True) as c:
        totals=list(c.execute('SELECT count(*),sum(cost) FROM requests').fetchone())
    if a.init:
        path=art/'start.json';assert not path.exists()
        write(path,{'parent':PARENT,'ledger_before':totals,'new_model_requests_max':0,'new_api_cost_max':0,
          'input':'Existing public archives restored by restore_public_run.py; original server records verified separately',
          'network_interfaces':interfaces,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
        print('Initialized read-only audit; no provider request');return
    start=read(art/'start.json');assert totals==start['ledger_before']
    inventory=read(art/'success_inventory.json');manifest=read(art/'source_manifest.json')
    for r in inventory:
        f=inp/r['source_ref'];assert sha(f.read_bytes())==r['source_sha256']
        assert sha(canonical(read(f)))==r['episode_semantic_sha256']
        assert canonical(read(original/r['source_ref']))==canonical(read(f)),r['job_id']
    old=read(out/'artifacts/root_cause_input_manifest.json')
    for name,expected in old['files'].items():
        if name!='ledger.sqlite':assert sha((original/name).read_bytes())==expected,name
    for f in (out/'src/flowevo_sw').glob('*.py'):
        name=f.relative_to(out).as_posix();assert f.read_bytes()==subprocess.check_output(['git','show',PARENT+':'+name],cwd=out)
    for name in ('results/summary.json','results/episodes.csv','results/costs.csv','artifacts/protocol.json'):
        assert (out/name).read_bytes()==subprocess.check_output(['git','show',PARENT+':'+name],cwd=out)
    freeze=read(art/'source_review_freeze.json')
    verify_frozen(out,freeze['files'])
    summary=read(art/'summary.json');transfer=read(art/'transfer_checks.json')
    assert summary['primary_units']==31 and summary['source_reviewed_records']==39
    source_review=read(art/'source_adjudicated.json');compilation_review=read(art/'compilation_review_b.json')
    reviewed={r['job_id'] for r in source_review}
    assert reviewed=={r['job_id'] for r in compilation_review}
    assert len(reviewed)==39 and len(inventory)==102
    for entry in manifest['packets']:
        packet=art/'source_packets'/(entry['job_id']+'.json')
        assert sha(canonical(read(packet)))==entry['packet_sha256']
        packet_text=art/'source_packets'/(entry['job_id']+'.txt')
        assert sha(packet_text.read_bytes().replace(b'\r\n',b'\n'))==entry['text_sha256']
    source_rows=list(csv.DictReader((out/'results/success_trace_audit.csv').open(encoding='utf-8',newline='')))
    matrix=list(csv.DictReader((out/'results/skill_information_loss.csv').open(encoding='utf-8',newline='')))
    assert len(matrix)==len(source_rows)==102
    assert {r['job_id'] for r in matrix}=={r['job_id'] for r in source_rows}=={r['job_id'] for r in inventory}
    primary=[r for r in matrix if r['scope']=='PRIMARY_TRAIN_DEV']
    assert len(primary)==len({r['unit'] for r in primary})==31
    assert dict(collections.Counter(r['source_process_label'] for r in primary))==summary['source_labels_primary']
    assert all(r['source_process_label']=='NOT_AUDITED_TEST' and not r['raw_action_template'] and not r['review_ref'] for r in matrix if r['split']=='test')
    compilation=read(art/'compilation_receipt.json')
    assert compilation['cached_compiler_outputs_revalidated']==39 and compilation['new_model_calls']==0
    assert compilation['saved_compilation_files']==37 and compilation['current_source_valid']==15
    assert summary['compilation_review_b_sha256']==sha((art/'compilation_review_b.json').read_bytes())
    assert all(c['split'] in ('train','dev') for c in transfer['cases'])
    assert transfer['new_model_calls']==0 and not transfer['target_score_used']
    assert not summary['new_task_success_rates_reported']
    receipt={'status':'PASSED','parent':PARENT,'runtime_code_unchanged':True,'historical_task_outcomes_unchanged':True,
      'original_files_verified':len(old['files'])-1,'original_public_success_records_equal':len(inventory),
      'ledger_before':start['ledger_before'],'ledger_after':totals,'new_model_API_calls':0,'new_API_cost':0,
      'api_key_read':False,'scheduler_started':False,'network_interfaces':interfaces,'source_review_frozen':True,
      'primary_units':31,'source_reviewed_records':39,'static_transfer_cases':len(transfer['cases']),
      'source_packets_and_csv_join_verified':True,'matrix_records':len(matrix),'TEST_design_rows':0,
      'new_TEST_solves':0,'new_JVM_runs':0,'tests':(root/'tests-success.log').read_text().strip(),
      'source_sha256':{f.relative_to(out).as_posix():sha(f.read_bytes()) for f in sorted((out/'scripts').glob('success_audit*'))+[out/'configs/success_trace_audit.json'] if f.is_file()},
      'output_sha256':{name:sha((out/name).read_bytes()) for name in ('results/success_trace_audit.csv','results/skill_information_loss.csv','reports/SUCCESS_TRACE_INTEGRITY_ZH.md','reports/COMPILATION_INFORMATION_LOSS_ZH.md','artifacts/success_audit/summary.json')},
      'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    assert 'passed' in receipt['tests'] and 'failed' not in receipt['tests']
    write(art/'verification.json',receipt);print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
