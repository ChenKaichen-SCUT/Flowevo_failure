from .invariant_schema import validate_rule

def evaluate(expr,facts):
    op,value=next(iter(expr.items()))
    if op in ('all','any'):
        vals=[evaluate(c,facts) for c in value]
        if op=='all':return False if False in vals else None if None in vals else True
        return True if True in vals else None if None in vals else False
    if op=='not':
        v=evaluate(value,facts);return None if v is None else not v
    f,want=value
    if f not in facts or facts[f] is None:return None
    got=facts[f]
    if op=='eq':return got==want
    if not isinstance(got,str) or not isinstance(want,str):return None
    if op=='contains':return want.lower() in got.lower()
    if op=='starts_with':return got.lower().startswith(want.lower())
    return None

def check(rule,context,action):
    validate_rule(rule);history=context.get('history',[]);last=history[-1] if history else {}
    facts={k:context.get(k) for k in ('look','inventory','goal')}
    facts.update(action=action,last_action=last.get('action'),last_feedback=last.get('feedback'),same_action=action==last.get('action') if last else None,same_visible_state=context.get('same_visible_state'))
    verdict=evaluate(rule['trigger'],facts)
    return {'decision':'VETO' if verdict is True else 'ALLOW' if verdict is False else 'ABSTAIN','rule_id':rule['rule_id'],'evidence_refs':rule['source_evidence_ids']}
