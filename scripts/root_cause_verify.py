"""Phase-A invariants, accounting fixture and immutable-input verification."""
import argparse,json,csv,hashlib,sqlite3,subprocess,collections,copy,datetime,sys,math
from pathlib import Path
from root_cause_audit import read,js
from alfworld_.skill_library import SkillLibrary
from flowevo_sw.batch_runner import publish_batch

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--original',default=None);a=p.parse_args();root=Path(a.root).resolve();out=root/'output';inp=root/'input-snapshot';manifest=read(out/'artifacts/root_cause_input_manifest.json');checks={}
 for name,sha in manifest['files'].items():assert hashlib.sha256((inp/name).read_bytes()).hexdigest()==sha,name
 checks['immutable_snapshot_files_verified']=len(manifest['files'])
 for name in ('summary.json','episodes.csv','costs.csv'):
  expected=(out/'results'/name).read_bytes();actual=(root/'recompute/output/results'/name).read_bytes()
  if expected==actual:checks[name]='BYTE_IDENTICAL'
  else:
   assert name=='summary.json',name
   lhs=json.loads(expected);rhs=json.loads(actual);cost_a=lhs['costs'].pop('estimated_peak_usd');cost_b=rhs['costs'].pop('estimated_peak_usd')
   assert lhs==rhs and math.isclose(cost_a,cost_b,rel_tol=0,abs_tol=1e-12)
   checks[name]={'status':'SEMANTICALLY_IDENTICAL_EXCEPT_SQLITE_FLOAT_SUM','published_historical_usd':cost_a,'restored_historical_usd':cost_b,'absolute_difference_usd':abs(cost_a-cost_b)}
 tax=list(csv.DictReader((out/'results/failure_taxonomy.csv').open()));steps=list(csv.DictReader((out/'results/trajectory_decision_audit.csv').open()));assert len(tax)==252 and len(steps)==7453
 assert len({r['job_id'] for r in tax})==252;assert len({(r['job_id'],r['step']) for r in steps})==7453
 counts=collections.Counter(r['job_id'] for r in steps)
 for r in tax:assert counts[r['job_id']]==int(r['steps'])
 checks['episode_action_reconciliation']='252 episodes / 7453 unique actual actions'
 receipts=read(out/'artifacts/root_cause_counterfactual_receipts.json');assert len(receipts)==18
 assert len({r['job_id'] for r in receipts})==14
 assert all(r['prefix_verified'] and r['api_calls']==0 and r['split'] in ('train','dev') and len(r['alternative'])<=3 and r['branches'][0]['start_hash']==r['branches'][1]['start_hash'] for r in receipts)
 checks['counterfactuals']='18 paired checkpoints, 36 branches, 14 source episodes; no TEST'
 m0=read(inp/'M0.json');fixtures=[]
 for f in sorted((inp/'episodes').glob('main-order-17-v1.F.*.json')):
  if '.prefix.' in f.name:continue
  d=read(f);t=d['retrieved'].get('template')
  if not t or d['trace']['direct_use_count']:continue
  original=SkillLibrary.from_dict(copy.deepcopy(m0));guarded=SkillLibrary.from_dict(copy.deepcopy(m0))
  before=original.to_dict();method=guarded.record_template_usage
  guarded.record_template_usage=lambda tid,success:method(tid,success) if d['trace']['direct_use_count'] else None
  publish_batch(original,[d],[None]);publish_batch(guarded,[d],[None]);tid=t['template_id'];b=original.to_dict();g=guarded.to_dict()
  assert b['template_use_count'][tid]==before['template_use_count'][tid]+1;assert g['template_use_count'][tid]==before['template_use_count'][tid]
  fixtures.append({'job_id':d['job_id'],'template_id':tid,'actual_direct_actions':0,'original_count_before':before['template_use_count'][tid],'original_count_after':b['template_use_count'][tid],'guarded_count_after':g['template_use_count'][tid],'original_utility_after':b['template_utility'][tid],'guarded_utility_after':g['template_utility'][tid],'classification':'LOCAL_COUNTERFACTUAL_SUPPORTED_ACCOUNTING_ONLY','scope':'Same M0 for each fixture, no compilation/model/environment changes, not a replay of online policy outcomes.'})
 (out/'artifacts/root_cause_governance_fixtures.json').write_text(js(fixtures));checks['accounting_fixtures']=len(fixtures)
 before=manifest['ledger_before'];source=Path(a.original) if a.original else inp
 uri='file:'+str(source/'ledger.sqlite')+'?mode=ro'+('' if a.original else '&immutable=1')
 with sqlite3.connect(uri,uri=True) as c:after=list(c.execute('select count(*),sum(cost) from requests').fetchone())
 assert before==after
 checks['ledger_before']=before;checks['ledger_after']=after;checks['new_DeepSeek_API_calls']=0;checks['new_API_cost_CNY']=0
 checks['phase_B_executed']=False;checks['api_key_read']=False;checks['scheduler_started']=False
 if a.original:
  # Original raw records (SQLite backup bytes can differ while SQL totals match).
  for name,sha in manifest['files'].items():
   if name!='ledger.sqlite':assert hashlib.sha256((source/name).read_bytes()).hexdigest()==sha,'Original changed '+name
  checks['original_raw_records_unchanged']=True
 # /sys can retain the parent mount namespace's view after unshare -n.
 # Netlink queries the current process's actual network namespace.
 checks['network_interfaces']=sorted(x['ifname'] for x in json.loads(subprocess.check_output(['ip','-json','link','show'])));assert checks['network_interfaces']==['lo'],'Execute in an isolated network namespace'
 checks['routes']=Path('/proc/net/route').read_text();checks['historical_commit']='a0f6e0816c23a4abcb646a5fb018e786c2a6be95';checks['runtime_unchanged']=not subprocess.check_output(['git','diff',checks['historical_commit'],'--','src','configs','scripts/analyze_results.py'],cwd=out).strip();assert checks['runtime_unchanged']
 checks['python_version']=sys.version
 checks['java_version']=subprocess.check_output(['java','-version'],stderr=subprocess.STDOUT,text=True).strip()
 checks['verified_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 checks['analysis_script_sha256']={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((out/'scripts').glob('root_cause_*.py'))}
 checks['status']='PASSED';(out/'artifacts/root_cause_run_receipt.json').write_text(js(checks));print(js(checks))
if __name__=='__main__':main()
