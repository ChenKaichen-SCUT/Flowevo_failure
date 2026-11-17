FIELDS={'action','last_action','last_feedback','look','inventory','goal','same_action','same_visible_state','action_verb','action_target','target_door_state','target_container_state'}

def validate_expr(expr,depth=0):
    if depth>8 or not isinstance(expr,dict) or len(expr)!=1:raise ValueError('Invalid declarative expression')
    op,value=next(iter(expr.items()))
    if op in ('all','any'):
        if not isinstance(value,list) or not 1<=len(value)<=10:raise ValueError('Invalid arity')
        for child in value:validate_expr(child,depth+1)
    elif op=='not':validate_expr(value,depth+1)
    elif op in ('eq','contains','starts_with'):
        if not isinstance(value,list) or len(value)!=2 or value[0] not in FIELDS or not isinstance(value[1],(str,bool)):raise ValueError('Invalid public predicate')
        if isinstance(value[1],str) and len(value[1])>512:raise ValueError('Predicate too long')
    else:raise ValueError('Unknown operator')

def validate_rule(rule):
    for k in ('rule_id','version','source_evidence_ids','scope','public_state_requirements','trigger','protected_property','invalidation','exceptions','on_unknown','counterexamples','validation_status'):
        if k not in rule:raise ValueError('Missing '+k)
    if rule['on_unknown']!='ABSTAIN':raise ValueError('Unknown must abstain')
    validate_expr(rule['trigger'])
    return rule
