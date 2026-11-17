"""Read-only analysis of locked run files. No model client is imported."""
import argparse,csv,json,hashlib,sqlite3,collections
from pathlib import Path
import numpy as np
from scipy.stats import binomtest
from flowevo_sw.checkpointing import read_json,atomic_json

def analyze(root,run_prefixes):
    files=sorted((root/'runs-private/episodes').glob('*.json'));rows=[];hashes={};detailed=[]
    for f in files:
        if '.prefix.' in f.name or not any(f.name.startswith(p+'.') for p in run_prefixes):continue
        d=read_json(f);hashes[f.name]=hashlib.sha256(f.read_bytes()).hexdigest();s=d['spec'];o=d.get('outcome',{});tr=d.get('trace',{})
        verdicts=[v.get('decision') for check in d.get('checks',[]) for v in check['verdicts']]
        row={'job_id':d['job_id'],'run_id':d['run_id'],'arm':d['arm'],'task_name':s['task_name'],'variation_id':s['variation_id'],'split':s['split'],'episode_id':s['episode_id'],'status':d['status'],'success':o.get('success'),'final_score':o.get('final_score'),'highest_score':o.get('highest_score'),'native_completion':o.get('native_completion'),'environment_moves':o.get('environment_moves'),'host_decisions':o.get('host_decisions'),'termination_reason':o.get('termination_reason'),'failure_type':tr.get('failure_type',d.get('error','')),'planning_mode':tr.get('planning_mode'),'retrieval_opportunity':int(d.get('retrieved',{}).get('best_layer') is not None),'template_retrieved':int(bool(d.get('retrieved',{}).get('template'))),'binding_accepted':int(bool(d.get('binding',{}).get('accepted'))) if d.get('binding') else 0,'direct_executions':tr.get('direct_use_count',0),'direct_successes':tr.get('direct_success_count',0),'guided':int(tr.get('skill_seeded',False)),'fallback':int(tr.get('fallback_triggered',False)),'native_holdout':int(tr.get('strategy_holdout',False)),'allow':verdicts.count('ALLOW'),'veto':verdicts.count('VETO'),'abstain':verdicts.count('ABSTAIN'),'gateway_proposals':len(d.get('checks',[])),'actual_actions':len(d.get('steps',[])),'model_calls':len(d.get('requests',[])),'wall_seconds':d.get('wall_seconds')}
        rows.append(row);detailed.append(d)
    out=root/'output/results';out.mkdir(parents=True,exist_ok=True)
    if rows:
        with (out/'episodes.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    grouped={}
    for split in sorted({r['split'] for r in rows}):
        for arm in sorted({r['arm'] for r in rows if r['split']==split}):
            subset=[r for r in rows if r['split']==split and r['arm']==arm];locked=[r for r in subset if r['status']=='EPISODE_LOCKED'];succ=sum(bool(r['success']) for r in locked)
            families={n:[r for r in locked if r['task_name']==n] for n in sorted({r['task_name'] for r in locked})}
            grouped[split+'/'+arm]={'started_denominator':len(subset),'locked_denominator':len(locked),'missing':len(subset)-len(locked),'successes':succ,'completion_rate':succ/len(locked) if locked else None,'type_equal_score_mean':float(np.mean([np.mean([r['final_score'] for r in v]) for v in families.values()])) if families else None,'by_task':{n:{'n':len(v),'success':sum(bool(r['success']) for r in v),'final_score_mean':float(np.mean([r['final_score'] for r in v]))} for n,v in families.items()},'mechanism_counts':{k:sum(r[k] for r in subset) for k in ('retrieval_opportunity','template_retrieved','binding_accepted','direct_executions','direct_successes','guided','fallback','native_holdout','allow','veto','abstain','actual_actions','model_calls')},'failure_types':dict(collections.Counter(r['failure_type'] for r in subset if r['failure_type']))}
    # Average repeated orders within a task/variation before any resampling.
    comparisons={}
    test=[r for r in rows if r['split']=='test' and r['status']=='EPISODE_LOCKED']
    for other in ('F','F-T','F-S','F-H'):
        pair=[]
        keys=sorted({(r['task_name'],r['variation_id']) for r in test})
        for task,var in keys:
            x=[r for r in test if r['task_name']==task and r['variation_id']==var and r['arm']=='F-I']
            y=[r for r in test if r['task_name']==task and r['variation_id']==var and r['arm']==other]
            if x and y and {r['run_id'] for r in x}=={r['run_id'] for r in y}:
                pair.append({'task':task,'variation':var,'delta':np.mean([bool(r['success']) for r in x])-np.mean([bool(r['success']) for r in y]),'by_order':{a['run_id']:int(bool(a['success']))-int(bool(next(b for b in y if b['run_id']==a['run_id'])['success'])) for a in x}})
        if pair:
            groups={n:[p for p in pair if p['task']==n] for n in {p['task'] for p in pair}};rng=np.random.default_rng(20261117);bootstrap=[];names=sorted(groups)
            for _ in range(10000):
                values=[]
                for n in rng.choice(names,size=len(names),replace=True):
                    v=groups[n];values.append(np.mean([v[i]['delta'] for i in rng.integers(0,len(v),len(v))]))
                bootstrap.append(float(np.mean(values)))
            order_names=sorted({o for p in pair for o in p['by_order']})
            comparisons['F-I_vs_'+other]={'task_variations':len(pair),'task_families':len(groups),'type_equal_completion_delta':float(np.mean([np.mean([p['delta'] for p in v]) for v in groups.values()])),'hierarchical_bootstrap_95_ci':np.quantile(bootstrap,[.025,.975]).tolist(),'order_deltas':{o:float(np.mean([p['by_order'][o] for p in pair if o in p['by_order']])) for o in order_names},'F_I_only_success_order_pairs':sum(d==1 for p in pair for d in p['by_order'].values()),'comparator_only_success_order_pairs':sum(d==-1 for p in pair for d in p['by_order'].values()),'inference_note':'Orders are repeated measures, not new independent tasks. Batch-online memory creates dependence beyond variation bootstrap; family/order results and small-sample limits remain essential. No significance selection.'}
    ledger=root/'runs-private/ledger.sqlite';costs=[]
    with sqlite3.connect(f'file:{ledger}?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row
        for r in c.execute('SELECT * FROM requests ORDER BY started'):
            d=dict(r);meta=json.loads(d['meta']);u=json.loads(d['usage']) if d['usage'] else {}
            costs.append({'request_id':d['id'],'stage':meta.get('stage',''),'run':meta.get('run',''),'arm':meta.get('arm',''),'state':d['state'],'prompt_tokens':u.get('prompt_tokens',0),'completion_tokens':u.get('completion_tokens',0),'cache_hit_tokens':u.get('prompt_cache_hit_tokens',0),'estimated_peak_usd':d['cost'],'unresolved_reservation_usd':d['reserved'] if d['state'] in ('STARTED','UNKNOWN','RESPONSE_SAVED') else 0,'finish_reason':d['finish_reason'],'parse_status':d['parse_status'],'model':d['model'],'latency_seconds':d['finished']-d['started'] if d['finished'] else None})
    if costs:
        with (out/'costs.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(costs[0]));w.writeheader();w.writerows(costs)
    summary={'run_prefixes':run_prefixes,'groups':grouped,'comparisons':comparisons,'costs':{'requests':len(costs),'estimated_peak_usd':sum(c['estimated_peak_usd'] for c in costs),'unresolved_reservation_usd':sum(c['unresolved_reservation_usd'] for c in costs),'supplier_actual_bill':None,'prompt_tokens':sum(c['prompt_tokens'] for c in costs),'completion_tokens':sum(c['completion_tokens'] for c in costs),'includes_superseded_calibration':True},'test_comparison_status':'COMPLETED' if comparisons else 'NOT_RUN_NO_CLAIM'}
    atomic_json(out/'summary.json',summary);atomic_json(out/'analysis_input_hashes.json',hashes);print(json.dumps(summary,ensure_ascii=False))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--runs',nargs='+',required=True);a=p.parse_args();analyze(Path(a.root).resolve(),a.runs)
