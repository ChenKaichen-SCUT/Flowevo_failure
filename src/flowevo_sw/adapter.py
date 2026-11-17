import os
from dataclasses import dataclass
from scienceworld import ScienceWorldEnv
from .public_view import public_view
from .state_tracker import StateTracker

@dataclass
class Receipt:
    observation:str
    score:float
    done:bool
    won:bool
    admissible_commands:list

class ScienceWorldAdapter:
    """Host-only owner of Java; models receive serialized allowlisted public_view."""
    def __init__(self,limit=100):
        os.environ.pop('SCIENCEWORLD_DEBUG',None)
        self._env=ScienceWorldEnv(envStepLimit=limit);self.limit=limit
    def reset(self,task,variation):
        self._env.load(task,variation,simplificationStr='',generateGoldPath=False)
        obs,info=self._env.reset();self.decisions=0;self.highest=info['score'];self.done=False
        self.tracker=StateTracker();self.view=public_view(obs,info);self.initial=self.view.copy()
        self.info=info;self.native=bool(self._env.server.getCompleted())
        return self.view
    def execute(self,action):
        if self.done or self.decisions>=self.limit:raise RuntimeError('EPISODE_ALREADY_TERMINATED')
        obs,reward,done,info=self._env.step(action);self.decisions+=1
        self.info=info;self.native=bool(self._env.server.getCompleted());self.highest=max(self.highest,info['score'])
        self.done=done or self.decisions>=self.limit
        self.view=public_view(obs,info);self.tracker.update(action,self.view)
        return Receipt(obs,info['score'],self.done,self.native and info['score']==100,info['valid'])
    def context(self):return self.tracker.context(self.view)
    def outcome(self):
        score=self.info['score'];success=self.native and score==100
        reason='SUCCESS' if success else 'NEGATIVE_SCORE' if score<0 else 'NATIVE_INCOMPLETE' if self.native else 'HOST_STEP_LIMIT' if self.decisions>=self.limit else 'ENVIRONMENT_STEP_LIMIT' if self.done else 'AGENT_STOPPED'
        return dict(success=success,final_score=score,highest_score=self.highest,native_completion=self.native,wrapper_done=self.done,environment_moves=self.info['moves'],host_decisions=self.decisions,termination_reason=reason)
    def close(self):self._env.close()

class SolverFacade:
    """No generic forwarding of attributes or Java/gold handles."""
    __slots__=('_public',)
    def __init__(self,view):self._public=view
    def context(self):return self._public.copy()
    def __getattr__(self,name):raise PermissionError('Private environment API denied')
