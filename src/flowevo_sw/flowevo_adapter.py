"""Retain upstream three-layer routing, memory, instantiation and governance.

ALFWorld-only physics/templates/parser/exploration are replaced at explicit
environment extension points, not transplanted as ScienceWorld solutions.
"""
import json,re
from dataclasses import asdict
from types import SimpleNamespace
from alfworld_.executor import AlfWorldExecutor
from alfworld_.compiler import AlfWorldCompiler
from alfworld_.schemas import AlfWorldAction,AlfWorldTask,AlfWorldSkillTemplate,AlfWorldExemplar
from alfworld_.skill_library import SkillLibrary
from .public_view import parse_action
from .deepseek_client import ParseError,DeliveryError
from .action_gateway import Veto
from .checkpointing import digest

ACTION_SYSTEM='''You are operating ScienceWorld, an interactive scientific environment. Complete the given goal using only public observations and normal action feedback. Choose exactly ONE action. The valid-action list is an interface aid, NOT a list of task-correct actions; other syntactically supported commands and numeric ambiguity choices can be used when the environment requests them. Observe scientific processes over time as needed. Use the recent feedback and current look/inventory; old observations may be stale. Return JSON {"action":"one exact environment command","reason":"next subgoal in at most 60 words"}. No fabricated observations. Do not emit an extended internal debate.'''

class ScienceGenerator:
    def __init__(self,client,adapter):self.client=client;self.adapter=adapter;self.last=None
    def step(self,task_goal,observation,admissible_commands,action_history=None,observation_history=None,skill_context='',policy_directives=None,correction=None):
        context=self.adapter.context()
        ordered={k:context[k] for k in ('goal','valid_actions','look','inventory')}
        ordered.update({k:v for k,v in context.items() if k not in ordered})
        data={'public':ordered,'successful_skill_guidance':skill_context,'native_policy_directives':policy_directives or []}
        if correction:data['interface_or_constraint_feedback']=correction
        raw,rid,usage=self.client.call(ACTION_SYSTEM,json.dumps(data,ensure_ascii=False))
        try:action=parse_action(raw)
        except ParseError:self.client.parsed(rid,'ACTION_PARSE_ERROR');raise
        self.client.parsed(rid,'VALID_ACTION_FORMAT')
        self.last=dict(raw=raw,request_id=rid)
        return SimpleNamespace(action=action,prompt_tokens=usage.get('prompt_tokens',0),completion_tokens=usage.get('completion_tokens',0))

class ScienceExecutor(AlfWorldExecutor):
    """Inherited run() implements L1 -> L2/L3 -> dynamic fallback composition."""
    def _record(self,trace,action,result):
        trace.actions.append(AlfWorldAction(step=len(trace.actions),action=action,observation=result.observation,score=result.score,done=result.done,admissible_commands=result.admissible_commands))
        trace.action_history.append(action)
        if result.won:trace.success=True
    def _execute_direct(self,trace,task,template,bindings,initial_observation,admissible_commands):
        trace.direct_use_count=1;trace.used_skills=[template.template_id];trace.selected_skill_id=template.template_id
        for action in template.instantiate(bindings):
            if self.env.done or len(trace.actions)>=self.max_steps:break
            # A missing currently-valid action is a public applicability failure,
            # not a hidden-score retry. No fuzzy or first-valid substitution.
            if action not in self.env.adapter.view['valid_actions']:
                trace.runtime_skill_block_reason='PUBLIC_ACTION_NOT_CURRENTLY_VALID';break
            try:result=self.env.step(action,source='direct_skill')
            except Veto:trace.runtime_skill_block_reason='CONSTRAINT_VETO';break
            self._record(trace,action,result)
            if result.won:trace.direct_success_count=1;return
            if result.done:break
        trace.direct_failure_count=1;trace.fallback_triggered=not self.env.done
    def _execute_step_by_step(self,trace,task,initial_observation,admissible_commands,skill_context='',policy_directives=None):
        if self.env.done:return
        trace.skill_seeded=bool(skill_context or policy_directives);trace.seeded_use_count=int(trace.skill_seeded)
        while len(trace.actions)<self.max_steps and not self.env.done:
            correction=None;out=None
            for attempt in range(2):
                try:
                    out=self.generator.step(task.goal,self.env.adapter.view['observation'],self.env.adapter.view['valid_actions'],skill_context=skill_context,policy_directives=policy_directives,correction=correction)
                    trace.llm_call_count+=1;trace.llm_prompt_tokens_total+=out.prompt_tokens;trace.llm_completion_tokens_total+=out.completion_tokens
                    result=self.env.step(out.action,source='skill_guided' if trace.skill_seeded else 'dynamic',replanned=attempt>0,**self.generator.last)
                    self._record(trace,out.action,result);break
                except ParseError:
                    correction='Invalid JSON action interface. Return exactly one JSON object containing a nonempty single-line action string.'
                    if attempt:trace.failure_type='ACTION_PARSE_ERROR';return
                except Veto as exc:
                    correction='Public-state rule rejected the proposed action. Replan once using the SAME remaining episode budget: '+str(exc)
                    if attempt:trace.failure_type='PERSISTENT_CONSTRAINT_CONFLICT';return
                except DeliveryError as exc:trace.failure_type=str(exc);return
            if trace.success:return
        trace.llm_total_tokens_total=trace.llm_prompt_tokens_total+trace.llm_completion_tokens_total

