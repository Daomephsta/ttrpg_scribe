import re
from functools import partial
from typing import Any, Self

from ttrpg_scribe.core.dice import SimpleDice


class Action:
    traits: dict[str, Any]

    def __init__(self, name: str, cost: str | int, traits: list[str] | dict[str, Any],
                 trigger: str):
        self.name = name
        self.cost = cost
        self.trigger = trigger

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

    @staticmethod
    def from_json(data: dict):
        def from_json_as(kind: type[Action]):
            return kind.from_json_with(
                partial(kind, name=data['name'], cost=data['cost'], traits=data['traits'],
                        trigger=data['trigger']),
                data
            )
        match data.pop('kind'):
            case 'SimpleAction':
                return from_json_as(SimpleAction)
            case 'Strike':
                return from_json_as(Strike)
            case _ as kind:
                raise ValueError(f'Unknown kind {kind} for action {data}')

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        ...


class SimpleAction(Action):
    def __init__(self, name: str, desc: str = '', cost: str | int = 1, traits: list[str] = [],
                 trigger=''):
        super().__init__(name, cost, traits, trigger)
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
                 traits: list[str] = [], trigger='', effects: list[str] = []):
        super().__init__(name, cost, traits, trigger)
        self.weapon_type = weapon_type
        self.bonus = bonus
        self.damage = list(damage)
        self.effects = list(effects)

    def attack_maluses(self):
        if 'agile' in self.traits:
            return [0, 4, 8]
        return [0, 5, 10]

    @classmethod
    def from_json_with(cls, curried_constructor: partial, data: dict) -> Self:
        return curried_constructor(
            weapon_type=data['weapon_type'],
            bonus=data['bonus'],
            damage=[(SimpleDice.from_json(amount), damage_type)
                    for amount, damage_type in data['damage']],
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
