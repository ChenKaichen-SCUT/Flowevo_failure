"""Join frozen source reviews to saved compiler requests, outputs and lifecycle."""
import argparse,collections,csv,json,os,re
from pathlib import Path
from success_audit_prepare import read,write,sha,canonical,verify_frozen

def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def exact_alignment(actions,source):
    position=0;indices=[]
    for action in actions:
        while position<len(source) and source[position]!=action:position+=1
        if position==len(source):return None
        indices.append(position+1);position+=1
    return indices

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    inp=Path(a.input).resolve();out=Path(a.output).resolve();art=out/'artifacts/success_audit'
    assert os.environ.get('FLOWEVO_OFFLINE_ONLY')=='1'
    frozen=read(art/'source_review_freeze.json')
    verify_frozen(out,frozen['files'])
    from flowevo_sw.flowevo_adapter import ScienceCompiler,public_episode
    from flowevo_sw.batch_runner import restore_trace
    from flowevo_sw.conditional_binding import unique_source_alignment
    from flowevo_sw.credit_accounting import ScienceSkillLibrary
    inventory=read(art/'success_inventory.json');reviews={r['job_id']:r for r in read(art/'source_adjudicated.json')}
    episodes={f.stem:read(f) for f in sorted((inp/'episodes').glob('*.json')) if '.prefix.' not in f.name}
    private_hash={r['private_file']:r['private_sha256'] for r in read(out/'results/export_mapping.json')['records']}
    events=collections.defaultdict(list)
    for f in sorted((inp/'banks').glob('*.json')):
        for e in read(f).get('events',[]):events[e['job_id']].append({'bank_ref':'banks/'+f.name,'admitted':e['admitted'],'compiled':e['compiled']})
    lifecycle=collections.defaultdict(lambda:collections.Counter())
    for e in episodes.values():
        split=e['spec']['split'];retrieved=e.get('retrieved',{})
        for layer,key in (('L1','template'),('L2','exemplar')):
            asset=retrieved.get(key)
            if not asset:continue
            jid=asset['source_trace_id'];lifecycle[jid][layer+'_retrieved_'+split]+=1
            used=[s for s in e['steps'] if s['source']==('direct_skill' if layer=='L1' else 'skill_guided')]
            if used:lifecycle[jid][layer+'_actually_used_episodes_'+split]+=1;lifecycle[jid][layer+'_actions_'+split]+=len(used)
    chains=[];source_rows=[];template_summaries=[]
    for ident in inventory:
        jid=ident['job_id'];episode=episodes[jid];cpath=inp/'compilations'/(jid+'.json');saved=read(cpath) if cpath.exists() else None
        row=dict(ident,source_original_sha256=private_hash.get(ident['source_ref']),source_hash_format='UTF-8 public restore file; original server bytes hashed separately',
          process_label=reviews[jid]['label'] if jid in reviews else 'NOT_AUDITED_TEST',
          decision_supported=reviews[jid]['decision_supported'] if jid in reviews else None,
          requires_inference_or_experiment=reviews[jid]['requires_inference_or_experiment'] if jid in reviews else None,
          comparison_required=reviews[jid]['comparison_required'] if jid in reviews else None,
          source_reason_zh=reviews[jid]['reason_zh'] if jid in reviews else '仅历史库存，不用于技能设计、调参或过程标签统计',
          evidence_grade=reviews[jid]['evidence_grade'] if jid in reviews else 'HISTORICAL_METADATA_ONLY',
          measurement_evidence_steps=json.dumps(reviews[jid]['measurement_evidence_steps']) if jid in reviews else '',
          comparison_evidence_steps=json.dumps(reviews[jid]['comparison_evidence_steps']) if jid in reviews else '',
          selection_steps=json.dumps(reviews[jid]['selection_steps']) if jid in reviews else '',
          source_review_ref='artifacts/success_audit/source_adjudicated.json#'+jid if jid in reviews else '',
          compilation_file_present=cpath.exists(),compilation_ref='compilations/'+cpath.name,
          compilation_sha256=sha(cpath.read_bytes()) if cpath.exists() else None,
          historical_source_valid=bool(saved['template']) if saved else None,
          historical_rejection=saved.get('rejection') if saved else 'NO_SAVED_COMPILATION',
          historical_admission_events=json.dumps(events[jid],sort_keys=True),lifecycle=json.dumps(lifecycle[jid],sort_keys=True))
        source_rows.append(row)
        if jid not in reviews:continue
        paths=sorted((inp/'requests').glob(jid+'.compile.*.request.json'));assert len(paths)==1,(jid,paths)
        request_path=paths[0];request=read(request_path);rid=request['request_id'];response_path=request_path.with_name(request_path.name.replace('.request.json','.json'))
        response=read(response_path);text=response['response']['choices'][0]['message']['content'];raw=json.loads(text)
        if saved:assert raw==saved['raw_parsed'],jid
        user=json.loads(request['payload']['messages'][-1]['content']);expected=public_episode(episode)
        assert user==expected,jid+' compiler public input differs'
        compiler=ScienceCompiler(None,user);compiler.generated=raw;compiled=compiler.compile(restore_trace(episode))
        if saved:assert bool(compiled.template)==bool(saved['template']),jid+' source validation changed'
        output=compiled.template.to_dict() if compiled.template else None
        if compiled.template:
            lib=ScienceSkillLibrary();lib.add_template(compiled.template);restored=ScienceSkillLibrary.from_dict(lib.to_dict()).retrieve(compiled.template.task_type)['template']
            assert restored.applicability==raw.get('applicability','')
        actions=raw['action_template'];parameters=raw['parameters'];bindings=raw['example_bindings']
        try:instantiated=[action.format(**bindings) for action in actions]
        except (KeyError,ValueError):instantiated=[]
        alignment=exact_alignment(instantiated,[s['executed_action'] for s in episode['steps']]) if instantiated else None
        loose,count=unique_source_alignment(actions,[s['executed_action'] for s in episode['steps']])
        aliases={}
        if loose:
            values=collections.defaultdict(set)
            for index,pairs in loose:
                for param,value in pairs:values[param].add(value)
            aliases={p:sorted(v) for p,v in values.items() if len(v)>1}
        case={'job_id':jid,'scope':ident['scope'],'task':ident['task'],'split':ident['split'],'unit':ident['unit'],
          'compiler_request_id':rid,'compiler_request_ref':'requests/'+request_path.name,'compiler_request_sha256':sha(request_path.read_bytes()),
          'compiler_request_original_sha256':private_hash.get('requests/'+request_path.name),
          'compiler_response_ref':'requests/'+response_path.name,'compiler_response_sha256':sha(response_path.read_bytes()),
          'compiler_input_equal_to_all_public_steps':True,'compiler_input_steps':len(user['steps']),
          'source_reason_sent_to_compiler':any('reason' in s or 'raw_model_response' in s for s in user['steps']),
          'raw':raw,'historical_compilation_file_present':bool(saved),'historical_template':saved.get('template') if saved else None,
          'historical_exemplar':saved.get('exemplar') if saved else None,
          'current_cached_source_validation':bool(compiled.template),'current_cached_rejection':compiler.rejection,
          'current_cached_template':output,'historical_rejection':saved.get('rejection') if saved else None,
          'raw_rules_equal_historical_L2':raw.get('rules',[])[:5]==saved['exemplar']['rules'] if saved and saved.get('exemplar') else None,
          'original_applicability_in_historical_L1':'applicability' in saved['template'] if saved and saved.get('template') else None,
          'A2_applicability_preserved':output['applicability']==raw.get('applicability','') if output else None,
          'exact_source_alignment_1based':alignment,'loose_source_alignment_count_capped_at_2':count,
          'unique_alignment_multivalue_parameters':aliases,'candidate_admitted_this_audit':False,
          'source_validation_scope':'Revalidate cached output only. No new model output, semantic correctness or complete-goal verification implied.'}
        chains.append(case)
        template_summaries.append('\n## '+jid+'\n'+json.dumps({'raw':raw,'source_validation':case['current_cached_source_validation'],'rejection':compiler.rejection,'source_label':reviews[jid]['label']},ensure_ascii=False,indent=2))
    csv_write(out/'results/success_trace_audit.csv',source_rows)
    write(art/'compilation_chain.json',chains)
    (art/'compilation_packets.txt').write_text('\n'.join(template_summaries)+'\n',encoding='utf-8')
    write(art/'compilation_receipt.json',{'review_freeze_sha256':sha((art/'source_review_freeze.json').read_bytes()),'source_only_records':len(reviews),
       'historical_success_inventory':len(inventory),'cached_compiler_outputs_revalidated':len(chains),
       'saved_compilation_files':sum(c['historical_compilation_file_present'] for c in chains),
       'recovered_responses_without_compilation_file':[c['job_id'] for c in chains if not c['historical_compilation_file_present']],
       'all_compiler_public_inputs_complete':all(c['compiler_input_equal_to_all_public_steps'] for c in chains),
       'source_reasons_not_in_input':sum(not c['source_reason_sent_to_compiler'] for c in chains),
       'current_source_valid':sum(c['current_cached_source_validation'] for c in chains),'new_model_calls':0,'new_candidates_admitted':0})
    print(json.dumps(read(art/'compilation_receipt.json'),ensure_ascii=False))
if __name__=='__main__':main()
