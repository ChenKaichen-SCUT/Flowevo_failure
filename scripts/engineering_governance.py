"""Replay recorded publications, never model policies or task outcomes."""
import argparse,collections,copy,json
from pathlib import Path
from alfworld_.skill_library import SkillLibrary
from flowevo_sw.credit_accounting import ScienceSkillLibrary
from engineering_common import read,write,digest,csv_write,publisher,records

RUN_ORDER=['discovery-v1','discovery-v2','selected-train-v1','batch-sensitivity-1-v1','batch-sensitivity-8-v1','dev-baseline-v1','main-order-17-v1','main-order-29-v1','control-order-17-v1']
def retrieved_signature(lib,record):
    value=lib.retrieve(record['spec']['task_name'])
    if record['spec'].get('native_holdout'):
        value['exemplar']=None;value['insight']=None
    return signature(value)
def signature(value):
    def data(key):
        v=value.get(key);return v.to_dict() if hasattr(v,'to_dict') else v
    t,e,i=data('template'),data('exemplar'),data('insight')
    return [t['template_id'] if t else None,e['exemplar_id'] if e else None,digest(i) if i else None]
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default='..');args=parser.parse_args()
    root=Path(args.root).resolve();repo=root/'output';inp=root/'input-snapshot';res=repo/'results/engineering';art=repo/'artifacts/engineering'
    episodes=records(inp);legacy=publisher(repo,True);updated=publisher(repo)
    known={digest({}):{}}
    for file in inp.glob('*.final_bank.json'):
        value=read(file);known[digest(value)]=value
    m0=read(inp/'M0.json');known[digest(m0)]=m0
    chains={mode:{digest({}):{}} for mode in ('chained_credit_fix','chained_credit_and_age_fix')};event_rows=[];delta_rows=[];summary_rows=[];states={};checks=[];version_mismatches=[]
    for run in RUN_ORDER:
        plan=read(inp/(run+'.plan.json'));initial=known[plan['initial_bank_hash']]
        for arm in plan['arms']:
            key=run+'.'+arm;old=SkillLibrary.from_dict(copy.deepcopy(initial))
            isolated=ScienceSkillLibrary.from_dict(copy.deepcopy(initial));isolated.fix_inactivity_age=False
            libraries={'isolated_credit_fix':isolated}
            for mode,prior in chains.items():
                chain_initial=prior.get(plan['initial_bank_hash']);assert chain_initial is not None,'Missing predecessor: '+key
                lib=ScienceSkillLibrary.from_dict(copy.deepcopy(chain_initial));lib.fix_inactivity_age=mode=='chained_credit_and_age_fix';libraries[mode]=lib
            first_divergence={m:None for m in libraries};event_counts=collections.Counter()
            batches=sorted((inp/'banks').glob(key+'.batch*.json'))
            for file in batches:
                saved=read(file);batch=[episodes[e['job_id']] for e in saved['events']]
                compiled=[read(inp/'compilations'/(r['job_id']+'.json')) if (inp/'compilations'/(r['job_id']+'.json')).exists() else None for r in batch]
                old_input=old.to_dict();assert digest(old_input)==saved['input_hash'],str(file)+' input'
                for r in batch:assert r['bank_hash']==saved['input_hash']
                mismatches={m:{r['job_id']:retrieved_signature(lib,r)!=signature(r['retrieved']) for r in batch} for m,lib in libraries.items()}
                original_events=legacy(old,batch,compiled)
                if old.to_dict()!=saved['library']:
                    if run!='discovery-v1':raise AssertionError(str(file)+' library')
                    version_mismatches.append({'run':run,'bank':str(file.relative_to(inp)),
                        'different_fields':[k for k in saved['library'] if saved['library'][k]!=old.to_dict().get(k)],
                        'scope':'Superseded engineering calibration cannot be replayed by the final frozen publisher; no corrected-state claim for these 16 episodes.'})
                    break
                original_events=json.loads(json.dumps(original_events))
                if original_events!=saved['events']:
                    differences=[{'job_id':a['job_id'],'fields':{k:[a.get(k),b.get(k)] for k in set(a)|set(b) if a.get(k)!=b.get(k)}} for a,b in zip(original_events,saved['events']) if a!=b]
                    raise AssertionError(str(file)+' events '+json.dumps(differences))
                checks.append(str(file.relative_to(inp)))
                for mode,lib in libraries.items():
                    fixed_events=updated(lib,batch,compiled)
                    for r,compiled_record,previous,current in zip(batch,compiled,original_events,fixed_events):
                        mismatch=mismatches[mode][r['job_id']]
                        if mismatch and first_divergence[mode] is None:first_divergence[mode]=r['job_id']
                        change=previous['admitted']!=current['admitted']
                        event_counts[mode+':admission_changes']+=change
                        event_counts[mode+':retrieval_mismatches']+=mismatch
                        old_status=previous['status_after'];new_status=current['status_after']
                        changed_status={tid:[old_status.get(tid,'ABSENT'),new_status.get(tid,'ABSENT')] for tid in set(old_status)|set(new_status) if old_status.get(tid)!=new_status.get(tid)}
                        event_rows.append({'run':run,'arm':arm,'mode':mode,'job_id':r['job_id'],'task':r['spec']['task_name'],
                          'split':r['spec']['split'],'candidate_template_id':((compiled_record or {}).get('template') or {}).get('template_id'),'original_admitted':previous['admitted'],'recomputed_admitted':current['admitted'],
                          'admission_changed':change,'status_changes':json.dumps(changed_status,sort_keys=True),
                          'retrieval_incompatible_with_saved_trace':mismatch,'first_retrieval_divergence':first_divergence[mode],
                          'original_audit':json.dumps(previous['audit'],sort_keys=True),'recomputed_audit':json.dumps(current['audit'],sort_keys=True),
                          **current['credit'],'scope':'Frozen observations and candidates; not an online policy counterfactual'})
            if run=='discovery-v1' and version_mismatches:continue
            original=old.to_dict()
            final_path=inp/(key+'.final_bank.json')
            if final_path.exists():assert original==read(final_path),key+' final'
            states[key]={'original':original,**{mode:lib.to_dict() for mode,lib in libraries.items()}}
            for mode in chains:chains[mode][digest(original)]=libraries[mode].to_dict()
            for mode,lib in libraries.items():
                fixed=lib.to_dict();changed=0
                for tid in sorted(set(original['templates'])|set(fixed['templates'])):
                    values={}
                    for field in ('template_utility','template_status','template_use_count','template_success_count','template_failure_count','template_last_used'):
                        values['original_'+field]=original[field].get(tid)
                        values['recomputed_'+field]=fixed[field].get(tid)
                    differs=any(original[f].get(tid)!=fixed[f].get(tid) for f in ('template_utility','template_status','template_use_count','template_last_used'))
                    changed+=differs
                    template=original['templates'].get(tid) or fixed['templates'][tid]
                    delta_rows.append({'run':run,'arm':arm,'mode':mode,'template_id':tid,'task':template['task_type'],'changed':differs,**values})
                summary_rows.append({'run':run,'arm':arm,'mode':mode,'recorded_publications':sum(len(read(f)['events']) for f in batches),
                    'templates_changed':changed,'admission_changes':event_counts[mode+':admission_changes'],
                    'retrieval_mismatches':event_counts[mode+':retrieval_mismatches'],'first_divergence':first_divergence[mode],
                    'original_injection_suppressed':original['injection_suppressed'],'recomputed_injection_suppressed':fixed['injection_suppressed']})
    csv_write(res/'governance_events.csv',event_rows);csv_write(res/'governance_template_deltas.csv',delta_rows);csv_write(res/'governance_summary.csv',summary_rows)
    write(art/'governance_states.json',states)
    write(art/'governance_receipt.json',{'status':'PASSED_WITH_EXPLICIT_VERSION_EXCLUSION','reference_batches_reproduced_exactly':checks,'version_mismatches':version_mismatches,'original_outcomes_modified':False,'models_called':0,'new_task_success_rates_reported':False,'summary':summary_rows})
    print(json.dumps({'reference_batches':len(checks),'publication_events_per_mode':len(event_rows)//3,'run_arms':len(states),'delta_rows':len(delta_rows),'new_model_calls':0}))
if __name__=='__main__':main()
