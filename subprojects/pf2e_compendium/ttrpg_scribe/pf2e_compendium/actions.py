import re
from functools import partial
from typing import Any, ClassVar, Literal, Self

from ttrpg_scribe.core.dice import SimpleDice


class Action:
    type Cost = Literal[0, 1, 2, 3, 're', 'reaction', 'free'] | str
    type Category = Literal['interaction', 'defensive', 'offensive']
    CATEGORIES: ClassVar[list[Category]] = ['interaction', 'defensive', 'offensive']
    traits: dict[str, Any]
    category: Category

    def __init__(self, name: str, desc: str = '', cost: Cost = 1,
                 traits: list[str] | dict[str, Any] = [], trigger: str = '',
                 category: Category = 'interaction'):
        self.name = name
        self.desc = desc
        self.cost = cost

        def parse_trait(trait: str) -> tuple[str, Any]:
            trait = trait.lower().replace(' ', '-')
            m = re.match(r'([a-z-]+)-(d\d+|\d+|\w$)', trait)
            if m:
                return m[1], m[2]
            return trait, None
        match traits:
            case dict():
                self.traits = traits
            case list():
                self.traits = dict(parse_trait(t) for t in traits)

        self.trigger = trigger
        self.category = category

    def kind(self):
        return self.__class__.__name__

    def to_json(self) -> dict[str, Any]:
        return dict(
            kind=self.kind(),
            name=self.name,
            desc=self.desc,
            cost=self.cost,
            traits=self.traits,
            trigger=self.trigger
        )

    @classmethod
    def from_json(cls, data: dict) -> Self:
        @staticmethod
        def from_json_as(data: dict, kind: type[Self]) -> Self:
            return kind.from_json_with(
                partial(kind, name=data['name'], desc=data['desc'], cost=data['cost'],
                        traits=data['traits'], trigger=data['trigger']),
                data
            )

        kind = data.pop('kind')
        if cls != Action and kind != cls.__name__:
            raise ValueError(f'Kind {kind} does not match cls {cls}')
        match kind:
            case 'Action':
                return from_json_as(data, Action)
            case 'Strike':
                return from_json_as(data, Strike)
            case _ as kind:
                raise ValueError(f'Unknown kind {kind} for action {data}')

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        ...


def interaction(name: str, desc: str = '', cost: Action.Cost = 1, traits: list[str] = [],
                 trigger=''):
    return Action(name, desc, cost, traits, trigger, 'interaction')


def passive(name: str, desc: str = '', traits: list[str] = [],
                 trigger=''):
    return Action(name, desc, 0, traits, trigger, 'interaction')


def defensive(name: str, desc: str = '', cost: Action.Cost = 1, traits: list[str] = [],
                 trigger=''):
    return Action(name, desc, cost, traits, trigger, 'defensive')


def offensive(name: str, desc: str = '', cost: Action.Cost = 1, traits: list[str] = [],
                 trigger=''):
    return Action(name, desc, cost, traits, trigger, 'offensive')


class Strike(Action):
    type WeaponType = Literal['melee', 'ranged']
    WEAPON_TYPES: ClassVar[list[WeaponType]] = ['melee', 'ranged']

    def __init__(self, name: str, weapon_type: WeaponType, bonus: int,
                 damage: list[tuple[SimpleDice | int, str]], desc: str = '', cost: Action.Cost = 1,
                 traits: list[str] = [], trigger='', category: 'Action.Category' = 'offensive',
                 effects: list[str] = []):
        super().__init__(name, desc, cost, traits, trigger, category)
        self.weapon_type: 'Strike.WeaponType' = weapon_type
        self.bonus = bonus
        self.damage = list(damage)
        self.effects = list(effects)

    def attack_maluses(self):
        if 'agile' in self.traits:
            return [4, 8]
        return [5, 10]

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        return curried_constructor(
            weapon_type=data['weapon_type'],
            bonus=data['bonus'],
            damage=[
                (amount if isinstance(amount, int) else SimpleDice.from_json(amount), damage_type)
                for amount, damage_type in data['damage']
            ],
            effects=data['effects']
        )

    def to_json(self):
        data = super().to_json()
        data.update(
            weapon_type=self.weapon_type,
            bonus=self.bonus,
            damage=[(amount, damage_type)
                    for amount, damage_type in self.damage],
            effects=self.effects
        )
        return data
