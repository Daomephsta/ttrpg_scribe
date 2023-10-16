import json
import math
import re
from typing import (Any, Callable, Iterable, TypedDict, TypeVar,
                    Unpack, cast)

from pluralizer import Pluralizer

from .ability import Ability, Perception, Skill, mod
from .armour import ArmourClass
from .movement import Movement
from .sense import Sense

XP_BY_CR = {0: 10, 1/8: 25, 1/4: 50, 1/2: 100, 1: 200, 2: 450, 3: 700, 4: 1_100, 5: 1_800, 6: 2_300, 7: 2_900, 8: 3_900, 9: 5_000, 10: 5_900, 11: 7_200, 12: 8_400, 13: 10_000, 14: 11_500, 15: 13_000, 16: 15_000, 17: 18_000, 18: 20_000, 19: 22_000, 20: 25_000, 21: 33_000, 22: 41_000, 23: 50_000, 24: 62_000, 25: 75_000, 26: 90_000, 27: 105_000, 28: 120_000, 29: 135_000, 30: 155_000}  # noqa: E501


class Constant(int):
    def __call__(self, _) -> int:
        return self


class Creature:
    ITALICISE_PATTERN = re.compile(r'(Melee Weapon Attack|Ranged Weapon Attack|Hit)')
    PLURALIZER = Pluralizer()
    DefaultHp = Callable[['Creature'], int]
    Statistics = tuple[int, int, int, int, int, int]
    Feature = tuple[str, str] | Callable[['Creature'], tuple[str, str]]
    Trait = Feature
    Action = Feature
    TemplateArgs = TypedDict('TemplateArgs', {'name': str, 'size': str, 'type': str, 'alignment': str, 'ac': int | list[ArmourClass], 'hp': tuple[int, int], 'speeds': Iterable[Movement], 'statistics': Statistics, 'cr': float, 'saves': list[Ability], 'skill_profs': list[Skill | tuple[Skill, int]], 'vulnerabilities': list[str], 'resistances': list[str], 'immunities': list[str], 'senses': list[Sense], 'languages': list[str], 'traits': list[Trait], 'actions': list[Action], 'bonus_actions': list[Action], 'reactions': list[Action], 'default_hp': DefaultHp | int, 'lore': str},  # noqa: E501
                             total=True)
    ConstructorArgs = TypedDict('ConstructorArgs', {'saves': list[Ability], 'skill_profs': list[Skill | tuple[Skill, int]], 'vulnerabilities': list[str], 'resistances': list[str], 'immunities': list[str], 'senses': list[Sense], 'languages': list[str], 'traits': list[Trait], 'actions': list[Action], 'bonus_actions': list[Action], 'reactions': list[Action], 'default_hp': DefaultHp | int, 'lore': str},  # noqa: E501
                                total=False)
    DeriveArgs = TypedDict('DeriveArgs', {'name': str, 'size': str, 'type': str, 'alignment': str, 'ac': int | list[ArmourClass], 'hp': tuple[int, int], 'speeds': Iterable[Movement], 'statistics': Statistics, 'cr': float, 'saves': list[Ability], 'skill_profs': list[Skill | tuple[Skill, int]], 'vulnerabilities': list[str], 'resistances': list[str], 'immunities': list[str], 'senses': list[Sense], 'languages': list[str], 'traits': list[Trait], 'actions': list[Action], 'bonus_actions': list[Action], 'reactions': list[Action], 'default_hp': DefaultHp | int, 'lore': str},  # noqa: E501
                           total=False)

    def __init__(self, name: str, size: str, type: str, alignment: str,
                 ac: int | list[ArmourClass], hp: tuple[int, int],
                 speeds: Iterable[Movement],
                 statistics: Statistics, cr: float,
                 **args: Unpack[ConstructorArgs]):
        self.name = name
        self.size = size
        self.type = type
        self.alignment = alignment
        match ac:
            case int() as ac:
                self.ac = [ArmourClass(ac, '{ac:d}')]
            case _ as ac:
                self.ac = ac
        self.hp = hp
        match args.get('default_hp'):
            case float() | int() as ac_num:
                self.default_hp = Constant(ac_num)
            case None:
                self.default_hp = Creature.mean_hp
            case _ as func:
                self.default_hp = func
        match speeds:
            case dict() as speeds:
                self.speeds = speeds
            case _ as speeds:
                self.speeds = {speed.name: speed for speed in speeds}
        self.statistics = statistics
        self.cr = cr
        self.prof = int(2 + (self.cr - 1) // 4) if self.cr >= 1 else 2
        self.saves = args.get('saves', [])
        (self.str, self.dex, self.con,
            self.int, self.wis, self.cha) = statistics
        self.vulnerabilities = args.get('vulnerabilities', [])
        self.resistances = args.get('resistances', [])
        self.immunities = args.get('immunities', [])
        self.senses = args.get('senses', [])
        self.languages = args.get('languages', [])
        self.skill_profs: dict[Skill, int] = {}
        for skill in args.get('skill_profs', []):
            if isinstance(skill, Skill):
                self.skill_profs[skill] = skill.mod(self) + self.prof
            else:
                self.skill_profs[skill[0]] = skill[1]

        def realise(suppliers):
            return [supplier if isinstance(supplier, tuple) else supplier(self)
            for supplier in suppliers]
        self.traits = realise(args.get('traits', []))
        self.actions = realise(args.get('actions', []))
        self.bonus_actions = realise(args.get('bonus_actions', []))
        self.reactions = realise(args.get('reactions', []))
        self.xp = XP_BY_CR[self.cr]
        self.lore = args.get('lore', '')

    Template = Callable[[TemplateArgs], None]

    def derive(self, *templates: Template, merge: dict[str, Any] = {},
               **overrides: Unpack[DeriveArgs]):
        args: Creature.TemplateArgs = {
            'name': self.name,
            'size': self.size,
            'type': self.type,
            'alignment': self.alignment,
            'ac': self.ac,
            'hp': self.hp,
            'default_hp': self.default_hp,
            'speeds': self.speeds.values(),
            'statistics': self.statistics,
            'cr': self.cr,
            'saves': self.saves,
            'skill_profs': list(self.skill_profs.items()),
            'vulnerabilities': self.vulnerabilities,
            'resistances': self.resistances,
            'immunities': self.immunities,
            'senses': self.senses,
            'languages': self.languages,
            'traits': [*self.traits],
            'actions': [*self.actions],
            'bonus_actions': [*self.bonus_actions],
            'reactions': [*self.reactions],
            'lore': self.lore
        }
        for key, values in merge.items():
            # += mutates self.key
            # + creates a new array
            args[key] = args[key] + values
        args.update(overrides)
        for template in templates:
            template(args)
        return Creature(**args)

    def plural(self, count) -> str:
        return Creature.PLURALIZER.pluralize(self.name, count)

    def mean_hp(self):
        count, size = self.hp
        con_bonus = count * mod(self.con)
        return math.floor(count * (1 + size) / 2.0 + con_bonus)

    def max_hp(self):
        count, size = self.hp
        con_bonus = count * mod(self.con)
        return count * size + con_bonus

    def to_json(self):
        return {
            'name': self.name,
            'size': self.size,
            'type': self.type,
            'alignment': self.alignment,
            'ac': [ac.to_json() for ac in self.ac],
            'hp': self.hp,
            'default_hp': self.default_hp if isinstance(self.default_hp, Constant)
                else self.default_hp.__name__,
            'speeds': [speed.to_json() for speed in self.speeds.values()],
            'statistics': self.statistics,
            'cr': self.cr,
            'saves': self.saves,
            'skill_profs': [(skill.to_json(), mod) for skill, mod in self.skill_profs.items()],
            'vulnerabilities': self.vulnerabilities,
            'resistances': self.resistances,
            'immunities': self.immunities,
            'senses': self.senses,
            'languages': self.languages,
            'traits': self.traits,
            'actions': self.actions,
            'bonus_actions': self.bonus_actions,
            'reactions': self.reactions,
            'lore': self.lore
        }

    P = TypeVar('P')

    @staticmethod
    def from_json(json):
        return Creature(
            name=json['name'],
            size=json['size'],
            type=json['type'],
            alignment=json['alignment'],
            ac=[ArmourClass.from_json(ac_data) for ac_data in json['ac']],
            hp=cast(tuple[int, int], tuple(json['hp'])),
            default_hp=Constant(json['default_hp']) if isinstance(json['default_hp'], int)
                else getattr(Creature, json['default_hp']),
            speeds=[Movement.from_json(speed) for speed in json['speeds']],
            statistics=cast(Creature.Statistics, tuple(json['statistics'])),
            cr=json['cr'],
            saves=[Ability.from_json(save) for save in json['saves']],
            skill_profs=[(Skill.from_json(skill), mod)
                for skill, mod in json['skill_profs']],
            vulnerabilities=json['vulnerabilities'],
            resistances=json['resistances'],
            immunities=json['immunities'],
            senses=[Sense.from_json(sense) for sense in json['senses']],
            languages=json['languages'],
            traits=[cast(Creature.Trait, tuple(trait))
                for trait in json['traits']],
            actions=[cast(Creature.Action, tuple(action))
                for action in json['actions']],
            bonus_actions=[cast(Creature.Action, tuple(action))
                for action in json['bonus_actions']],
            reactions=[cast(Creature.Action, tuple(action))
                for action in json['reactions']],
            lore=json['lore']
        )

    def pretty_print(self) -> str:
        def default(o):
            if hasattr(o, 'to_json'):
                return o.to_json()
            else:
                raise TypeError(f'{o} doesn\'t define to_json()')
        return json.dumps(self, indent=1, default=default)

    def str_hp(self):
        count, size = self.hp
        con_bonus = count * mod(self.con)
        s = f'{self.default_hp(self):.0f}'
        if con_bonus != 0:
            s += f' ({count}d{size}{con_bonus:+d})'
        else:
            s += f' ({count}d{size})'
        return s

    def str_saves(self):
        return ', '.join([f'{save.abbreviation.upper()} {save.mod(self) + self.prof:+d}'
            for save in self.saves])

    def str_skills(self):
        return ', '.join(f'{skill.name} {bonus:+d}'
            for skill, bonus in self.skill_profs.items())

    def str_senses(self):
        if Perception in self.skill_profs:
            passive_perception = 10 + self.skill_profs[Perception]
        else:
            passive_perception = 10 + mod(self.wis)
        return ', '.join([str(sense) for sense in self.senses] +
            [f'passive Perception {passive_perception}'])

    def str_cr(self):
        return str(self.cr) if self.cr >= 1 or self.cr == 0 else f'1/{1 / self.cr:.0f}'
