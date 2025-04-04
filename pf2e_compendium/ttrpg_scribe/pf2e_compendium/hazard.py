from dataclasses import dataclass
import re
from typing import Any, Callable

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike


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

    type Template = Callable[['PF2Hazard'], None]

    def apply(self, *templates: Template):
        for template in templates:
            template(self)
        return self

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


def map_all_text(mapper: Callable[[str], str]) -> PF2Hazard.Template:
    def template(creature: PF2Hazard):
        for action in creature.actions:
            match action:
                case SimpleAction():
                    action.name = mapper(action.name)
                    action.desc = mapper(action.desc)
    return template


def adjust_all_dcs(delta: int) -> PF2Hazard.Template:
    def template(creature: PF2Hazard):
        creature.ac += delta
        creature.apply(map_all_text(lambda s: re.sub(
            r'([AD]C) (\d+)',
            lambda match: f'{match[1]} {int(match[2]) + delta}', s)
        ))
    return template


def elite(hazard: PF2Hazard):
    hazard.name = f'Elite {hazard.name}'
    starting_level = hazard.level
    hazard.level += 1 if hazard.level > 0 else 2
    # Increase AC and DCs
    hazard.apply(adjust_all_dcs(2))
    # Increase attack bonus & damage
    for action in hazard.actions:
        match action:
            case Strike():
                action.bonus += 2
                # Only boost the main/first damage type
                amount, damage_type = action.damage[0]
                action.damage[0] = amount + 2, damage_type

    for save in hazard.saves:
        if hazard.saves[save]:  # Hazard saves can be None
            hazard.saves[save] += 2
    hazard.stealth += 2
    if starting_level <= 1:
        hazard.max_hp += 10
    elif 2 <= starting_level <= 4:
        hazard.max_hp += 15
    elif 5 <= starting_level <= 19:
        hazard.max_hp += 20
    else:
        hazard.max_hp += 30


def weak(hazard: PF2Hazard):
    hazard.name = f'Weak {hazard.name}'
    starting_level = hazard.level
    hazard.level -= 1 if hazard.level != 1 else 2
    # Decrease AC and DCs
    hazard.apply(adjust_all_dcs(-2))
    # Decrease attack bonus & damage
    for action in hazard.actions:
        match action:
            case Strike():
                action.bonus -= 2
                # Only reduce the main/first damage type
                amount, damage_type = action.damage[0]
                action.damage[0] = amount - 2, damage_type
    for save in hazard.saves:
        if hazard.saves[save]:  # Hazard saves can be None
            hazard.saves[save] -= 2
    hazard.stealth -= 2
    if starting_level <= 2:
        hazard.max_hp -= 10
    elif 3 <= starting_level <= 5:
        hazard.max_hp -= 15
    elif 6 <= starting_level <= 20:
        hazard.max_hp -= 20
    else:
        hazard.max_hp -= 30
