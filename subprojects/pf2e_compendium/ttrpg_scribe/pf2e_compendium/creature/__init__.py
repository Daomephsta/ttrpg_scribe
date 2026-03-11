import collections
from dataclasses import dataclass, field
from typing import Any, Callable, ClassVar, Iterable, Literal

from ttrpg_scribe.encounter.flask import InitiativeParticipant
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction
from ttrpg_scribe.pf2e_compendium.actor import PF2Actor, Saves
from ttrpg_scribe.pf2e_compendium.creature import statistics
from ttrpg_scribe.pf2e_compendium.creature.statistics import (StatisticBracket,
                                                              Table)


@dataclass
class Spellcasting:
    name: str
    casting_type: str
    dc: int
    attack: int
    spells: dict[int, list[str]] = field(default_factory=dict)
    slots: dict[int, int] = field(default_factory=dict)
    spell_info: dict[str, Any] = field(default_factory=dict)

    def iter_spells(self):
        for level, spells in sorted(self.spells.items(), key=lambda t: t[0]):
            yield (level, collections.Counter(spells).items())

    def to_json(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            casting_type=self.casting_type,
            dc=self.dc,
            attack=self.attack,
            spells=self.spells,
            slots=self.slots,
            spell_info=self.spell_info
        )

    @staticmethod
    def from_json(data: dict):
        return Spellcasting(
            name=data['name'],
            casting_type=data['casting_type'],
            dc=data['dc'],
            attack=data['attack'],
            spells={int(level): spells for level, spells in data['spells'].items()},
            slots={int(level): slots for level, slots in data['slots'].items()},
            spell_info=data['spell_info']
        )


def zip_with(mappers: Iterable[Callable[[Any], Any] | None], data: Iterable[Any]) -> list[Any]:
    return [mapper(data) if mapper is not None else data
            for mapper, data in zip(mappers, data)]


@dataclass
class Skill:
    type Attribute = Literal['str', 'dex', 'con', 'int', 'wis', 'cha']

    SKILLS: ClassVar[dict[str, Attribute]] = {
        'acrobatics': 'dex',
        'arcana': 'int',
        'athletics': 'str',
        'crafting': 'int',
        'deception': 'cha',
        'diplomacy': 'cha',
        'intimidation': 'cha',
        'medicine': 'wis',
        'nature': 'wis',
        'occultism': 'int',
        'performance': 'cha',
        'religion': 'wis',
        'society': 'int',
        'stealth': 'dex',
        'survival': 'wis',
        'thievery': 'dex'
    }
    name: str
    mod: int
    special: dict[str, int]

    def __init__(self, name: str, mod: int, special: dict[str, int] | list[str] = []):
        if not self.is_valid(name):
            raise ValueError(f"Unknown skill '{name}'")
        self.name = name
        self.mod = mod
        match special:
            case dict():
                self.special = special
            case list():
                self.special = {}
                for e in special:
                    [bonus, condition] = e.split(' ', maxsplit=1)
                    self.special[condition] = int(bonus)

    @classmethod
    def is_valid(cls, name: str) -> bool:
        return name in cls.SKILLS or 'lore' in name

    @staticmethod
    def attribute(skill: str) -> Attribute:
        if 'lore' in skill:
            return 'int'
        return Skill.SKILLS[skill]

    @staticmethod
    def from_json(data: dict):
        return Skill(
            name=data['name'],
            mod=data['mod'],
            special=data['special'],
        )


@dataclass
class Sense:
    name: str
    range: int | None = None
    acuity: str | None = None

    @staticmethod
    def from_json(data: dict):
        return Sense(
            name=data['name'],
            range=data['range'],
            acuity=data['acuity'],
        )


type Abilities[V] = dict[Literal['str', 'dex', 'con', 'int', 'wis', 'cha'], V]


