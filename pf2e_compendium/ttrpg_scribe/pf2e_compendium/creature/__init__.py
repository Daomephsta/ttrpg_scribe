import collections
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, SAVING_THROWS,
    SKILLS, StatisticBracket, Table)


@dataclass
class Spellcasting:
    name: str
    tradition: str
    dc: int
    attack: int
    spells: dict[int, list[str]] = field(default_factory=dict)
    id_to_name: dict[str, str] = field(default_factory=dict)

    def iter_spells(self):
        for level, spell_ids in self.spells.items():
            def inner():
                spell_counts = collections.Counter(spell_ids)
                for id in spell_counts:
                    yield (self.id_to_name[id], spell_counts[id])
            yield (level, inner())


    def to_json(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            tradition=self.tradition,
            dc=self.dc,
            attack=self.attack,
            spells=self.spells,
            id_to_name=self.id_to_name,
        )

    @staticmethod
    def from_json(data: dict):
        return Spellcasting(
            name=data['name'],
            tradition=data['tradition'],
            dc=data['dc'],
            attack=data['attack'],
            spells={int(level): spells for level, spells in data['spells'].items()},
            id_to_name=data['id_to_name'],
        )


@dataclass
class Skill:
    name: str
    mod: int
    notes: list[str] = field(default_factory=list)

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
    languages: list[str]
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
    spellcasting: dict[str, Spellcasting]

    def __post_init__(self):
        if 'construct' in self.traits:
            self.immunities += ['bleed', 'death effects', 'disease', 'healing', 'necromancy',
                                'nonlethal attacks', 'poison', 'doomed', 'drained', 'fatigued',
                                'paralyzed', 'sickened', 'unconscious ',]

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

    type Template = Callable[['PF2Creature'], None]

    def apply(self, *templates: Template):
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
            languages=self.languages,
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
            languages=data['languages'],
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
            spellcasting={id: Spellcasting.from_json(e) for id, e in data.get('spellcasting', {}).items()},
        )

    type _Ability = Literal['str', 'dex', 'con', 'int', 'wis', 'cha']
    type _Save = Literal['fortitude', 'reflex', 'will']
    type _Skills = Callable[[Callable[[StatisticBracket], int]], list[Skill]]
    type _Lookup = Callable[[Table, StatisticBracket], Any]

    @staticmethod
    def from_brackets(
            name: str, level: int, size: str, traits: list[str], perception: StatisticBracket,
            skills: _Skills, inventory: dict[str, int],
            abilities: dict[_Ability, StatisticBracket], ac: StatisticBracket,
            saves:  dict[_Save, StatisticBracket], hp: StatisticBracket, speeds: dict[str, int],
            actions: Callable[[_Lookup], list[Any | list[Action]] | list[Action]]
            ):

        def lookup(table: Table, bracket: StatisticBracket):
            return bracket.lookup(table, level)

        def convert_dict(table: Table, d: Mapping) -> dict[str, int]:
            return {key: lookup(table, bracket) for key, bracket in d.items()}

        match actions(lookup):
            case [*_, [*actions0]]: pass
            case [*actions0]: pass

        return PF2Creature(
            name=name,
            level=level,
            size=size,
            traits=traits,
            perception=lookup(PERCEPTION, perception),
            languages=[],
            senses=[],
            skills=skills(lambda bracket: lookup(SKILLS, bracket)),
            inventory=inventory,
            abilities=convert_dict(ATTRIBUTE_MODIFIERS, abilities),
            interactions=[],
            ac=ac.lookup(ARMOR_CLASS, level),
            saves=convert_dict(SAVING_THROWS, saves),
            max_hp=hp.lookup(HIT_POINTS, level),
            immunities=[],
            resistances=[],
            weaknesses=[],
            defenses=[],
            speeds=speeds,
            actions=actions0,
            spellcasting={},
        )
