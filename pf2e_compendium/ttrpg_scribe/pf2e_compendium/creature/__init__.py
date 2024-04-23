import collections
from dataclasses import dataclass, field
from typing import Any, Callable

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction


@dataclass
class Spellcasting:
    name: str
    tradition: str
    dc: int
    attack: int
    slots: dict[int, list[str]]
    spells: dict[str, str] = field(default_factory=dict)

    def prepared(self):
        for level, spell_ids in self.slots.items():
            def inner():
                spell_counts = collections.Counter(spell_ids)
                for id in spell_counts:
                    yield (self.spells[id], spell_counts[id])
            yield (level, inner())

    def to_json(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            tradition=self.tradition,
            dc=self.dc,
            attack=self.attack,
            slots=self.slots,
            spells=self.spells,
        )

    @staticmethod
    def from_json(data: dict):
        return Spellcasting(
            name=data['name'],
            tradition=data['tradition'],
            dc=data['dc'],
            attack=data['attack'],
            slots={int(level): spells for level, spells in data['slots'].items()},
            spells=data['spells'],
        )


@dataclass
class Skill:
    name: str
    mod: int
    notes: list[str]

    @staticmethod
    def from_json(data: dict):
        return Skill(
            name=data['name'],
            mod=data['mod'],
            notes=data['notes'],
        )


@dataclass
class Sense:
    name: str
    range: int | None
    acuity: str | None

    @staticmethod
    def from_json(data: dict):
        return Sense(
            name=data['name'],
            range=data['range'],
            acuity=data['acuity'],
        )


@dataclass
class PF2Creature(InitiativeParticipant):
    name: str
    level: int
    size: str
    traits: list[str]
    perception: int
    senses: list[Sense]
    skills: list[Skill]
    inventory: dict[str, int]
    abilities: dict[str, int]
    interactions: list[tuple[str, str]]
    ac: int
    saves: dict[str, int]
    max_hp: int
    immunities: list[str]
    resistances: list[tuple[str, int]]
    weaknesses: list[tuple[str, int]]
    defenses: list[SimpleAction]
    speeds: dict[str, int]
    actions: list[Action]
    spellcasting: Spellcasting | None

    def initiative_mod(self) -> int:
        return self.abilities['dex']

    def default_hp(self) -> int:
        return self.max_hp

    def override(self, **overrides):
        for name, value in overrides.items():
            if callable(value):
                value = value(getattr(self, name))
            setattr(self, name, value)
        return self

    def apply(self, *templates: Callable[['PF2Creature'], None]):
        for template in templates:
            template(self)
        return self

    def write_json(self, data: dict[str, Any]):
        data.update(
            type='creature',
            name=self.name,
            level=self.level,
            size=self.size,
            traits=self.traits,
            perception=self.perception,
            senses=self.senses,
            skills=self.skills,
            inventory=self.inventory,
            abilities=self.abilities,
            interactions=self.interactions,
            ac=self.ac,
            saves=self.saves,
            max_hp=self.max_hp,
            immunities=self.immunities,
            resistances=self.resistances,
            weaknesses=self.weaknesses,
            defenses=self.defenses,
            speeds=self.speeds,
            actions=self.actions,
            spellcasting=self.spellcasting
        )

    @classmethod
    def from_json(cls, data):
        return PF2Creature(
            name=data['name'],
            level=data['level'],
            size=data['size'],
            traits=data['traits'],
            perception=data['perception'],
            senses=[Sense.from_json(sense) for sense in data['senses']],
            skills=[Skill.from_json(skill) for skill in data['skills']],
            inventory=data['inventory'],
            abilities=data['abilities'],
            interactions=data['interactions'],
            ac=data['ac'],
            saves=data['saves'],
            max_hp=data['max_hp'],
            immunities=data['immunities'],
            resistances=data['resistances'],
            weaknesses=data['weaknesses'],
            defenses=data['defenses'],
            speeds=data['speeds'],
            actions=[Action.from_json(action) for action in data['actions']],
            spellcasting=Spellcasting.from_json(data['spellcasting'])
                         if data['spellcasting'] else None,
        )
