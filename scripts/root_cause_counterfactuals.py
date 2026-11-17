"""Predeclared, free JVM diagnostics. No new agent decisions or provider client.

All target objects come from saved public state/reason. Both plane candidates are
tested, never selecting a winner for a new efficacy score.
"""
import argparse,json,re,hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from root_cause_audit import read,write_csv,js

def run(item):
    from flowevo_sw.adapter import ScienceWorldAdapter
    from flowevo_sw.checkpointing import digest
    root,case=item;inp=Path(root)/'input-snapshot';d=read(inp/'episodes'/(case['job_id']+'.json'));records=[]
    for branch,commands in [('factual',case['factual']),('alternative',case['alternative'])]:
        env=ScienceWorldAdapter();env.reset(d['spec']['task_name'],d['spec']['variation_id']);assert digest(env.view)==digest(d['initial'])
        for s in d['steps'][:case['prefix_len']]:
            env.execute(s['executed_action']);assert digest(env.view)==s['observation_hash'],case['case_id']+' prefix mismatch'
        start=digest(env.view);steps=[];blocked=None
        for action in commands:
            if env.done:break
            if branch=='alternative' and case.get('strict_direct') and action not in env.view['valid_actions']:
                blocked=action;break
            before=digest(env.view);env.execute(action);steps.append({'action':action,'feedback':env.view['observation'],'look':env.view['look'],'before_hash':before,'after_hash':digest(env.view)})
        records.append({'branch':branch,'start_hash':start,'steps':steps,'blocked_by_original_public_validity_check':blocked,'outcome':env.outcome()});env.close()
    assert records[0]['start_hash']==records[1]['start_hash']
    return dict(case,branches=records,prefix_verified=True,api_calls=0)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--workers',type=int,default=4);p.add_argument('--summarize-receipts',help='Only serialize existing receipts to CSV; does not run or verify JVM branches');a=p.parse_args();root=Path(a.root).resolve();inp=root/'input-snapshot';out=root/'output';episodes={}
    if a.summarize_receipts:
        summarize(out,read(Path(a.summarize_receipts)));return
    for f in sorted((inp/'episodes').glob('*.json')):
        if '.prefix.' not in f.name:d=read(f);episodes[d['job_id']]=d
    cases=[]
    def add(jid,n,alt,hyp,scope,strict=False):
        d=episodes[jid];remaining=100-n;budget=min(3,remaining);case={'case_id':f'CF{len(cases)+1:02d}','job_id':jid,'task':d['spec']['task_name'],'variation':d['spec']['variation_id'],'split':d['spec']['split'],'prefix_len':n,'hypothesis':hyp,'factual':[s['executed_action'] for s in d['steps'][n:n+budget]],'alternative':alt[:budget],'strict_direct':strict,'scope':scope};cases.append(case)
    for suffix in ('02e77cda31db3b964346','0ef2ea6f576b10fb9a37','20e65c56c84af8ab157f','81f896325b22612a849e','d129caa70cba348ea3e4','1b4703786cd7f2ff0592'):
        jid='discovery-v2.F.'+suffix;d=episodes[jid];s=d['steps'][-1];assert s['executed_action'].startswith('focus on ')
        add(jid,len(d['steps'])-1,['look at '+s['executed_action'][9:]],'H2_FOCUS_SEMANTICS','Replace commitment by inspection of exactly the same object; survival only, not solved task.')
    for suffix in ('06eebbde9128242aba13','5de4ccea5ffbd8f8b877'):
        jid='discovery-v2.F.'+suffix;d=episodes[jid];assert 'green box' in d['steps'][-1]['raw_model_response']
        add(jid,len(d['steps'])-1,['focus on green box'],'H2_REASON_ACTION_MISMATCH','Alternative explicitly present in saved model reason; no new answer/knowledge supplied.')
    for suffix in ('3c034ff32bf35c264df7','ef2e54dbb3a42029c804'):
        jid='discovery-v2.F.'+suffix;d=episodes[jid];assert 'bathroom' in d['initial']['goal']
        n=max(i for i,s in enumerate(d['steps'][:99]) if s['before']['look'].startswith('This room is called the hallway.'));v=d['steps'][n]['before']
        visited={re.search(r'This room is called the (.*?)\.',s['before']['look']).group(1) for s in d['steps'][:n+1]}
        targets=sorted(set(re.findall(r'A door to the (.*?) \(that is',v['look']))-visited);assert targets
        target=targets[0];acts=['go to '+target] if 'go to '+target in v['valid_actions'] else ['open door to '+target,'go to '+target]
        add(jid,n,acts,'H3_NAVIGATION_LOOP','Last hallway checkpoint with two actions remaining; first alphabetic publicly visible unvisited neighbor. Break cycle only; goal route unknown and no model continuation.')
    for run_prefix in ('selected-train-v1','dev-baseline-v1'):
        eligible=[d for d in episodes.values() if d['run_id']==run_prefix and d['arm']=='F' and (d['retrieved'].get('template') or {}).get('template_id')=='sw_9b4527b829af33c8']
        picked=0
        for d in sorted(eligible,key=lambda d:d['job_id']):
            available=next((s for s in d['steps'] if any(x.startswith('look at inclined plane with a ') for x in s['before']['valid_actions'])),None)
            if not available:continue
            planes=sorted({x[8:] for x in available['before']['valid_actions'] if x.startswith('look at inclined plane with a ')})
            for plane in planes:
                add(d['job_id'],available['step']-1,[x.format(plane=plane) for x in d['retrieved']['template']['action_template']],'H1_DELAYED_BINDING','First visible-plane checkpoint; enumerate every public candidate, do not choose by score.',True)
            picked+=1
            if picked==2:break
    plan={'selection':'Fixed explicit diagnostic IDs for focus/reason/navigation; first two SHA-ordered eligible TRAIN and DEV plane episodes, all visible plane candidates. No TEST replay. Frozen before branch execution.','cases':cases,'new_api_calls':0}
    p=out/'artifacts/root_cause_counterfactual_plan.json'
    if p.exists():assert read(p)==plan
    p.write_text(js(plan))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:results=list(pool.map(run,[(str(root),c) for c in cases]))
    (out/'artifacts/root_cause_counterfactual_receipts.json').write_text(js(results));summarize(out,results)

def summarize(out,results):
    rows=[]
    for r in results:
        f,b=r['branches'];changed=f['steps']!=b['steps'];rows.append({'case_id':r['case_id'],'job_id':r['job_id'],'task':r['task'],'variation':r['variation'],'split':r['split'],'hypothesis':r['hypothesis'],'prefix_len':r['prefix_len'],'prefix_verified':r['prefix_verified'],'factual_actions':js(r['factual']),'alternative_actions':js(r['alternative']),'factual_feedback':js(f['steps']),'alternative_feedback':js(b['steps']),'factual_score':f['outcome']['final_score'],'alternative_score':b['outcome']['final_score'],'factual_success':f['outcome']['success'],'alternative_success':b['outcome']['success'],'alternative_blocked':b['blocked_by_original_public_validity_check'],'evidence_level':'LOCAL_COUNTERFACTUAL_SUPPORTED' if changed else 'NOT_VERIFIED','scope':r['scope'],'new_api_calls':0,'new_api_cost_cny':0,'source_ref':'artifacts/root_cause_counterfactual_receipts.json#'+r['case_id']})
    write_csv(out/'results/minimal_counterfactuals.csv',rows);print(js([{k:v for k,v in x.items() if k not in ('factual_feedback','alternative_feedback')} for x in rows]))
if __name__=='__main__':main()
