"""Precondition-repair labels use actual public replies, never hidden task scores."""
import argparse,json,re
from pathlib import Path
from flowevo_sw.checkpointing import read_json,atomic_json,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--probe-index',required=True);p.add_argument('--mechanisms',required=True);a=p.parse_args();root=Path(a.root).resolve();probes=read_json(a.probe_index);ms=read_json(a.mechanisms)['mechanisms'];by={m['mechanism_id']:m for m in ms};groups={};audit=[]
    for d in probes:
        original=d['branches'][0]['steps'];alt=d['branches'][1]['steps'];suffix=[]
        if original and re.search(r"isn't open|door is not open",original[0]['after']['observation'],re.I):
            for i,s in enumerate(alt):
                if i and s['action']==original[0]['action'] and 'now open' in alt[i-1]['after']['observation'].lower() and re.match(r'Inside |You move ',s['after']['observation']):suffix=alt[i-1:i+1];break
        d['independent_public_adjudication']={'verified_precondition_repair':bool(suffix),'recovery_suffix':suffix,'label_scope':'Explicit closed-state error -> observed opening -> same requested action returns movement/contents. This establishes local action functionality, not full task success.'}
        groups.setdefault(d['mechanism_id'],[]).append(d)
    admitted={mid:rs for mid,rs in groups.items() if len([r for r in rs if r['independent_public_adjudication']['verified_precondition_repair']])>=2}
    for mid,records in groups.items():
        audit.append({'mechanism_id':mid,'task_name':by[mid]['task_name'],'hypothesis':by[mid]['name'],'verified_repairs':sum(r['independent_public_adjudication']['verified_precondition_repair'] for r in records),'status':'TWO_VARIATION_LOCAL_REPAIR' if mid in admitted else 'NOT_CONFIRMED_AS_A_REPAIR','reason':'No two clean prepare-state -> same-action functional repairs under the bounded probes. State change, interface ambiguity, or scientific knowledge may still be real; this is not proof of no mechanism.'})
    names=sorted({by[mid]['task_name'] for mid in admitted},key=lambda n:digest([20261117,'selection',n]))[:6]
    selected=[r for mid,rs in admitted.items() if by[mid]['task_name'] in names for r in rs]
    success_counts={};total_counts={}
    for f in (root/'runs-private/episodes').glob('discovery-v2.F.*.json'):
        if '.prefix.' in f.name:continue
        d=read_json(f);n=d['spec']['task_name'];total_counts[n]=total_counts.get(n,0)+1;success_counts[n]=success_counts.get(n,0)+int(d.get('outcome',{}).get('success',False))
    if not any(success_counts.get(n,0)>0 for n in names):raise RuntimeError('Selected scope has no baseline successful case; additional fixed TRAIN exploration required')
    easy=[n for n,k in success_counts.items() if k==total_counts[n] and n not in names]
    controls=sorted(easy,key=lambda n:digest([20261117,'control',n]))[:2]
    preliminary=root/'output/artifacts/task_selection.json'
    if preliminary.exists():atomic_json(root/'output/artifacts/task_selection_provisional.json',read_json(preliminary))
    selection={'selected_task_types':names,'out_of_scope_controls':controls,'selection_policy':'TRAIN-only hypotheses, replicated same-prefix public precondition repair in two variations, finite legal alternatives, baseline success present in the scope; SHA tie breaker if more than six eligible families. Initial quote-only shortlist was provisional and superseded before additional TRAIN, DEV or TEST.','train_target_per_type':12,'dev_target_per_type':4,'test_target_per_type':6,'order_seeds':[17,29],'source_mechanisms':sorted(admitted),'baseline_success_counts':{n:success_counts[n] for n in names},'status':'FROZEN_AFTER_TRAIN_PROBES'}
    atomic_json(preliminary,selection);atomic_json(root/'output/artifacts/probe_adjudication.json',audit);atomic_json(root/'runs-private/selected_probes.json',selected)
    print(json.dumps(selection))
if __name__=='__main__':main()
