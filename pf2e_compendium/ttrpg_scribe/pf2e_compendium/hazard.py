from dataclasses import dataclass
from typing import Any

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action


@dataclass
class PF2Hazard(InitiativeParticipant):
    name: str
    level: int
    complex: bool
    stealth: int
    disable: str
    ac: int
    saves: dict[str, int]
    hardness: int
    max_hp: int
    routine: str
    actions: list[Action]
    reset: str
    description: str

    def initiative_mod(self) -> int:
        return self.stealth

    def default_hp(self) -> int:
        return self.max_hp

    def write_json(self, data: dict[str, Any]):
        data.update(
            name=self.name,
            level=self.level,
            complex=self.complex,
            stealth=self.stealth,
            disable=self.disable,
            ac=self.ac,
            saves=self.saves,
            hardness=self.hardness,
            max_hp=self.max_hp,
            routine=self.routine,
            actions=self.actions,
            reset=self.reset,
            description=self.description,
        )

    @classmethod
    def from_json(cls, data):
        return PF2Hazard(
            name=data['name'],
            level=data['level'],
            complex=data['complex'],
            stealth=data['stealth'],
            disable=data['disable'],
            ac=data['ac'],
            saves=data['saves'],
            hardness=data['hardness'],
            max_hp=data['max_hp'],
            routine=data['routine'],
            actions=[Action.from_json(action) for action in data['actions']],
            reset=data['reset'],
            description=data['description'],
        )
