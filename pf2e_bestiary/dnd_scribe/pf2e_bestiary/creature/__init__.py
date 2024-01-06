from dataclasses import dataclass
from typing import Any

from dnd_scribe.encounter.flask import Creature
from dnd_scribe.pf2e_bestiary.actions import Action


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
    interactions: list[tuple[str, str]]
    ac: int
    saves: dict[str, int]
    max_hp: int
    immunities: list[str]
    weaknesses: list[tuple[str, int]]
    defenses: list[tuple[str, str]]
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
