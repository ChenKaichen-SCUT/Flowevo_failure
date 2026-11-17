import argparse,json
from pathlib import Path
from flowevo_sw.batch_runner import run_batches
from flowevo_sw.checkpointing import read_json

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--run-id',default='selected-train-v1');p.add_argument('--discovery-run',default='discovery-v2');p.add_argument('--workers',type=int,default=8);a=p.parse_args();root=Path(a.root).resolve();selection=read_json(root/'output/artifacts/task_selection.json');names=selection['selected_task_types']
    rows=[json.loads(l) for l in (root/'data/manifests/train.jsonl').read_text().splitlines()];by={n:sorted([r for r in rows if r['task_name']==n],key=lambda r:r['sort_key'])[:12] for n in names}
    specs=[by[n][i] for i in range(2,12) for n in names if i<len(by[n])]
    if not specs:raise RuntimeError('NO_SELECTED_TRAIN_TASKS')
    bank=read_json(root/'runs-private'/(a.discovery_run+'.F.final_bank.json'))
    run_batches(specs,root/'runs-private',a.run_id,bank=bank,workers=a.workers)
if __name__=='__main__':main()
