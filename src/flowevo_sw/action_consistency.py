"""Version 1: deterministic, public-input, REPORT-ONLY interface diagnostics.

Warnings neither veto nor rewrite an action, and are not sent back as replanning
instructions. NO_FLAG/UNKNOWN never certifies goal correctness. No scores or
post-action observations are inputs to this checker.
"""
import json,re

FOCUS_CONTRACT=('focus on marks a task-relevant object and may advance a subgoal, complete the task, '
                'or terminate it on a wrong choice. It is not a general inspect/measure operation. '
                'The goal may explicitly require focus on an instrument or intermediate object.')
VERBS=('focus on','look at','look in','pick up','go to','activate','deactivate','open','close','wait')
def canonical(text):
    text=re.sub(r'\s+',' ',str(text).lower().strip().strip('`"\'.'))
    return re.sub(r'^(?:the|an|a)\s+','',text)
def parts(action):
    text=action.strip().lower()
    for verb in VERBS:
        if text==verb or text.startswith(verb+' '):return verb,canonical(text[len(verb):])
    return None,None
def explicit_intent(reason):
    # Only a final explicit commitment/correction; quoted goals and if-clauses
    # are not inferred to be the model's next action.
    patterns=[r'(?:correcting|correct action)\s*:\s*([^.!?\n]+)',
              r'\bI(?: will| should| must| need to|\x27ll)\s+([^.!?\n]+)',
              r'(?:^|[.!?]\s+)(?:next|therefore|thus)[:,]?\s*([^.!?\n]+)']
    for pattern_index,pattern in enumerate(patterns):
        matches=list(re.finditer(pattern,reason,re.I))
        if not matches:continue
        tail=matches[-1].group(1)
        if re.search(r',\s*(?:so first|but)\b',tail,re.I):return None
        tail=re.split(r'[.!?;,]|\s+(?:because|per the goal|per instructions|to (?:inspect|identify|locate|measure|find|see|close|search|carry|place|begin|grow|confirm|learn)|so I|before|after|in order to)\b',tail,maxsplit=1,flags=re.I)[0].strip()
        if re.search(r'\b(?:if|unless|or|maybe|might)\b',tail,re.I):return None
        for old,new in [('inspect ','look at '),('examine ','look at '),('travel to ','go to '),('enter ','go to '),('take ','pick up ')]:
            if tail.lower().startswith(old):tail=new+tail[len(old):];break
        verb,target=parts(tail)
        if verb and not re.search(r'\b(?:it|its|them|this|that|one|those|these)\b',target):return {'verb':verb,'target':target,'text':matches[-1].group(0),'normalized':tail,'explicit_correction':pattern_index==0}
    return None