@dataclass
class PF2Creature(InitiativeParticipant, PF2Actor):
    name: str
    level: int
    size: str
    rarity: str
    traits: list[str]
    perception: int
    initiative_source: str
    languages: list[str]
    senses: list[Sense]
    skills: dict[str, Skill]
    inventory: dict[str, int]
    abilities: Abilities[int]
    interactions: list[SimpleAction]
    ac: int
    saves: Saves[int]
    max_hp: int
    immunities: list[str]
    resistances: dict[str, int]
    weaknesses: dict[str, int]
    defenses: list[SimpleAction]
    speeds: dict[str, int]
    actions: list[Action]
    spellcasting: list[Spellcasting]

    def __post_init__(self):
        if 'construct' in self.traits:
            self.immunities += ['bleed', 'death effects', 'disease', 'healing', 'necromancy',
                                'nonlethal attacks', 'poison', 'doomed', 'drained', 'fatigued',
                                'paralyzed', 'sickened', 'unconscious ',]

    def skill_mod(self, skill: str) -> int:
        if skill in self.skills:
            return self.skills[skill].mod
        else:
            return self.abilities[Skill.attribute(skill)]

    def initiative_mod(self) -> int:
        if self.initiative_source == 'perception':
            return self.perception
        else:
            return self.skill_mod(self.initiative_source)

    def default_hp(self) -> int:
        return self.max_hp

    def override(self, **overrides):
        for name, value in overrides.items():
            if callable(value):
                value = value(getattr(self, name))
            setattr(self, name, value)
        return self

    type Template = PF2Actor.GenericTemplate['PF2Creature']

    def apply(self, *templates: Template):
        for template in templates:
            template(self)
        return self

    def write_json(self, data: dict[str, Any]):
        data.update(
            type='creature',
            name=self.name,
            level=self.level,
            rarity=self.rarity,
            size=self.size,
            traits=self.traits,
            perception=self.perception,
            initiative_source=self.initiative_source,
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
            rarity=data['rarity'],
            size=data['size'],
            traits=data['traits'],
            perception=data['perception'],
            initiative_source=data.get('initiative_source', 'perception'),
            languages=data['languages'],
            senses=[Sense.from_json(sense) for sense in data['senses']],
            skills={name: Skill.from_json(skill) for name, skill in data['skills'].items()},
            inventory=data['inventory'],
            abilities=data['abilities'],
            interactions=[SimpleAction.from_json(action) for action in data['interactions']],
            ac=data['ac'],
            saves=data['saves'],
            max_hp=data['max_hp'],
            immunities=data['immunities'],
            resistances=data['resistances'],
            weaknesses=data['weaknesses'],
            defenses=[SimpleAction.from_json(action) for action in data['defenses']],
            speeds=data['speeds'],
            actions=[Action.from_json(action) for action in data['actions']],
            spellcasting=[Spellcasting.from_json(e) for e in data.get('spellcasting', [])],
        )

    type _Skills = Callable[[Callable[[StatisticBracket], int]], list[Skill]]
    type _Lookup = Callable[[Table, StatisticBracket], Any]

    @staticmethod
    def from_brackets(
            name: str, level: int, rarity: str, size: str, traits: list[str],
            perception: StatisticBracket, skills: _Skills, inventory: dict[str, int],
            abilities: Abilities[StatisticBracket], ac: StatisticBracket,
            saves: Saves[StatisticBracket], hp: StatisticBracket, speeds: dict[str, int],
            actions: Callable[[_Lookup], list[Any | list[Action]] | list[Action]]):

        from ttrpg_scribe.pf2e_compendium.creature.builder import \
            CreatureBuilder

        def lookup(table: Table, bracket: StatisticBracket):
            return table.lookup(level, bracket)

        match actions(lookup):
            case [*_, [*actions0]]: pass
            case [*actions0]: pass

        return CreatureBuilder(name, level, lambda b: b.update(
            rarity=rarity,
            size=size,
            traits=traits,
            perception=perception,
            skills={skill.name: skill for skill in
                    skills(lambda bracket: statistics.SKILLS[level, bracket])},
            inventory=inventory,
            abilities=dict(abilities.items()),
            ac=ac,
            saves=dict(saves.items()),
            max_hp=hp,
            speeds=speeds,
            actions=actions0,
        )).build()
