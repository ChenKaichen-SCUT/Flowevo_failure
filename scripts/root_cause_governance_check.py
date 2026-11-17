"""Run accounting-only fixtures from frozen publish_batch function bodies.

AST selection avoids importing the environment/client/scheduler module. Functions
are extracted unchanged from the frozen Git blob, not reimplemented or mocked.
"""
import argparse,ast,copy,hashlib,json,subprocess,sys
from pathlib import Path
from root_cause_audit import read,js

BASE='a0f6e0816c23a4abcb646a5fb018e786c2a6be95'
UPSTREAM='36e81efd4d1fdbabca7366200b15808ebef157fa'
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default='..');parser.add_argument('--flowevo-source');args=parser.parse_args()
    root=Path(args.root).resolve();out=root/'output';inp=root/'input-snapshot'
    upstream=Path(args.flowevo_source).resolve() if args.flowevo_source else root/'vendor/FlowEvo'
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True).strip()==UPSTREAM
    assert not subprocess.check_output(['git','diff','HEAD','--','src/alfworld_/skill_library.py','src/alfworld_/schemas.py'],cwd=upstream).strip()
    sys.path.insert(0,str(upstream/'src'))
    from alfworld_.schemas import AlfWorldTrace,AlfWorldAction
    from alfworld_.skill_library import SkillLibrary
    source=subprocess.check_output(['git','show',BASE+':src/flowevo_sw/batch_runner.py'],cwd=out)
    tree=ast.parse(source)
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('restore_trace','publish_batch')]
    assert len(functions)==2
    def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    namespace={'copy':copy,'digest':digest,'AlfWorldTrace':AlfWorldTrace,'AlfWorldAction':AlfWorldAction}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'<frozen accounting functions>','exec'),namespace)
    publish_batch=namespace['publish_batch'];m0=read(inp/'M0.json');fixtures=[]
    for file in sorted((inp/'episodes').glob('main-order-17-v1.F.*.json')):
        if '.prefix.' in file.name:continue
        record=read(file);template=record['retrieved'].get('template')
        if not template or record['trace']['direct_use_count']:continue
        original=SkillLibrary.from_dict(copy.deepcopy(m0));guarded=SkillLibrary.from_dict(copy.deepcopy(m0))
        before=original.to_dict();method=guarded.record_template_usage
        guarded.record_template_usage=lambda tid,success:method(tid,success) if record['trace']['direct_use_count'] else None
        publish_batch(original,[record],[None]);publish_batch(guarded,[record],[None]);tid=template['template_id'];b=original.to_dict();g=guarded.to_dict()
        assert b['template_use_count'][tid]==before['template_use_count'][tid]+1
        assert g['template_use_count'][tid]==before['template_use_count'][tid]
        fixtures.append({'job_id':record['job_id'],'template_id':tid,'actual_direct_actions':0,'original_count_before':before['template_use_count'][tid],'original_count_after':b['template_use_count'][tid],'guarded_count_after':g['template_use_count'][tid],'original_utility_after':b['template_utility'][tid],'guarded_utility_after':g['template_utility'][tid],'classification':'LOCAL_COUNTERFACTUAL_SUPPORTED_ACCOUNTING_ONLY','scope':'Same M0 for each fixture, no compilation/model/environment changes, not a replay of online policy outcomes.'})
    assert len(fixtures)==6
    (out/'artifacts/root_cause_governance_fixtures.json').write_text(js(fixtures),encoding='utf-8')
    receipt={'status':'PASSED','fixtures':len(fixtures),'frozen_commit':BASE,'upstream_commit':UPSTREAM,'batch_runner_blob_sha256':hashlib.sha256(source).hexdigest(),'execution':'Unmodified frozen restore_trace/publish_batch AST functions and pinned real SkillLibrary','new_api_calls':0,'new_api_cost_cny':0,'model_client_imported':False}
    (out/'artifacts/root_cause_governance_reproduction.json').write_text(js(receipt),encoding='utf-8');print(js(receipt))

if __name__=='__main__':main()