def inspect_response(raw,view):
    result={'version':1,'policy':'REPORT_ONLY','action_unchanged':True,'warnings':[],
            'reason_action_relation':'UNKNOWN','grounding':'NOT_VERIFIED','focus_role':None}
    try:
        data=json.loads(raw);action=data['action'];reason=data.get('reason','')
        if not isinstance(action,str) or not isinstance(reason,str):raise ValueError()
    except (ValueError,TypeError,KeyError):
        result['warnings'].append({'category':'ACTION_FORMAT','level':'OBSERVED_INTERFACE_ERROR','evidence':'Unparseable action/reason fields'})
        return result
    result['parsed_action']=action;verb,target=parts(action);goal=str(view.get('goal','')).lower()
    def warn(category,level,evidence):result['warnings'].append({'category':category,'level':level,'evidence':evidence})
    intention=explicit_intent(reason)
    if intention and verb:
        refs={}
        for command in view.get('valid_actions',[]):
            v,t=parts(command)
            if v:refs.setdefault(v,set()).add(t)
        itarget=intention['target'];atarget=target
        # Door descriptions and navigation aliases are normalized only when
        # the current public door name is explicit.
        doors=re.findall(r'A door to the (.+?) \(that is (?:open|closed)\)',view.get('look',''),re.I)
        if verb in ('open','close','go to'):
            for room in doors:
                if canonical(itarget) in (room+' door','closed '+room+' door','open '+room+' door'):itarget='door to '+room
            if verb=='go to':itarget=itarget.removeprefix('door to ');atarget=atarget.removeprefix('door to ')
        same=intention['verb']==verb and canonical(itarget)==canonical(atarget)
        def grounded(v,t):
            if t in {'animal','plant','thing','object','substance','container','room','door','seed','bee'}:return False
            return t in refs.get(v,set()) or bool(v=='focus on' and t and re.search(r'(?<!\w)'+re.escape(t)+r'(?!\w)',goal))
        if same:
            result['reason_action_relation']='NORMAL_WORDING_VARIANT' if intention['normalized'].lower()!=action.lower() else 'EXPLICIT_AGREEMENT'
        elif verb=='go to' and not intention['explicit_correction']:
            result['reason_action_relation']='POSSIBLE_INTERMEDIATE_ROUTE'
        elif intention['verb']==verb and grounded(verb,itarget) and grounded(verb,atarget) and (' '+itarget+' ') not in (' '+atarget+' ') and (' '+atarget+' ') not in (' '+itarget+' '):
            result['reason_action_relation']='EXPLICIT_CONFLICT'
            warn('REASON_ACTION_CONFLICT','OBSERVED_TEXT_CONTRADICTION',intention['text'])
        elif intention['verb']!=verb and canonical(itarget)==canonical(atarget):
            result['reason_action_relation']='VERB_DIFFERENCE_REQUIRES_REVIEW'
            warn('ACTION_SEMANTICS','PLAUSIBLE_CAUSE',intention['text'])
        else:result['reason_action_relation']='POSSIBLE_ALIAS_OR_QUALIFIER'
    if verb=='focus on':
        result['focus_contract']=FOCUS_CONTRACT
        result['focus_role']='GOAL_COMMITMENT_OR_SUBGOAL_MARKER'
        # These two literal goal classes are precise; no animal/material oracle.
        for kind in ('inclined plane','light bulb'):
            if re.search(r'focus on (?:the |a |an )?(?:[a-z]+ )?'+kind,goal) and kind not in target:
                explicit_other_type=bool(re.search(r'\bcup\b|\bpaint\b|\bbee hive\b|\bpicture\b',target))
                warn('TARGET_OBJECT_MISMATCH' if explicit_other_type else 'TARGET_REFERENCE_AMBIGUOUS',
                     'PUBLIC_GOAL_TYPE_CONTRADICTION' if explicit_other_type else 'ALIAS_OR_WRONG_OBJECT_REQUIRES_REVIEW',{'goal_class':kind,'action_object':target})
                result['grounding']='LITERAL_TYPE_MISMATCH' if explicit_other_type else 'UNKNOWN_ALIAS_OR_OBJECT'
        inspection=re.search(r'focus.{0,90}?\bto (?:inspect|identify|locate|learn|measure|reveal|examine)\b|focus.{0,70}?(?:will|should|may) (?:reveal|show|tell)|(?:inspect|examine).{0,50}\bpropert',reason,re.I)
        if inspection:
            warn('FOCUS_AS_INSPECTION','PLAUSIBLE_ACTION_SEMANTICS_ERROR',inspection.group(0))
        # Explicitly requested focus is never banned or automatically labelled wrong.
        if target and re.search(r'focus on (?:the )?'+re.escape(target)+r'(?:[.,;]|\s|$)',goal):
            result['focus_role']='EXPLICIT_GOAL_FOCUS_CANDIDATE'
    if not result['warnings']:result['diagnostic_status']='NO_FLAG_NOT_A_CORRECTNESS_CERTIFICATE'
    else:result['diagnostic_status']='REVIEW_WARNING'
    return result
