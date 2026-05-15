import re
from functools import partial
from typing import Any, ClassVar, Literal, Self

from ttrpg_scribe.core.dice import SimpleDice


class Action:
    type Category = Literal['interaction', 'defensive', 'offensive']
    CATEGORIES: ClassVar[list[Category]] = ['interaction', 'defensive', 'offensive']
    traits: dict[str, Any]
    category: Category

    def __init__(self, name: str, cost: str | int, traits: list[str] | dict[str, Any],
                 trigger: str, category: Category | None):
        self.name = name
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
        self.category = category or 'interaction'

    def kind(self):
        return self.__class__.__name__

    def to_json(self) -> dict[str, Any]:
        return dict(
            kind=self.kind(),
            name=self.name,
            cost=self.cost,
            traits=self.traits,
            trigger=self.trigger
        )

    @classmethod
    def from_json(cls, data: dict) -> Self:
        @staticmethod
        def from_json_as(data: dict, kind: type[Self]) -> Self:
            return kind.from_json_with(
                partial(kind, name=data['name'], cost=data['cost'], traits=data['traits'],
                        trigger=data['trigger']),
                data
            )

        kind = data.pop('kind')
        if cls != Action and kind != cls.__name__:
            raise ValueError(f'Kind {kind} does not match cls {cls}')
        match kind:
            case 'SimpleAction':
                return from_json_as(data, SimpleAction)
            case 'Strike':
                return from_json_as(data, Strike)
            case _ as kind:
                raise ValueError(f'Unknown kind {kind} for action {data}')

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        ...


class SimpleAction(Action):
    def __init__(self, name: str, desc: str = '', cost: str | int = 1, traits: list[str] = [],
                 trigger='', category: 'Action.Category' = 'interaction'):
        super().__init__(name, cost, traits, trigger, category)
        self.desc = desc

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        return curried_constructor(desc=data['desc'])

    def to_json(self):
        data = super().to_json()
        data['desc'] = self.desc
        return data


class Strike(Action):
    def __init__(self, name: str, weapon_type: str, bonus: int,
                 damage: list[tuple[SimpleDice | int, str]], cost: str | int = 1,
                 traits: list[str] = [], trigger='', category: 'Action.Category' = 'offensive',
                 effects: list[str] = []):
        super().__init__(name, cost, traits, trigger, category)
        self.weapon_type = weapon_type
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
