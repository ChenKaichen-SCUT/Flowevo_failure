import argparse,json,subprocess,hashlib,shutil
from pathlib import Path
from flowevo_sw.batch_runner import run_batches
from flowevo_sw.checkpointing import read_json,atomic_json,digest
from flowevo_sw.config import load_config

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--bank',required=True);p.add_argument('--validation',required=True);p.add_argument('--workers',type=int,default=8);p.add_argument('--test-per-type',type=int,default=6);a=p.parse_args();root=Path(a.root).resolve();config=load_config(root);validation=read_json(a.validation)
    if validation.get('status')!='VALIDATED' or not validation.get('rules',{}).get('F-I'):
        atomic_json(root/'output/artifacts/main_status.json',{'status':'NO_VALIDATED_CANDIDATE','test_opened':False,'reason':'No rules met preregistered DEV admission. No F-I efficacy claims.'});print('NO_VALIDATED_CANDIDATE');return
    rules=validation['rules']
    for arm,rs in rules.items():
        if arm!='F-T':assert len(rs)<=3
        assert all(r['validation_status']=='VALIDATED' for r in rs)
    selected=read_json(root/'output/artifacts/task_selection.json')['selected_task_types'];bank=read_json(a.bank);protocol_path=root/'output/artifacts/protocol.json'
    # Open only frozen metadata, not task observations; select every arm identically.
    allrows=[json.loads(l) for l in (root/'data/manifests/test_manifest.private.jsonl').read_text().splitlines()]
    chosen=[]
    for name in selected:chosen+=sorted([r for r in allrows if r['task_name']==name],key=lambda r:r['sort_key'])[:a.test_per_type]
    source_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root/'output',text=True).strip()
    protocol={'source_commit':source_sha,'config':config,'environment':read_json(root/'output/artifacts/environment_manifest.json'),'upstreams':read_json(root/'output/artifacts/upstream_manifest.json'),'rules':rules,'M0_hash':digest(bank),'selected_task_ids':[r['episode_id'] for r in chosen],'order_seeds':[17,29],'arms':['F','F-I','F-T','F-S','F-H'],'analysis':'Primary F-I minus F completion. Repeated-order averaging per task/variation, family hierarchical bootstrap, family/order results. Secondary comparisons descriptive; no best-order selection. Final score is official raw final, not highest.','batch_size':8,'success_learning':'online_batch_barrier','failure_learning':'frozen','test_exposure':'Only completed TEST trajectories may be exported and then count as exposed.'}
    protocol['protocol_sha256']=digest(protocol)
    if protocol_path.exists() and read_json(protocol_path)!=protocol:raise RuntimeError('Frozen TEST protocol conflict')
    atomic_json(protocol_path,protocol);atomic_json(root/'runs-private/M0.json',bank)
    for seed in (17,29):
        sequence=sorted(chosen,key=lambda r:digest([seed,r['episode_id']]))
        run_batches(sequence,root/'runs-private',f'main-order-{seed}-v1',bank=bank,arms=protocol['arms'],rules=rules,workers=a.workers)
    atomic_json(root/'output/artifacts/main_status.json',{'status':'RUNS_FINISHED_CHECK_COMPLETENESS','protocol_sha256':protocol['protocol_sha256']})
if __name__=='__main__':main()
