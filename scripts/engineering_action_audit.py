"""Audit every archived action response, including non-executed proposals."""
import argparse,collections,json
from pathlib import Path
from flowevo_sw.action_consistency import inspect_response
from engineering_common import read,write,csv_write,records,digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='..');args=parser.parse_args()
    root=Path(args.root).resolve();inp=root/'input-snapshot';out=root/'output';episodes=records(inp)
    executed={s['request_id']:(d,s) for d in episodes.values() for s in d['steps'] if s.get('request_id')}
    rows=[];counts=collections.Counter();details=[]
    for file in sorted((inp/'requests').glob('*.action.*.request.json')):
        request=read(file);rid=request['request_id'];response_file=file.with_name(file.name.replace('.request.json','.json'))
        if not response_file.exists():continue
        response=read(response_file)['response'];raw=response['choices'][0]['message'].get('content','')
        step=executed.get(rid);context_source='REQUEST_PUBLIC'
        try:user=json.loads(request['payload']['messages'][-1]['content']);view=user.get('public',{})
        except (ValueError,TypeError):view={}
        if not view:
            view=step[1]['before'] if step else {};context_source='SAVED_PRE_ACTION' if step else 'UNAVAILABLE_LEGACY_FORMAT'
        diagnosis=inspect_response(raw,view)
        if context_source=='UNAVAILABLE_LEGACY_FORMAT':
            for warning in diagnosis['warnings']:
                if warning['category']=='ACTION_FORMAT':warning.update(category='LEGACY_FORMAT_UNSUPPORTED',level='NOT_VERIFIED')
        try:parsed=json.loads(raw)
        except (TypeError,ValueError):parsed={}
        jid=rid.rsplit('.action.',1)[0];episode=episodes.get(jid)
        categories=[x['category'] for x in diagnosis['warnings']];counts.update(categories)
        counts['responses']+=1;counts['focus_responses']+=str(parsed.get('action','')).startswith('focus on ')
        counts['relation:'+diagnosis['reason_action_relation']]+=1
        if step:assert diagnosis.get('parsed_action','').strip()==step[1]['parsed_action']
        rows.append({'request_id':rid,'job_id':jid,'run':episode['run_id'] if episode else request.get('meta',{}).get('run'),
          'arm':episode['arm'] if episode else request.get('meta',{}).get('arm'),'split':episode['spec']['split'] if episode else request.get('meta',{}).get('split'),
          'executed':bool(step),'step':step[1]['step'] if step else None,'public_context_source':context_source,'goal':view.get('goal',''),
          'action':parsed.get('action'),'reason':parsed.get('reason'),'warnings':';'.join(categories),
          'reason_action_relation':diagnosis['reason_action_relation'],'grounding':diagnosis['grounding'],
          'focus_role':diagnosis['focus_role'],'policy':diagnosis['policy'],'evidence':json.dumps(diagnosis['warnings'],ensure_ascii=False),
          'public_input_hash':digest(view),'source_ref':'requests/'+file.name})
        details.append({'request_id':rid,'diagnosis':diagnosis})
    csv_write(out/'results/engineering/action_response_audit.csv',rows)
    write(out/'artifacts/engineering/action_audit.json',{'summary':dict(counts),'responses':details,
        'scope':'Warnings use saved request public input and raw response only; no scores/after-state. Unexecuted proposals included.','new_model_calls':0,'rewritten_actions':0})
    # Fixed archived regression anchors; errors include one deliberately unhandled
    # biological-category case to expose the boundary of a literal interface check.
    anchors={'06eebbde9128242aba13':'REASON_ACTION_CONFLICT','5de4ccea5ffbd8f8b877':'REASON_ACTION_CONFLICT',
             '20e65c56c84af8ab157f':'TARGET_OBJECT_MISMATCH','81f896325b22612a849e':'TARGET_OBJECT_MISMATCH',
             '02e77cda31db3b964346':'FOCUS_AS_INSPECTION','1b4703786cd7f2ff0592':'KNOWLEDGE_REQUIRED_NOT_LITERAL_INTERFACE'}
    regressions=[]
    for suffix,expected in anchors.items():
        episode=episodes['discovery-v2.F.'+suffix];last=episode['steps'][-1]
        row=next(x for x in rows if x['request_id']==last['request_id'])
        regressions.append({'job_id':episode['job_id'],'step':last['step'],'reference_review':expected,
          'flagged':expected in row['warnings'].split(';'),'observed_warnings':row['warnings'],
          'reason':row['reason'],'action':row['action'],'scope':'Known TRAIN regression case, not independent precision/recall estimation'})
    normal=[x for x in rows if x['split'] in ('train','dev') and x['reason_action_relation']=='NORMAL_WORDING_VARIANT' and not x['warnings']][:12]
    csv_write(out/'results/engineering/action_regression_cases.csv',regressions)
    csv_write(out/'results/engineering/action_wording_examples.csv',normal)
    print(json.dumps({'responses':len(rows),'executed_responses':sum(x['executed'] for x in rows),'warning_counts':dict(counts),'new_model_calls':0}))
if __name__=='__main__':main()
