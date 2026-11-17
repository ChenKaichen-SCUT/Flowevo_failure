"""At most two functional revisions; diagnostics consist of real public checks."""
import argparse,json,importlib.util
from pathlib import Path
from flowevo_sw.deepseek_client import DeepSeekClient
from flowevo_sw.checkpointing import read_json,atomic_json
from flowevo_sw.contrastive_learner import RULE_PROMPT
from flowevo_sw.invariant_schema import validate_rule
from flowevo_sw.invariant_runtime import check
from generate_rules import strip_private

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='..');p.add_argument('--revision',type=int,choices=[1,2],required=True);a=p.parse_args();root=Path(a.root).resolve();candidates=read_json(root/'output/artifacts/candidate_rules.json');probes=read_json(root/'runs-private/selected_probes.json');revised=[]
    for old in candidates:
        mid,arm=old['mechanism_id'],old['arm'];rs=[r for r in probes if r['mechanism_id']==mid];path=root/'output/artifacts/rule_versions'/f'rules-v1.{mid}.{arm}.revision{a.revision}.json'
        if path.exists():revised.append(read_json(path));continue
        evidence=[strip_private(r,arm=='F-S') for r in rs];diagnostics=[]
        if old.get('rule'):
            for item in evidence:
                for branch in item['branches']:
                    history=[]
                    for s in branch['steps']:
                        ctx=dict(s['before'],history=history)
                        diagnostics.append({'action':s['action'],'actual_feedback':s['feedback'],'rule_decision':check(old['rule'],ctx,s['action'])['decision'],'public_before':s['before']['public_facts']})
                        history.append({'action':s['action'],'feedback':s['feedback']})
        client=DeepSeekClient(f'rules-v1.{mid}.{arm}.revision{a.revision}',meta={'stage':'constraint_revision','arm':arm,'split':'train'})
        prompt=RULE_PROMPT.replace('real local contrastive executions','successful recovery suffixes only') if arm=='F-S' else RULE_PROMPT
        prompt+=' This is a bounded functional revision. True trigger means VETO (do NOT execute); never veto an action merely because it is the observed successful recovery. A syntactically listed action may still fail in its current state. Additional allowed fields: action_verb, action_target, target_door_state and target_container_state. The latter are parsed from explicit CURRENT look (open/closed) for the exact target, otherwise unknown. No failure history is provided in the success-only arm.'
        # First F-S generation was invalidated as an ENGINEERING evidence-boundary error.
        # Do not forward its failure-contaminated explanation into the repaired F-S input.
        payload={'evidence':evidence,'public_execution_checks':diagnostics}
        if arm=='F-I':payload['previous_candidate']=old.get('rule');payload['previous_reason']=old.get('reason')
        obj,raw,rid,usage=client.json(prompt,payload,stage='rule_revision',learning=True)
        rule=obj.get('rule');error=None
        if rule is not None:
            try:
                validate_rule(rule);rule['rule_id']=f'rules-v1.{mid}.{arm}';rule['version']=a.revision+1;rule['source_evidence_ids']=[r['probe_id'] for r in rs];rule['validation_status']='CANDIDATE'
            except ValueError as exc:error=str(exc);rule=None
        record={'arm':arm,'mechanism_id':mid,'rule':rule,'raw':raw,'request_id':rid,'usage':usage,'schema_error':error,'reason':obj.get('reason'),'generation_index':a.revision+1,'functional_revisions':a.revision,'input_protocol':'compact-public-v2; F-S excludes failed prefixes and failure summaries','diagnostics':diagnostics}
        atomic_json(path,record);revised.append(record)
    atomic_json(root/'output/artifacts/candidate_rules.json',revised);print({'revision':a.revision,'candidates':sum(bool(r['rule']) for r in revised)})
if __name__=='__main__':main()
