"""Freeze both source-only reviews and the explicit recorded adjudication."""
import argparse,collections,datetime
from pathlib import Path
from success_audit_prepare import read,write,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output).resolve();art=out/'artifacts/success_audit'
    ra=read(art/'review_a.json');rb=read(art/'review_b.json');aidx={r['job_id']:r for r in ra};bidx={r['job_id']:r for r in rb}
    manifest=read(art/'source_manifest.json');assert set(aidx)==set(bidx)=={p['job_id'] for p in manifest['packets']}
    final=[];disagreements=[]
    for jid,r in sorted(aidx.items()):
        s=bidx[jid];packet=read(art/'source_packets'/(jid+'.json'))
        for review in (r,s):
            for key in ('measurement_evidence_steps','comparison_evidence_steps','selection_steps','selection_step','critical_steps'):
                assert all(1<=n<=len(packet['steps']) for n in review.get(key,[])),(jid,key)
        record=dict(r,reviewer='adjudicated_assistant_review',review_a_label=r['label'],review_b_label=s['label'])
        if r['label']!=s['label']:
            assert jid=='discovery-v2.F.3fbe681bf784f2d76d21'
            record['label']='PARTIALLY_SUPPORTED'
            record['reason_zh']='确有第5步当前温度10°C读数，但没有熔化过程或熔点测量。第6步等值不能推出above分支。保留部分操作证据，最终分支依据仍不成立。'
            disagreements.append({'job_id':jid,'review_a':r['label'],'review_b':s['label'],'final':record['label'],
               'resolution_zh':'采纳较保守的部分支持：已有一次相关测量，尚未测到所需物理量；两位审阅者均判最终选择缺充分依据。'})
        record['selection_steps']=r['selection_steps'];record['observed_decision_dependency']=jid=='discovery-v2.F.2beaa66b5bcd3db3dc64'
        record['decision_basis']='OBSERVED_MEASUREMENT_THRESHOLD' if record['observed_decision_dependency'] else 'OBSERVED_STATE_CHANGE' if r['label']=='PROCESS_SUPPORTED' else 'PUBLIC_IDENTITY_AND_ACTION_FEEDBACK' if r['label']=='PROCESS_NOT_REQUIRED' else 'PUBLIC_EVIDENCE_INCOMPLETE'
        if packet['identity']['task'].startswith('lifespan'):
            record['decision_basis']='SPECIES_IDENTITY_WITH_UNVERIFIED_PRIOR_OR_FOCUS_AS_INSPECTION'
        final.append(record)
    write(art/'source_adjudicated.json',final)
    write(art/'review_disagreements.json',{'source_only_records':len(final),'label_agreement_count':len(final)-len(disagreements),
      'disagreements':disagreements,'measurement_vs_comparison_index_note':'温度例B标9为比较证据来源，A标10/14为运用比较的reason；裁定保留9为测量、10/14为应用关系，非标签分歧。',
      'reviewer_limit':'Two assistant review passes, not two humans or a measured independent annotation accuracy. Parent had prior project context; second pass read source packets only.'})
    names=['configs/success_trace_audit.json']+['artifacts/success_audit/'+n for n in ('source_manifest.json','review_a.json','review_b.json','source_adjudicated.json','review_disagreements.json')]
    freeze={'stage':'SOURCE_REVIEW_FROZEN_BEFORE_COMPILATION_JOIN','files':{n:sha((out/n).read_bytes()) for n in names},
      'new_provider_calls':0,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    path=art/'source_review_freeze.json';assert not path.exists(),'Do not silently overwrite frozen reviews'
    write(path,freeze);print('Frozen 39 source reviews; 38 initial label agreements and one explicit adjudication')
if __name__=='__main__':main()
