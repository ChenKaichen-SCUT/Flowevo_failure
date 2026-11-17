"""Observed exposure and execution accounting, not causal outcome attribution.

Zero-action attempts never update L1 utility. A partly executed template that
needs fallback is an incomplete direct attempt, even if fallback later succeeds.
Native admission/audit thresholds and all three retrieval layers are retained.
"""
import copy,json
from alfworld_.skill_library import SkillLibrary
from alfworld_.schemas import AlfWorldInsight
from .skill_contracts import ScienceSkillTemplate

class ScienceSkillLibrary(SkillLibrary):
    def __init__(self,governance_enabled=True,fix_inactivity_age=True):
        super().__init__(governance_enabled)
        self.credit_ledger={'schema_version':1,'retrieval':{},'direct':{},'guidance':{},'holdout':{}}
        self.template_admitted_at={};self.fix_inactivity_age=fix_inactivity_age

    def to_dict(self):
        data=super().to_dict();data['credit_ledger']=copy.deepcopy(self.credit_ledger)
        data['governance_metadata']={'template_admitted_at':dict(self.template_admitted_at),'fix_inactivity_age':self.fix_inactivity_age}
        return data

    @classmethod
    def from_dict(cls,data):
        lib=cls();base=SkillLibrary.from_dict(data);lib.__dict__.update(base.__dict__)
        lib._templates={tid:ScienceSkillTemplate.from_dict(value) for tid,value in data.get('templates',{}).items()}
        lib.credit_ledger=copy.deepcopy(data.get('credit_ledger',lib.credit_ledger))
        metadata=data.get('governance_metadata',{})
        lib.template_admitted_at=dict(metadata.get('template_admitted_at',{}))
        lib.fix_inactivity_age=metadata.get('fix_inactivity_age',True)
        return lib

    def add_template(self,template):
        admitted=super().add_template(template)
        if admitted:self.template_admitted_at[template.template_id]=self._current_episode
        return admitted

    def load(self,path):
        # The upstream loader hardcodes SkillLibrary.from_dict and would
        # discard applicability, roles and the new accounting on disk reload.
        if not path.exists():return
        loaded=type(self).from_dict(json.loads(path.read_text(encoding='utf-8')))
        self.__dict__.update(loaded.__dict__)

    def periodic_audit(self):
        # Inactivity starts at admission until the FIRST real direct use. Keep
        # the public last-used field honest; never count creation as execution.
        temporary=[]
        if self.fix_inactivity_age:
            for tid in self._templates:
                if tid not in self._template_last_used and tid in self.template_admitted_at:
                    self._template_last_used[tid]=self.template_admitted_at[tid];temporary.append(tid)
        try:return super().periodic_audit()
        finally:
            for tid in temporary:self._template_last_used.pop(tid,None)

    def record_episode_credits(self,result):
        steps=result.get('steps',[]);retrieved=result.get('retrieved',{});trace=result['trace']
        direct=[step for step in steps if step['source']=='direct_skill']
        guided=[step for step in steps if step['source']=='skill_guided']
        dynamic=[step for step in steps if step['source']=='dynamic']
        template=retrieved.get('template');tid=template['template_id'] if template else None
        exemplar=retrieved.get('exemplar');insight=retrieved.get('insight')
        # Inherited run() composes L2 examples AND L3 directives. They are
        # co-exposures, not separately identified causal contributions.
        insight_injected=bool(insight and AlfWorldInsight.from_dict(insight).to_prompt_text())
        gids=(['exemplar:'+exemplar['exemplar_id']] if exemplar else [])+(['insight:'+trace['task_type']] if insight_injected else [])
        event={'template_id':tid,'guidance_id':';'.join(gids),'direct_actions':len(direct),'guided_actions':len(guided),
               'dynamic_actions':len(dynamic),'direct_attempt_entered':bool(trace.get('direct_use_count')),
               'direct_credit_updated':False,'direct_completed':False,'guidance_credit_updated':False,
               'mixed_direct_guidance':bool(direct and guided),'guidance_identity_missing':bool(guided and not gids),'historical_template_present':tid in self._templates if tid else None}
        def exposure(key,used):
            stats=self.credit_ledger['retrieval'].setdefault(key,{'retrieved':0,'retrieved_only':0})
            stats['retrieved']+=1;stats['retrieved_only']+=int(not used)
        if tid:exposure('template:'+tid,bool(direct))
        if exemplar:exposure('exemplar:'+exemplar['exemplar_id'],bool(guided))
        if insight:exposure('insight:'+trace['task_type'],bool(guided and insight_injected))
        if direct and tid:
            # Use the outcome AT the last direct action, never the eventual episode outcome.
            completed=direct[-1].get('host_outcome',{}).get('success') is True
            stats=self.credit_ledger['direct'].setdefault(tid,{'attempts_with_actions':0,'completed_directly':0,'incomplete_direct_attempts':0,'executed_actions':0})
            stats['attempts_with_actions']+=1;stats['completed_directly']+=int(completed)
            stats['incomplete_direct_attempts']+=int(not completed);stats['executed_actions']+=len(direct)
            self.record_template_usage(tid,completed)
            event.update(direct_credit_updated=tid in self._templates,direct_completed=completed)
        if guided and gids:
            for gid in gids:
                stats=self.credit_ledger['guidance'].setdefault(gid,{'episodes_exposed':0,'associated_episode_successes':0,'guided_actions':0,'mixed_direct_prefix_episodes':0,'coexposed_guidance_episodes':0})
                stats['episodes_exposed']+=1;stats['associated_episode_successes']+=int(trace['success'])
                stats['guided_actions']+=len(guided);stats['mixed_direct_prefix_episodes']+=int(bool(direct))
                stats['coexposed_guidance_episodes']+=int(len(gids)>1)
            self.record_guided(trace['task_type'],trace['success']);event['guidance_credit_updated']=True
        # A holdout with a direct prefix is not a pure unguided comparison.
        if trace.get('strategy_holdout') and dynamic and not direct and not guided:
            stats=self.credit_ledger['holdout'].setdefault(trace['task_type'],{'episodes':0,'associated_episode_successes':0})
            stats['episodes']+=1;stats['associated_episode_successes']+=int(trace['success'])
            self.record_unguided(trace['task_type'],trace['success'])
        return event
