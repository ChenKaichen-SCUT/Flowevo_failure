"""Allowlist boundary. Private host outcome fields never enter these dictionaries."""
def public_view(observation,info):
    return {'observation':str(observation),'look':str(info.get('look','')),'inventory':str(info.get('inv','')),'goal':str(info.get('taskDesc','')),'valid_actions':list(info.get('valid',[]))}

def parse_action(raw,finish_reason='stop'):
    import json
    from .deepseek_client import ParseError,DeliveryError
    if finish_reason!='stop':raise DeliveryError('DELIVERY_TRUNCATED')
    try:
        d=json.loads(raw);action=d['action']
        if not isinstance(action,str) or not action.strip() or '\n' in action or len(action)>512:raise ValueError()
    except (ValueError,KeyError,TypeError):raise ParseError('ACTION_PARSE_ERROR')
    return action.strip()
