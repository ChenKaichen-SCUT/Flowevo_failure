"""Read-only final completeness, request-boundary and frozen-code audit."""
import argparse,json,sqlite3,subprocess,hashlib
from pathlib import Path
from flowevo_sw.checkpointing import read_json,atomic_json,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();private=root/'runs-private';protocol=read_json(root/'output/artifacts/protocol.json');counts={}
    for run,expected in [('main-order-17-v1',60),('main-order-29-v1',60),('control-order-17-v1',20)]:
        plan=read_json(private/(run+'.plan.json'));rows=[]
        for spec in plan['specs']:
            for arm in plan['arms']:
                d=read_json(private/'episodes'/f"{run}.{arm}.{spec['episode_id']}.json");assert d['status']=='EPISODE_LOCKED';assert d['outcome']['host_decisions']<=100;rows.append(d)
        assert len(rows)==expected;assert plan['initial_bank_hash']==protocol['M0_hash']
        for arm in plan['arms']:
            for start in range(0,len(plan['specs']),8):
                ids={s['episode_id'] for s in plan['specs'][start:start+8]};subset=[d for d in rows if d['arm']==arm and d['spec']['episode_id'] in ids]
                hashes={d['bank_hash'] for d in subset};assert len(hashes)==1
                bank=read_json(private/'banks'/f'{run}.{arm}.batch{start//8:03d}.json');assert hashes=={bank['input_hash']}
        counts[run]={'locked':len(rows),'missing':0,'same_batch_snapshot_verified':True}
    forbidden={'score','reward','highest_score','final_score','native_completion','host_outcome','gold_path','gold_actions','goal_progress','world_state'};violations=[];models=set();endpoints=set();n=0
    def walk(o,path):
        if isinstance(o,dict):
            for k,v in o.items():
                if k in forbidden:violations.append(path+'/'+k)
                walk(v,path+'/'+k)
        elif isinstance(o,list):
            for i,v in enumerate(o):walk(v,path+'/'+str(i))
    for f in (private/'requests').glob('*.request.json'):
        d=read_json(f);n+=1;endpoints.add(d['endpoint']);models.add(d['payload']['model'])
        for i,msg in enumerate(d['payload']['messages']):
            try:obj=json.loads(msg['content'])
            except (ValueError,TypeError):continue
            walk(obj,f.name+'/'+str(i))
    assert not violations, 'Forbidden structured provider payload fields detected'
    assert endpoints=={'https://api.deepseek.com/chat/completions'};assert models=={'deepseek-flash'}
    with sqlite3.connect(f'file:{private/"ledger.sqlite"}?mode=ro',uri=True) as c:
        states=dict(c.execute('select state,count(*) from requests group by state'));assert not any(states.get(s,0) for s in ('STARTED','UNKNOWN','RESPONSE_SAVED'))
    runtime=['src','configs','scripts/run_main.py','scripts/analyze_results.py','scripts/dev_local_validation.py','scripts/run_selected_train.py','scripts/run_discovery.py','scripts/learn_constraints.py','scripts/generate_rules.py','scripts/revise_rules.py']
    diff=subprocess.check_output(['git','diff','--name-only',protocol['source_commit'],'--',*runtime],cwd=root/'output',text=True);assert not diff,'Frozen experiment source changed'
    result={'status':'PASSED','populations':counts,'provider_requests_audited':n,'endpoints':sorted(endpoints),'requested_models':sorted(models),'forbidden_structured_request_fields':violations,'ledger_states':states,'frozen_runtime_diff':[],'frozen_source_commit':protocol['source_commit'],'protocol_sha256':protocol['protocol_sha256'],'scope':'Structured-field audit plus code/allowlist tests; public environment text is retained verbatim, not censored.'}
    atomic_json(root/'output/artifacts/delivery_audit.json',result);print(json.dumps(result))
if __name__=='__main__':main()