COMPILE_PROMPT='''Compile ONLY this autonomous successful public execution into a reusable ScienceWorld skill. Do not use expert paths or fill in an ideal solution from outside the trace. Output {"action_template":["command with {parameter}"],"parameters":["parameter"],"example_bindings":{"parameter":"source value"},"rules":["3-5 abstract procedural rules"],"applicability":"public conditions"}. Instantiating example_bindings must reproduce an ordered subsequence of actually executed successful-episode actions. Keep necessary observation/wait steps. Parameterize variable objects/materials/locations only when supported. No task/variation IDs in conditions.'''

class ScienceCompiler(AlfWorldCompiler):
    def __init__(self,client,public_episode):
        super().__init__(client);self.public_episode=public_episode;self.generated=None;self.rejection=None
    def _generate(self,trace):
        if self.generated is None:
            self.generated,_,_,_=self.llm_client.json(COMPILE_PROMPT,self.public_episode,stage='success_compile',learning=True)
        return self.generated
    def _compile_template(self,trace):
        d=self._generate(trace)
        try:
            actions=d['action_template'];params=d['parameters'];bindings=d['example_bindings']
            if not isinstance(actions,list) or not actions or len(actions)>100:raise ValueError('invalid template length')
            if any(not isinstance(a,str) for a in actions):raise ValueError('invalid action')
            if set(re.findall(r'\{(\w+)\}',' '.join(actions)))!=set(params):raise ValueError('parameter mismatch')
            if any(not isinstance(bindings.get(p),str) for p in params):raise ValueError('invalid binding')
            template=AlfWorldSkillTemplate('sw_'+digest(d)[:16],trace.task_type,actions,params,bindings,trace.task_id,trace.trace_id,1)
            it=iter(trace.action_history)
            if not all(any(actual==candidate for actual in it) for candidate in template.instantiate(bindings)):raise ValueError('not an observed action subsequence')
            return template
        except (ValueError,KeyError,TypeError) as exc:self.rejection=str(exc);return None
    def _compile_guideline(self,trace):
        d=self._generate(trace);rules=d.get('rules',[])
        if not isinstance(rules,list) or not rules or any(not isinstance(x,str) for x in rules):return None
        return AlfWorldExemplar('swguide_'+digest(rules)[:16],trace.task_type,trace.goal,rules[:5],trace.task_id,trace.trace_id)

def bind_skill(client,template,view):
    d,raw,rid,_=client.json('Decide applicability and bind this previously learned skill using ONLY the current goal and public observations. Do not assume hidden object locations or reuse source values automatically. Return {"applicable":true|false,"bindings":{},"reason":"public evidence for every binding"}. All parameters must bind; otherwise set applicable=false. Do not modify the action template.',{'template':template.to_dict(),'public':view},stage='binding')
    bindings=d.get('bindings',{})
    valid=d.get('applicable') is True and isinstance(bindings,dict) and all(isinstance(bindings.get(p),str) and bindings[p] for p in template.parameters)
    return (bindings if valid else None),{'raw':raw,'request_id':rid,'parsed':d,'accepted':valid}

def public_episode(result):
    return {'goal':result['initial']['goal'],'initial':result['initial'],'steps':[{'action':s['executed_action'],'feedback':s['after']['observation'],'look':s['after']['look'],'inventory':s['after']['inventory']} for s in result['steps']]}
