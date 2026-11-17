"""Shared public history, with timestamped observations rather than inferred truth."""
class StateTracker:
    def __init__(self):self.events=[]
    def update(self,action,view):
        self.events.append({'decision':len(self.events)+1,'action':action,'feedback':view['observation']})
    def context(self,view):
        from .shared_state import public_facts
        return dict(view,public_facts=public_facts(view),history=self.events[-16:],earlier_actions=[e['action'] for e in self.events[:-16]],state_policy='Only current look/inventory are current facts. Historical observations can be stale; do not infer unseen properties.')
