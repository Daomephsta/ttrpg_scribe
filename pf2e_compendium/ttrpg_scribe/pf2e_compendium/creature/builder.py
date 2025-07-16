from dataclasses import dataclass
from typing import Any, Callable, Self, TypedDict, Unpack

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction
from ttrpg_scribe.pf2e_compendium.creature import (Abilities, PF2Creature,
                                                   Saves, Sense, Skill,
                                                   Spellcasting, statistics)
from ttrpg_scribe.pf2e_compendium.creature.statistics import (StatisticBracket,
                                                              Table)

type BracketOrValue[T] = StatisticBracket | T


@dataclass
class _Statistic[E]:
    table: Table[E]
    level: int
    bracket: StatisticBracket
    override: E | None = None

    def resolve(self) -> E:
        if self.override is not None:
            return self.override
        return self.table[self.level, self.bracket]

    def update(self, value: BracketOrValue[E]):
        match value:
            case StatisticBracket():
                self.bracket = value
            case int():
                self.override = value


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
    abilities: Abilities[_Statistic[int]]
    interactions: list[tuple[str, str]]

    @property
    def ac(self) -> StatisticBracket:
        return self._ac.bracket

    @ac.setter
    def ac(self, bracket: StatisticBracket):
        self._ac.bracket = bracket

    saves: Saves[_Statistic[int]]

    @property
    def max_hp(self) -> StatisticBracket:
        return self._max_hp.bracket

    @max_hp.setter
    def max_hp(self, bracket: StatisticBracket):
        self._max_hp.bracket = bracket

    immunities: list[str]
    resistances: dict[str, _Statistic[int]]
    weaknesses: dict[str, _Statistic[int]]
    defenses: list[SimpleAction]
    speeds: dict[str, int]
    actions: list[Action]
    spellcasting: list[Spellcasting]

    type Template = Callable[[Self], Any]

    def __init__(self, name: str, level: int, init_template: Template):
        from ttrpg_scribe.pf2e_compendium.creature.statistics import (
            ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, MODERATE, PERCEPTION,
            SAVING_THROWS)
        self.name = name
        self.level = level
        self.rarity = 'common'
        self.size = 'medium'
        self.traits = []
        self._perception = _Statistic(PERCEPTION, level, MODERATE)
        self.languages = []
        self.senses = []
        self.skills = []
        self.inventory = {}
        self.abilities = {
            'str': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'dex': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'con': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'int': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'wis': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE),
            'cha': _Statistic(ATTRIBUTE_MODIFIERS, level, MODERATE)
        }
        self.interactions = []
        self._ac = _Statistic(ARMOR_CLASS, level, MODERATE)
        self.saves = {
            'fortitude': _Statistic(SAVING_THROWS, level, MODERATE),
            'reflex': _Statistic(SAVING_THROWS, level, MODERATE),
            'will': _Statistic(SAVING_THROWS, level, MODERATE)
        }
        self._max_hp = _Statistic(HIT_POINTS, level, MODERATE)
        self.immunities = []
        self.resistances = {}
        self.weaknesses = {}
        self.defenses = []
        self.speeds = {'walk': 25}
        self.actions = []
        self.spellcasting = []
        self.apply(init_template)

    def terrible[E](self, table: Table[E]) -> E:
        return table[self.level, statistics.TERRIBLE]

    def low[E](self, table: Table[E]) -> E:
        return table[self.level, statistics.LOW]

    def moderate[E](self, table: Table[E]) -> E:
        return table[self.level, statistics.MODERATE]

    def high[E](self, table: Table[E]) -> E:
        return table[self.level, statistics.HIGH]

    def extreme[E](self, table: Table[E]) -> E:
        return table[self.level, statistics.EXTREME]

    def apply(self, template: Template):
        template(self)
        return self

    class _UpdateAppendArgs(TypedDict, total=False):
        traits: list[str]
        languages: list[str]
        senses: list[Sense]
        skills: list[Skill]
        inventory: dict[str, int]
        interactions: list[tuple[str, str]]
        immunities: list[str]
        defenses: list[SimpleAction]
        speeds: dict[str, int]
        actions: list[Action]
        spellcasting: list[Spellcasting]

    def update_append(self, **kwargs: Unpack['CreatureBuilder._UpdateAppendArgs']):
        for field, value in kwargs.items():
            current = getattr(self, field)
            setattr(self, field, current + value)
        return self

    class _UpdateArgs(TypedDict, total=False):
        name: str
        level: int
        size: str
        rarity: str
        traits: list[str]
        perception: BracketOrValue[int]
        languages: list[str]
        senses: list[Sense]
        skills: list[Skill]
        inventory: dict[str, int]
        abilities: Abilities[BracketOrValue[int]]
        interactions: list[tuple[str, str]]
        ac: BracketOrValue[int]
        saves: Saves[BracketOrValue[int]]
        max_hp: BracketOrValue[int]
        immunities: list[str]
        resistances: dict[str, BracketOrValue[int]]
        weaknesses: dict[str, BracketOrValue[int]]
        defenses: list[SimpleAction]
        speeds: dict[str, int]
        actions: list[Action]
        spellcasting: list[Spellcasting]

    def update(self, **kwargs: Unpack['CreatureBuilder._UpdateArgs']):
        def update_dict[K, V](statistics: dict[K, '_Statistic[V]'],
                              values: dict[K, BracketOrValue[V]]):
            for key in values:
                statistics[key].update(values[key])

        update_dict(self.abilities, kwargs.pop('abilities', {}))
        update_dict(self.saves, kwargs.pop('saves', {}))
        for field, value in kwargs.items():
            current = getattr(self, field)
            if isinstance(current, _Statistic):
                current.update(value)
            else:
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
            abilities={k: v.resolve() for k, v in self.abilities.items()},
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
