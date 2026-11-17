"""Additional descriptive audit of locked logs; no model calls or rescoring."""
import argparse,json,sqlite3,collections
from pathlib import Path
import numpy as np
from flowevo_sw.checkpointing import read_json,atomic_json
from flowevo_sw.invariant_runtime import check

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');a=p.parse_args();root=Path(a.root).resolve();private=root/'runs-private';eps=[]
    for f in sorted((private/'episodes').glob('*.json')):
        if '.prefix.' not in f.name:
            d=read_json(f)
            if d.get('status')=='EPISODE_LOCKED':eps.append(d)
    compilation=collections.defaultdict(collections.Counter);governance=collections.defaultdict(collections.Counter)
    for f in sorted((private/'compilations').glob('*.json')):
        d=read_json(f)
        if d is None:continue
        run=f.name.split('.')[0];c=compilation[run];c['successful_episodes_submitted']+=1
        c['valid_templates']+=bool(d.get('template'));c['guidelines']+=bool(d.get('exemplar'));c['template_rejections']+=bool(d.get('rejection'));c['errors']+=bool(d.get('error'))
    for f in sorted((private/'banks').glob('*.json')):
        d=read_json(f);run=f.name.split('.')[0];c=governance[run]
        for ev in d['events']:
            c['published_episodes']+=1;c['templates_admitted']+=bool(ev['admitted']);c['audits']+=not ev['audit'].get('not_due',False)
            for key,value in ev['status_after'].items():
                if value!=ev['status_before'].get(key):c['status_to_'+str(value)]+=1
    rules=read_json(root/'output/artifacts/protocol.json')['rules'];veto_events=[];shadow=[];byrun={};skills=[]
    for run in sorted({d['run_id'] for d in eps}):
        ds=[d for d in eps if d['run_id']==run];byrun[run]={'episodes':len(ds),'successes':sum(d['outcome']['success'] for d in ds),'modes':dict(collections.Counter(d['trace']['planning_mode'] for d in ds)),'summed_episode_wall_seconds':sum(d['wall_seconds'] for d in ds),'termination':dict(collections.Counter(d['outcome']['termination_reason'] for d in ds)),'final_vs_highest_differ':sum(d['outcome']['final_score']!=d['outcome']['highest_score'] for d in ds)}
        for task in sorted({d['spec']['task_name'] for d in ds}):
            subset=[d for d in ds if d['spec']['task_name']==task]
            skills.append({'run':run,'task':task,'episodes':len(subset),'retrieved':sum(d['retrieved']['best_layer'] is not None for d in subset),'binding_accepted':sum(bool(d.get('binding',{}).get('accepted')) if d.get('binding') else 0 for d in subset),'direct':sum(d['trace']['direct_use_count'] for d in subset),'direct_success':sum(d['trace']['direct_success_count'] for d in subset),'guided':sum(d['trace']['skill_seeded'] for d in subset),'fallback':sum(d['trace']['fallback_triggered'] for d in subset)})
    for d in eps:
        for item in d['checks']:
            if not any(v.get('decision')=='VETO' for v in item['verdicts']):continue
            next_step=next((s for s in d['steps'] if s['step']==item['checkpoint']+1),None)
            view=d['initial'] if item['checkpoint']==0 else d['steps'][item['checkpoint']-1]['after']
            veto_events.append({'job_id':d['job_id'],'arm':d['arm'],'split':d['spec']['split'],'checkpoint':item['checkpoint'],'action':item['action'],'source':item['source'],'replanned':item['replanned'],'verdicts':item['verdicts'],'executable_FI_decisions':[check(r,dict(view,history=[]),item['action'])['decision'] for r in rules['F-I']],'next_action':next_step['executed_action'] if next_step else None,'next_feedback':next_step['after']['observation'] if next_step else None,'changed_action':bool(next_step and next_step['executed_action']!=item['action']),'episode_success':d['outcome']['success']})
        if d['arm']=='F' and d['spec']['split']=='test':
            for s in d['steps']:
                for arm in ('F-I','F-S','F-H'):
                    for rule in rules[arm]:
                        verdict=check(rule,dict(s['before'],history=[]),s['executed_action'])
                        if verdict['decision']=='VETO':shadow.append({'job_id':d['job_id'],'rule_arm':arm,'rule_id':rule['rule_id'],'step':s['step'],'action':s['executed_action'],'observed_feedback':s['after']['observation'],'label':'POSTHOC_PASSIVE_OPPORTUNITY_NOT_INTERVENTION'})
    with sqlite3.connect(f'file:{private/"ledger.sqlite"}?mode=ro',uri=True) as c:
        c.row_factory=sqlite3.Row;ledger=[dict(r) for r in c.execute('select * from requests')]
    costs=collections.defaultdict(lambda:collections.Counter());timings={}
    for row in ledger:
        m=json.loads(row['meta']);key=m.get('run','')+'/'+m.get('arm','')+'/'+m.get('stage','');u=json.loads(row['usage'] or '{}');cc=costs[key]
        cc['requests']+=1;cc['estimated_peak_usd']+=row['cost'];cc['prompt_tokens']+=u.get('prompt_tokens',0);cc['completion_tokens']+=u.get('completion_tokens',0)
    for run in byrun:
        rr=[r for r in ledger if json.loads(r['meta']).get('run')==run and r['finished'] is not None]
        if rr:timings[run]={'first_request':min(r['started'] for r in rr),'last_response':max(r['finished'] for r in rr),'request_span_seconds':max(r['finished'] for r in rr)-min(r['started'] for r in rr),'summed_request_seconds':sum(r['finished']-r['started'] for r in rr),'note':'Span excludes JVM startup before first request; summed latency is descriptive, not a measured serial rerun.'}
    resource=[json.loads(l) for l in (private/'resource_samples.jsonl').read_text().splitlines()];rr={}
    if resource:rr={'samples':len(resource),'first_epoch':resource[0]['utc_epoch'],'last_epoch':resource[-1]['utc_epoch'],'max_observed_experiment_rss_gib':max(r['experiment_rss'] for r in resource)/2**30,'min_available_memory_gib':min(r['available_memory'] for r in resource)/2**30,'mean_cpu_percent':float(np.mean([r['cpu_percent'] for r in resource])),'max_java_processes':max(r['java_processes'] for r in resource),'note':'5-second sampling; excludes short unseen peaks, includes simultaneous clean reproduction. Process cmdline filter may miss relative-command coordinator Python; JVM included.'}
    direct_routes=[{'job_id':d['job_id'],'task':d['spec']['task_name'],'split':d['spec']['split'],'direct_path_entered':d['trace']['direct_use_count'],'actual_direct_actions':sum(s['source']=='direct_skill' for s in d['steps']),'block_reason':d['trace']['runtime_skill_block_reason'],'fallback':d['trace']['fallback_triggered'],'direct_success':d['trace']['direct_success_count'],'episode_success':d['outcome']['success']} for d in eps if d['trace']['direct_use_count']]
    result={'compilation':dict(compilation),'governance':dict(governance),'runs':byrun,'skills_by_run_task':skills,'direct_routes':direct_routes,'veto_events':veto_events,'posthoc_baseline_opportunities':shadow,'costs_by_run_arm_stage':dict(costs),'timings':timings,'resource_sampling':rr,'failure_taxonomy_note':'Native noncompletion, parse/delivery/infrastructure and persistent-veto errors are separate. Public-feedback case interpretation is descriptive, not oracle labeling.'}
    atomic_json(root/'output/results/audit_summary.json',result);print(json.dumps({'runs':byrun,'veto_events':len(veto_events),'posthoc_baseline_opportunities':len(shadow),'resource_sampling':rr}))
if __name__=='__main__':main()
