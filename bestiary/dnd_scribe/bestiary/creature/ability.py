from dataclasses import dataclass
from typing import ClassVar, Self


def mod(stat: int):
    return stat // 2 - 5


def mod_str(stat: int):
    return f'{mod(stat):+d}'


class _AbilityMeta(type):
    def __iter__(self):
        return iter(Ability.BY_ID.values())


@dataclass
class Ability(metaclass=_AbilityMeta):
    name: str

    BY_ID: ClassVar[dict[str, Self]] = {}

    def __post_init__(self) -> None:
        self.abbreviation = self.name[0:3].lower()
        Ability.BY_ID[self.abbreviation] = self

    def mod(self, creature) -> int:
        return mod(getattr(creature, self.abbreviation))

    def to_json(self):
        return self.abbreviation

    @staticmethod
    def from_json(json):
        return Ability.BY_ID[json]

    @staticmethod
    def __iter__():
        return iter(Ability.BY_ID.values())


STR = Ability('Strength')
DEX = Ability('Dexterity')
CON = Ability('Constitution')
INT = Ability('Intelligence')
WIS = Ability('Wisdom')
CHA = Ability('Charisma')


@dataclass
class Skill:
    name: str
    ability: str

    BY_ID: ClassVar[dict[str, Self]] = {}

    def __post_init__(self) -> None:
        self.id = self.name.lower().replace(' ', '-')
        Skill.BY_ID[self.id] = self

    def to_json(self):
        return self.id

    @staticmethod
    def from_json(json):
        return Skill.BY_ID[json]

    def mod(self, creature) -> int:
        return mod(getattr(creature, self.ability))

    def __hash__(self) -> int:
        return hash(self.name)


Acrobatics = Skill("Acrobatics", 'dex')
AnimalHandling = Skill("Animal Handling", 'wis')
Arcana = Skill("Arcana", 'int')
Athletics = Skill("Athletics", 'str')
Deception = Skill("Deception", 'cha')
History = Skill("History", 'int')
Insight = Skill("Insight", 'wis')
Intimidation = Skill("Intimidation", 'cha')
Investigation = Skill("Investigation", 'int')
Medicine = Skill("Medicine", 'wis')
Nature = Skill("Nature", 'int')
Perception = Skill("Perception", 'wis')
Performance = Skill("Performance", 'cha')
Persuasion = Skill("Persuasion", 'cha')
Religion = Skill("Religion", 'int')
SleightOfHand = Skill("Sleight of Hand", 'dex')
Stealth = Skill("Stealth", 'dex')
Survival = Skill("Survival", 'wis')
