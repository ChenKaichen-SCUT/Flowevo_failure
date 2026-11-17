"""ScienceWorld metadata preserved across compile, library and retrieval boundaries."""
from dataclasses import dataclass,field
import copy
from alfworld_.schemas import AlfWorldSkillTemplate

@dataclass
class ScienceSkillTemplate(AlfWorldSkillTemplate):
    applicability: str = ''
    parameter_roles: dict = field(default_factory=dict)
    source_contract: dict = field(default_factory=dict)

    def to_dict(self):
        data=super().to_dict()
        data.update(applicability=self.applicability,parameter_roles=self.parameter_roles,source_contract=self.source_contract)
        return copy.deepcopy(data)

    @classmethod
    def from_dict(cls,data):
        base=AlfWorldSkillTemplate.from_dict(data)
        return cls(**base.to_dict(),applicability=data.get('applicability',''),
                   parameter_roles=copy.deepcopy(data.get('parameter_roles',{})),source_contract=copy.deepcopy(data.get('source_contract',{})))
