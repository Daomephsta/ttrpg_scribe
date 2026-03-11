from dataclasses import dataclass
from typing import Any

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action
from ttrpg_scribe.pf2e_compendium.actor import DetailedValue, PF2Actor, Saves


@dataclass
class PF2Hazard(InitiativeParticipant, PF2Actor):
    name: str
    level: int
    rarity: str
    traits: list[str]
    complex: bool
    stealth: DetailedValue[int]
    disable: str
    saves: Saves[int]
    ac: int
    hardness: int
    max_hp: int
    routine: str
    actions: list[Action]
    reset: str
    description: str

    def initiative_mod(self) -> int:
        return self.stealth.value

    def default_hp(self) -> int:
        return self.max_hp

    type Template = PF2Actor.GenericTemplate['PF2Hazard']

    def apply(self, *templates: Template):
        for template in templates:
            template(self)
        return self

    def write_json(self, data: dict[str, Any]):
        data.update(
            name=self.name,
            level=self.level,
            rarity=self.rarity,
            traits=self.traits,
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
            rarity=data['rarity'],
            traits=data['traits'],
            complex=data['complex'],
            stealth=DetailedValue(data['stealth']['value'], data['stealth']['details']),
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
