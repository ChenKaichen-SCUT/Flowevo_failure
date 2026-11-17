from .invariant_runtime import check
from .checkpointing import digest

class Veto(RuntimeError):pass

class ActionGateway:
    def __init__(self,adapter,client=None,arm='F',rules=None):
        self.adapter=adapter;self.client=client;self.arm=arm;self.rules=rules or []
        self.steps=[];self.checks=[];self.last_before=None;self.reviewed_checkpoint=None
    @property
    def done(self):return self.adapter.done
    def step(self,action,source='dynamic',raw=None,request_id=None,replanned=False):
        context=self.adapter.context()
        current=digest([context['look'],context['inventory']])
        context['same_visible_state']=current==self.last_before if self.last_before else None
        verdicts=[]
        if self.arm in ('F-I','F-S','F-H'):
            verdicts=[check(r,context,action) for r in self.rules]
        elif self.arm=='F-T' and self.rules and not replanned:
            review,_,rid,_=self.client.json('Review the proposed action using these learned rules and PUBLIC state. Return {"decision":"ALLOW|VETO|ABSTAIN","reason":"brief"}. Unknown state must ABSTAIN. Do not invent unseen facts.',{'context':context,'action':action,'rules':self.rules},stage='text_review')
            verdicts=[dict(review,request_id=rid,rule_id='text_review')]
        self.checks.append({'checkpoint':self.adapter.decisions,'action':action,'source':source,'verdicts':verdicts,'replanned':replanned})
        if any(v.get('decision')=='VETO' for v in verdicts):
            if not replanned:raise Veto(str(verdicts))
            raise Veto('PERSISTENT_CONFLICT')
        before=self.adapter.view.copy();receipt=self.adapter.execute(action)
        self.last_before=current
        self.steps.append({'step':self.adapter.decisions,'source':source,'raw_model_response':raw,'parsed_action':action,'executed_action':action,'request_id':request_id,'before':before,'after':self.adapter.view.copy(),'observation_hash':digest(self.adapter.view),'host_outcome':self.adapter.outcome()})
        if hasattr(self,'checkpoint'):self.checkpoint(self.steps)
        return receipt
