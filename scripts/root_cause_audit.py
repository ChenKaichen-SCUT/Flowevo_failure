"""Phase A. Deterministic offline audit; no credentials and no model calls.

Input is an immutable private copy or the existing public restoration output.
CSV is the requested machine-readable research database, not a workbook.
"""
import argparse,json,csv,re,hashlib,collections,sqlite3
from pathlib import Path

def read(p):return json.loads(p.read_text())
def js(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def cohort(d):
    r=d['run_id']
    if r=='discovery-v1':return 'SUPERSEDED_ENGINEERING'
    if r.startswith('batch-sensitivity'):return 'REPEATED_TRAIN_SENSITIVITY'
    if d['arm']=='F':return 'PRIMARY_BASELINE'
    return 'OTHER_ARM_DESCRIPTIVE'
def reason(s):
    try:return json.loads(s.get('raw_model_response') or '{}').get('reason','')
    except ValueError:return ''
def tags(s,previous):
    a=s['executed_action'];o=s['after']['observation'];out=[]
    if re.search(r"isn't open|door is not open",o,re.I):out.append('CLOSED_ACCESS_FEEDBACK')
    if 'No known action matches' in o:out.append('UNRECOGNIZED_COMMAND_FEEDBACK')
    if 'Ambiguous request' in o:out.append('AMBIGUITY_MENU')
    if 'Connections must specify specific points' in o:out.append('ELECTRICAL_TERMINAL_SYNTAX_FEEDBACK')
    if 'not movable' in o:out.append('IMMOVABLE_OBJECT_FEEDBACK')
    if 'already open' in o:out.append('REDUNDANT_OPEN_FEEDBACK')
    if s['host_outcome']['final_score']<0:out.append('NEGATIVE_TERMINAL_STEP')
    rr=reason(s)
    if a.startswith('focus on ') and re.search(r'inspect|reveal|examine|learn.*propert',rr,re.I):out.append('FOCUS_AS_INSPECTION_LANGUAGE_CANDIDATE')
    key=(a,s['before']['look'],s['before']['inventory'],o)
    if key in previous and not a.startswith(('wait','activate','deactivate')):out.append('REPEATED_ACTION_SAME_VISIBLE_CONTEXT')
    previous[key]=s['step']
    return out
def align(actions,steps,patterns=False):
    pos=0;matched=[];values=collections.defaultdict(set)
    for a in actions:
        parts=re.split(r'(\{\w+\})',a);names=[];pat=''
        for part in parts:
            if part.startswith('{') and part.endswith('}'):
                names.append(part[1:-1]);pat+='(.+?)'
            else:pat+=re.escape(part)
        found=None
        for k in range(pos,len(steps)):
            actual=steps[k]['executed_action'];m=re.fullmatch(pat,actual) if patterns else None
            if (patterns and m) or (not patterns and actual==a):found=k;break
        if found is None:return matched,dict((k,sorted(v)) for k,v in values.items()),a
        if patterns:
            for n,v in zip(names,m.groups()):values[n].add(v)
        matched.append(steps[found]);pos=found+1
    return matched,dict((k,sorted(v)) for k,v in values.items()),None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',default='..');a=ap.parse_args();root=Path(a.root).resolve();inp=root/'input-snapshot';out=root/'output';res=out/'results';episodes={}
    for f in sorted((inp/'episodes').glob('*.json')):
        if '.prefix.' not in f.name:
            d=read(f);assert d['status']=='EPISODE_LOCKED';episodes[d['job_id']]=d
    order={}
    for f in inp.glob('*.plan.json'):
        p=read(f)
        for i,s in enumerate(p['specs']):
            for arm in p['arms']:order[f.name[:-10]+'.'+arm+'.'+s['episode_id']]=i+1
    decisions=[];tax=[];skills=[];compstats=collections.defaultdict(collections.Counter);aggregate=collections.defaultdict(collections.Counter)
    events={}
    for f in (inp/'banks').glob('*.json'):
        for ev in read(f)['events']:events[ev['job_id']]=ev
    for jid,d in episodes.items():
        spec=d['spec'];trace=d['trace'];seen={};counts=collections.Counter();evidence=[];group=cohort(d)
        for s in d['steps']:
            prev_step=seen.get((s['executed_action'],s['before']['look'],s['before']['inventory'],s['after']['observation']))
            ts=tags(s,seen);counts.update(ts)
            if ts:evidence.append({'step':s['step'],'action':s['executed_action'],'feedback':s['after']['observation'],'labels':ts,'request_id':s['request_id']})
            decisions.append({'job_id':jid,'cohort':group,'run_id':d['run_id'],'arm':d['arm'],'task':spec['task_name'],'variation':spec['variation_id'],'split':spec['split'],'order_index':order.get(jid),'step':s['step'],'goal':d['initial']['goal'],'public_look':s['before']['look'],'inventory':s['before']['inventory'],'previous_observation':s['before']['observation'],'action':s['executed_action'],'public_feedback':s['after']['observation'],'model_reason':reason(s),'request_id':s['request_id'],'action_source':s['source'],'observed_labels':';'.join(ts),'evidence_level':'OBSERVED_ERROR' if any(t.endswith('_FEEDBACK') and t not in ('REDUNDANT_OPEN_FEEDBACK',) for t in ts) else 'NOT_VERIFIED' if ts else 'NO_FLAG','upstream_cause':'UNKNOWN','source_ref':f"episodes/{jid}.json#/steps/{s['step']-1}",'public_hash':s['observation_hash']})
            decisions[-1].update(repeat_previous_step=prev_step,repeat_gap=s['step']-prev_step if prev_step else None,repeat_feedback_in_recent_16=bool(prev_step and s['step']-prev_step<=16))
        b=d.get('binding');t=d['retrieved'].get('template');guidance=d['retrieved'].get('exemplar');last=d['steps'][-1] if d['steps'] else None
        calls=d.get('requests',[]);usage=collections.Counter()
        for c in calls:usage.update({k:c.get('usage',{}).get(k,0) for k in ('prompt_tokens','completion_tokens')})
        causes=[]
        if counts['FOCUS_AS_INSPECTION_LANGUAGE_CANDIDATE']:causes.append('PUBLIC_ACTION_SEMANTICS_OR_GROUNDING_PLAUSIBLE')
        if counts['REPEATED_ACTION_SAME_VISIBLE_CONTEXT']:causes.append('PLANNING_OR_MEMORY_PLAUSIBLE')
        if counts['ELECTRICAL_TERMINAL_SYNTAX_FEEDBACK']:causes.append('INTERFACE_OR_EXPERIMENT_DESIGN_PLAUSIBLE')
        if not causes:causes=['UNKNOWN']
        if len(causes)>1:causes.append('MULTIPLE_PLAUSIBLE_CAUSES')
        tax.append({'job_id':jid,'cohort':group,'run_id':d['run_id'],'arm':d['arm'],'task':spec['task_name'],'variation':spec['variation_id'],'split':spec['split'],'order_index':order.get(jid),'goal':d['initial']['goal'],'success':d['outcome']['success'],'final_score':d['outcome']['final_score'],'termination':d['outcome']['termination_reason'],'executor_error':trace['failure_type'],'steps':len(d['steps']),'model_calls':len(calls),**dict(usage),'planning_mode':trace['planning_mode'],'native_holdout':trace['strategy_holdout'],'retrieved_template':t['template_id'] if t else '', 'binding_accepted':b.get('accepted') if b else None,'actual_direct_actions':sum(s['source']=='direct_skill' for s in d['steps']),'observed_error_labels':';'.join(sorted(counts)),'possible_upstream_causes':';'.join(causes),'causal_conclusion':'INSUFFICIENT_EVIDENCE','key_evidence':js(evidence[:2]+([evidence[-1]] if len(evidence)>2 else [])),'final_action':last['executed_action'] if last else '', 'final_feedback':last['after']['observation'] if last else '', 'source_ref':f'episodes/{jid}.json'})
        aggregate[group]['episodes']+=1;aggregate[group]['successes']+=d['outcome']['success'];aggregate[group]['steps']+=len(d['steps'])
        for key in counts:aggregate[group][key+'_episodes']+=1
        if not d['outcome']['success']:
            for key in counts:aggregate[group][key+'_failed_episodes']+=1
        later=None
        if t and spec['task_name']=='inclined-plane-friction-named-surfaces':
            later=next((s['step'] for s in d['steps'] if any(ac.startswith('look at inclined plane with a ') for ac in s['before']['valid_actions'])),None)
        source=episodes.get(t.get('source_trace_id')) if t else None
        fields={'event':'RETRIEVAL_AND_BINDING','job_id':jid,'cohort':group,'task':spec['task_name'],'success':d['outcome']['success'],'template_id':t['template_id'] if t else '', 'source_trace':t.get('source_trace_id','') if t else '', 'source_goal':source['initial']['goal'] if source else '', 'target_goal':d['initial']['goal'],'template_actions':js(t['action_template']) if t else '', 'generated_applicability_discarded':bool(t),'source_validation_rejection':'','first_unmatched_action':'','collapsed_parameter_values':'','admitted':'','admission_reason':'','binding_accepted':b['accepted'] if b else None,'binding_reason':b['parsed'].get('reason','') if b else '', 'bindings':js(b['parsed'].get('bindings',{})) if b else '', 'late_plane_visible_before_step':later,'direct_path_entered':trace['direct_use_count'],'actual_direct_actions':sum(s['source']=='direct_skill' for s in d['steps']),'fallback':trace['fallback_triggered'],'guided':trace['skill_seeded'],'retrieved_guidance':js(guidance),'source_steps_with_error_feedback':'','credit_recorded_without_direct_path':bool(t and d['retrieved']['best_layer']==1 and trace['direct_use_count']==0 and jid in events),'evidence_level':'OBSERVED_ERROR' if t and d['retrieved']['best_layer']==1 and trace['direct_use_count']==0 and jid in events else 'OBSERVED_RECORD','source_ref':f'episodes/{jid}.json#/binding'}
        skills.append(fields)
        cf=inp/'compilations'/(jid+'.json');c=read(cf) if cf.exists() else None
        if c:
            gen=c.get('raw_parsed') or {};template=c.get('template');acts=gen.get('action_template',[]);bindings=gen.get('example_bindings',{})
            try:inst=[ac.format(**bindings) for ac in acts]
            except (KeyError,ValueError):inst=[]
            matched,_,miss=align(inst,d['steps']);alt,values,altmiss=align(acts,d['steps'],True)
            errors=[{'step':s['step'],'action':s['executed_action'],'feedback':s['after']['observation']} for s in matched if any(t in tags(s,{}) for t in ('UNRECOGNIZED_COMMAND_FEEDBACK','ELECTRICAL_TERMINAL_SYNTAX_FEEDBACK','CLOSED_ACCESS_FEEDBACK','IMMOVABLE_OBJECT_FEEDBACK'))]
            ev=events.get(jid,{});admitted=ev.get('admitted');stats=compstats[group];stats['candidates']+=1;stats['validated_templates']+=bool(template);stats['rejected_templates']+=bool(c.get('rejection'));stats['admitted']+=bool(admitted);stats['guidelines']+=bool(c.get('exemplar'));stats['position_specific_rebinding_matches_source']+=bool(c.get('rejection') and not altmiss);stats['valid_templates_containing_error_feedback']+=bool(template and errors)
            row=dict(fields,event='COMPILATION',template_id=template['template_id'] if template else '',source_trace=jid,source_goal=d['initial']['goal'],target_goal='',template_actions=js(acts),generated_applicability_discarded='applicability' in gen,source_validation_rejection=c.get('rejection'),first_unmatched_action=miss,collapsed_parameter_values=js({k:v for k,v in values.items() if len(v)>1}) if not altmiss else '',admitted=admitted,admission_reason='ADMITTED' if admitted else 'SOURCE_VALIDATION_FAILED' if not template else 'EXISTING_ACTIVE_TEMPLATE_UTILITY_GTE_0.5' if admitted is False else 'NO_PUBLISHED_EVENT',source_steps_with_error_feedback=js(errors),source_ref=f'compilations/{jid}.json',credit_recorded_without_direct_path=False)
            skills.append(row)
    write_csv(res/'failure_taxonomy.csv',tax);write_csv(res/'trajectory_decision_audit.csv',decisions);write_csv(res/'skill_lifecycle_audit.csv',skills)
    # First action divergence in one deterministic success/failure pair per family.
    pairs=[]
    for task in sorted({d['spec']['task_name'] for d in episodes.values()}):
        ds=[d for d in episodes.values() if d['spec']['task_name']==task and d['run_id']=='discovery-v2'];wins=[d for d in ds if d['outcome']['success']];loss=[d for d in ds if not d['outcome']['success']]
        if not wins or not loss:continue
        w,l=wins[0],loss[0];n=next((i for i,(x,y) in enumerate(zip(w['steps'],l['steps'])) if x['executed_action']!=y['executed_action']),0)
        pairs.append({'task':task,'success_job':w['job_id'],'failure_job':l['job_id'],'first_action_divergence_step':n+1,'success_goal':w['initial']['goal'],'failure_goal':l['initial']['goal'],'same_initial_public_state':w['initial']==l['initial'],'success_action':w['steps'][n]['executed_action'],'failure_action':l['steps'][n]['executed_action'],'success_feedback':w['steps'][n]['after']['observation'],'failure_feedback':l['steps'][n]['after']['observation'],'note':'Different variation/goal/start state; earliest lexical divergence is not a causal attribution.'})
    write_csv(res/'success_failure_pairs.csv',pairs)
    guidance=[]
    for task in sorted({r['task'] for r in tax if r['cohort']=='PRIMARY_BASELINE'}):
        for mode in ('guided','unguided'):
            ds=[d for d in episodes.values() if cohort(d)=='PRIMARY_BASELINE' and d['spec']['task_name']==task and bool(d['trace']['skill_seeded'])==(mode=='guided')]
            if ds:guidance.append({'task':task,'mode':mode,'n':len(ds),'successes':sum(d['outcome']['success'] for d in ds),'holdout_n':sum(d['trace']['strategy_holdout'] for d in ds),'note':'Descriptive, mixes stages; exposure/bank/order/variation confounded. No synthetic prompt-removal counterfactual.'})
    write_csv(res/'guidance_descriptive.csv',guidance)
    summ={'cohorts':dict(aggregate),'compilation':dict(compstats),'unique_primary_task_variations':len({(d['spec']['task_name'],d['spec']['variation_id'],d['spec']['split']) for d in episodes.values() if cohort(d)=='PRIMARY_BASELINE'}),'all_episodes':len(episodes),'all_actions':len(decisions),'usage_rows':sum(s['event']=='RETRIEVAL_AND_BINDING' for s in skills),'compilation_rows':sum(s['event']=='COMPILATION' for s in skills),'primary_binding_requests':sum(bool(d.get('binding')) for d in episodes.values() if cohort(d)=='PRIMARY_BASELINE'),'main_F_template_retrieved':sum(bool(d['retrieved'].get('template')) for d in episodes.values() if d['run_id'].startswith('main-') and d['arm']=='F'),'main_F_late_plane_visible':sum(bool(s['late_plane_visible_before_step']) for s in skills if s['event']=='RETRIEVAL_AND_BINDING' and s['job_id'].startswith('main-') and '.F.' in s['job_id']),'credit_without_execution':dict(collections.Counter(s['cohort'] for s in skills if s['credit_recorded_without_direct_path'])),'label_policy':'Deterministic observed-feedback flags and lexical candidates; causal conclusions UNKNOWN unless separately adjudicated. Never five-arm pooling into baseline.'}
    (out/'artifacts/root_cause_summary.json').write_text(js(summ));print(js(summ))
if __name__=='__main__':main()
