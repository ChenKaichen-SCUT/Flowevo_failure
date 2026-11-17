import argparse,json
from pathlib import Path
from flowevo_sw.checkpointing import read_json,atomic_json,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--mechanisms',required=True);p.add_argument('--discovery-run',default='discovery-v2');a=p.parse_args();root=Path(a.root).resolve();ms=read_json(a.mechanisms)['mechanisms']
    names=sorted({m['task_name'] for m in ms},key=lambda n:digest([20261117,'selection',n]))[:6]
    all_names=read_json(root/'data/manifests/all_tasks.json')
    controls=sorted(set(all_names)-set(names),key=lambda n:digest([20261117,'control',n]))[:2]
    result={'selected_task_types':names,'out_of_scope_controls':controls,'mechanism_ids':[m['mechanism_id'] for m in ms if m['task_name'] in names],'selection_policy':'Two distinct TRAIN variations with verified public quotes; fixed SHA ordering among eligible families, at most six. Hypotheses are not yet validated. No TEST descriptions/actions/outcomes accessed.','train_target_per_type':12,'dev_target_per_type':4,'test_target_per_type':6,'order_seeds':[17,29]}
    atomic_json(root/'output/artifacts/task_selection.json',result);print(json.dumps(result))
if __name__=='__main__':main()
