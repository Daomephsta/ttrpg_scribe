from dataclasses import dataclass
from typing import Any

from dnd_scribe.encounter.flask import Creature


@dataclass
class Action:
    name: str
    cost: int
    traits: list[str]

    def kind(self):
        return self.__class__.__name__

    def to_json(self) -> dict[str, Any]:
        return dict(
            kind=self.kind(),
            name=self.name,
            cost=self.cost,
            traits=self.traits,
        )

    @staticmethod
    def from_json(data: dict):
        match data.pop('kind'):
            case 'SimpleAction':
                return SimpleAction(**data)
            case 'Strike':
                return Strike(**data)
            case _ as kind:
                raise ValueError(f'Unknown kind {kind} for action {data}')


@dataclass
class SimpleAction(Action):
    desc: str

    def to_json(self):
        data = super().to_json()
        data['desc'] = self.desc
        return data


@dataclass
class Strike(Action):
    weapon_type: str
    bonus: int
    damage: list[tuple[str, str]]
    effects: list[str]

    def attack_maluses(self):
        if 'agile' in self.traits:
            return [0, 4, 8]
        return [0, 5, 10]

    def to_json(self):
        data = super().to_json()
        data.update(
            weapon_type=self.weapon_type,
            bonus=self.bonus,
            damage=self.damage,
            effects=self.effects
        )
        return data


@dataclass
class PF2Creature(Creature):
    name: str
    level: int
    alignments: list[str]
    size: str
    traits: list[str]
    perception: int
    senses: list[str]
    skills: list[tuple[str, int]]
    abilities: dict[str, int]
    interactions: list[str]
    ac: int
    saves: dict[str, int]
    max_hp: int
    immunities: list[str]
    weaknesses: list[tuple[str, int]]
    defenses: list[str]
    speeds: dict[str, int]
    actions: list[Action]

    def initiative_mod(self) -> int:
        return self.abilities['dex']

    def default_hp(self) -> int:
        return self.max_hp

    def to_json(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            level=self.level,
            alignments=self.alignments,
            size=self.size,
            traits=self.traits,
            perception=self.perception,
            senses=self.senses,
            skills=self.skills,
            abilities=self.abilities,
            interactions=self.interactions,
            ac=self.ac,
            saves=self.saves,
            max_hp=self.max_hp,
            immunities=self.immunities,
            weaknesses=self.weaknesses,
            defenses=self.defenses,
            speeds=self.speeds,
            actions=self.actions,
        )

    @classmethod
    def from_json(cls, data):
        return PF2Creature(
            name=data['name'],
            level=data['level'],
            alignments=data['alignments'],
            size=data['size'],
            traits=data['traits'],
            perception=data['perception'],
            senses=data['senses'],
            skills=data['skills'],
            abilities=data['abilities'],
            interactions=data['interactions'],
            ac=data['ac'],
            saves=data['saves'],
            max_hp=data['max_hp'],
            immunities=data['immunities'],
            weaknesses=data['weaknesses'],
            defenses=data['defenses'],
            speeds=data['speeds'],
            actions=[Action.from_json(action) for action in data['actions']]
        )
