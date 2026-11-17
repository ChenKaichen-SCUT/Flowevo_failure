import argparse,json
from pathlib import Path
from flowevo_sw.batch_runner import run_batches
from flowevo_sw.checkpointing import read_json,atomic_json
from flowevo_sw.invariant_runtime import check

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--bank',required=True);p.add_argument('--run-id',default='dev-baseline-v1');p.add_argument('--workers',type=int,default=8);a=p.parse_args();root=Path(a.root).resolve();selection=read_json(root/'output/artifacts/task_selection.json');names=selection['selected_task_types']
    rows=[json.loads(l) for l in (root/'data/manifests/dev.jsonl').read_text().splitlines()];by={n:sorted([r for r in rows if r['task_name']==n],key=lambda r:r['sort_key'])[:4] for n in names};specs=[by[n][i] for i in range(4) for n in names if i<len(by[n])]
    results=run_batches(specs,root/'runs-private',a.run_id,bank=read_json(a.bank),workers=a.workers)
    candidates=read_json(root/'output/artifacts/candidate_rules.json');matches=[]
    for candidate in candidates:
        rule=candidate.get('rule')
        if not rule:continue
        decisions=[]
        for r in results:
            if r['status']!='EPISODE_LOCKED':continue
            history=[];last_before=None
            for s in r['steps']:
                from flowevo_sw.checkpointing import digest
                state=digest([s['before']['look'],s['before']['inventory']]);context=dict(s['before'],history=history,same_visible_state=state==last_before if last_before else None)
                verdict=check(rule,context,s['executed_action']);decisions.append({'job_id':r['job_id'],'step':s['step'],'action':s['executed_action'],'decision':verdict['decision'],'feedback':s['after']['observation']})
                history.append({'action':s['executed_action'],'feedback':s['after']['observation']});last_before=state
        matches.append({'rule_id':rule['rule_id'],'arm':candidate['arm'],'decisions':decisions,'veto_count':sum(d['decision']=='VETO' for d in decisions),'validation_status':'PASSIVE_SCREEN_ONLY_REQUIRES_REAL_INTERVENTION'})
    atomic_json(root/'output/artifacts/dev_passive_screen.json',matches)
    print(json.dumps({'episodes':len(results),'rules_screened':len(matches),'veto_counts':[m['veto_count'] for m in matches]}))
if __name__=='__main__':main()
