"""DeepSeek proposes hypotheses from autonomous PUBLIC TRAIN records only."""
from .flowevo_adapter import public_episode
from .deepseek_client import DeepSeekClient
from .checkpointing import digest

DIAGNOSE='''Analyze autonomous ScienceWorld public trajectories. You have NO expert solution, hidden score, internal object tree or subgoal progress. Distinguish ENGINEERING (interface or delivery), STATE_CANDIDATE (publicly evidenced precondition, stale state, object confusion, destructive phase transition), KNOWLEDGE_OR_PLANNING, and UNDETERMINED. Failure alone does not establish a state mechanism. Repeated waiting may be necessary. Find at most TWO mechanisms each supported by exact steps from TWO DIFFERENT episodes; otherwise return no mechanisms. Do not manufacture evidence. Output {"diagnoses":[{"episode_id":"...","category":"...","reason":"...","evidence_steps":[1]}],"mechanisms":[{"name":"...","description":"...","source_evidence":[{"episode_id":"...","bad_step":1,"public_failure_quote":"verbatim feedback","state_issue":"..."}],"testable_public_property":"...","negative_control":"when this action is useful","requires_more_information":false}]}. bad_step is 1-based host action index. Propose a mechanism only if locally testable by <=8 actions, not a full task-specific solver.'''

def compact_public(result):
    prev={};steps=[]
    for s in result['steps']:
        row={'step':s['step'],'action':s['executed_action'],'feedback':s['after']['observation']}
        for k in ('look','inventory'):
            if s['after'][k]!=prev.get(k):row[k]=s['after'][k]
        prev=s['after'];steps.append(row)
    return {'episode_id':result['job_id'],'goal':result['initial']['goal'],'initial_look':result['initial']['look'],'initial_inventory':result['initial']['inventory'],'steps':steps}

def diagnose_group(name,results,run_id):
    client=DeepSeekClient(run_id+'.diagnose.'+digest(name)[:12],meta={'stage':'failure_diagnosis','split':'train'})
    obj,raw,rid,usage=client.json(DIAGNOSE,{'episodes':[compact_public(r) for r in results]},learning=True)
    byid={r['job_id']:r for r in results};verified=[]
    for mechanism in obj.get('mechanisms',[]):
        refs=mechanism.get('source_evidence',[]);valid=[]
        for ref in refs:
            r=byid.get(ref.get('episode_id'));i=ref.get('bad_step')
            if r and isinstance(i,int) and 1<=i<=len(r['steps']):
                quote=ref.get('public_failure_quote','')
                if quote and quote in r['steps'][i-1]['after']['observation']:valid.append(ref)
        mechanism['verified_quote_references']=valid
        mechanism['two_variations_supported']=len({byid[x['episode_id']]['spec']['variation_id'] for x in valid})>=2
        mechanism['mechanism_id']='mechanism_'+digest([name,mechanism.get('name')])[:12]
        verified.append(mechanism)
    return {'task_name':name,'raw':raw,'request_id':rid,'usage':usage,'diagnoses':obj.get('diagnoses',[]),'mechanisms':verified,'interpretation':'DeepSeek hypotheses; quote checks verify provenance only, not causal truth.'}

RULE_PROMPT='''Infer a transferable public-state action constraint from the supplied real local contrastive executions. Do not encode task IDs, variation IDs, source object instance IDs, hidden scores, or a full solution plan. Use a declarative trigger with one operator per node: {"all":[...]}, {"any":[...]}, {"not":...}, {"eq":[field,value]}, {"contains":[field,string]}, {"starts_with":[field,string]}. Allowed fields: action,last_action,last_feedback,look,inventory,goal,same_action,same_visible_state. Unknown values must ABSTAIN. A true trigger means VETO. Output {"rule": {"rule_id":"...","version":1,"source_evidence_ids":[],"scope":"...","public_state_requirements":[],"trigger":{},"protected_property":"...","invalidation":"...","exceptions":[],"on_unknown":"ABSTAIN","counterexamples":[],"validation_status":"CANDIDATE"},"reason":"..."}, or {"rule":null,"reason":"insufficient evidence"}. Preserve legitimate waiting, reversal and new object instances. Avoid blanket vetoes.'''
