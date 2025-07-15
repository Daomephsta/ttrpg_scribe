from dataclasses import dataclass
from typing import Any, Callable, Self, TypedDict, Unpack

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction
from ttrpg_scribe.pf2e_compendium.creature import (Abilities, PF2Creature,
                                                   Saves, Sense, Skill,
                                                   Spellcasting)
from ttrpg_scribe.pf2e_compendium.creature.statistics import (StatisticBracket,
                                                              Table)


@dataclass
class Statistic[E]:
    table: Table[E]
    level: int
    bracket: StatisticBracket
    override: E | None = None

    def resolve(self) -> E:
        if self.override is not None:
            return self.override
        return self.bracket.lookup_in(self.table, self.level)


class CreatureBuilder:
    name: str
    level: int
    size: str
    rarity: str
    traits: list[str]

    @property
    def perception(self) -> StatisticBracket:
        return self._perception.bracket

    @perception.setter
    def perception(self, bracket: StatisticBracket):
        self._perception.bracket = bracket

    languages: list[str]
    senses: list[Sense]
    skills: list[Skill]
    inventory: dict[str, int]
    abilities: Abilities[Statistic[int]]
    interactions: list[tuple[str, str]]

    @property
    def ac(self) -> StatisticBracket:
        return self._ac.bracket

    @ac.setter
    def ac(self, bracket: StatisticBracket):
        self._ac.bracket = bracket

    saves: Saves[Statistic[int]]

    @property
    def max_hp(self) -> StatisticBracket:
        return self._max_hp.bracket

    @max_hp.setter
    def max_hp(self, bracket: StatisticBracket):
        self._max_hp.bracket = bracket

    immunities: list[str]
    resistances: dict[str, Statistic[int]]
    weaknesses: dict[str, Statistic[int]]
    defenses: list[SimpleAction]
    speeds: dict[str, int]
    actions: list[Action]
    spellcasting: list[Spellcasting]

    def __init__(self, name: str, level: int):
        from ttrpg_scribe.pf2e_compendium.creature.statistics import (
            ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, MODERATE, PERCEPTION,
            SAVING_THROWS)
        self.name = name
        self.level = level
        self.rarity = 'common'
        self.size = 'medium'
        self.traits = []
        self._perception = Statistic(PERCEPTION, level, MODERATE)
        self.languages = []
        self.senses = []
        self.skills = []
        self.inventory = {}
        self._abilities = {
            'str': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'dex': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'con': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'int': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'wis': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'cha': Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE)
        }
        self.interactions = []
        self._ac = Statistic(ARMOR_CLASS, level, MODERATE)
        self.saves = {
            'fortitude': Statistic(SAVING_THROWS, level, MODERATE),
            'reflex': Statistic(SAVING_THROWS, level, MODERATE),
            'will': Statistic(SAVING_THROWS, level, MODERATE)
        }
        self._max_hp = Statistic(HIT_POINTS, level, MODERATE)
        self.immunities = []
        self.resistances = {}
        self.weaknesses = {}
        self.defenses = []
        self.speeds = {'walk': 25}
        self.actions = []
        self.spellcasting = []

    class _UpdateArgs(TypedDict, total=False):
        name: str
        level: int
        size: str
        rarity: str
        traits: list[str]
        perception: StatisticBracket
        languages: list[str]
        senses: list[Sense]
        skills: list[Skill]
        inventory: dict[str, int]
        abilities: Abilities[Statistic[int]]
        interactions: list[tuple[str, str]]
        ac: StatisticBracket
        saves: Saves[StatisticBracket]
        max_hp: StatisticBracket
        immunities: list[str]
        resistances: dict[str, StatisticBracket]
        weaknesses: dict[str, StatisticBracket]
        defenses: list[SimpleAction]
        speeds: dict[str, int]
        actions: list[Action]
        spellcasting: list[Spellcasting]

    def apply(self, template: Callable[[Self], Any]):
        template(self)
        return self

    def update(self, **kwargs: Unpack['CreatureBuilder._UpdateArgs']):
        for field, value in kwargs.items():
            setattr(self, field, value)
        return self

    def build(self) -> PF2Creature:
        return PF2Creature(
            name=self.name,
            level=self.level,
            rarity=self.rarity,
            size=self.size,
            traits=self.traits,
            perception=self._perception.resolve(),
            languages=self.languages,
            senses=self.senses,
            skills=self.skills,
            inventory=self.inventory,
            abilities={k: v.resolve() for k, v in self._abilities.items()},
            interactions=self.interactions,
            ac=self._ac.resolve(),
            saves={k: v.resolve() for k, v in self.saves.items()},
            max_hp=self._max_hp.resolve(),
            immunities=self.immunities,
            resistances={k: v.resolve() for k, v in self.resistances.items()},
            weaknesses={k: v.resolve() for k, v in self.weaknesses.items()},
            defenses=self.defenses,
            speeds=self.speeds,
            actions=self.actions,
            spellcasting=self.spellcasting
        )
