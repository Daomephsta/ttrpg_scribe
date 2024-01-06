from dataclasses import dataclass
from typing import Any


@dataclass
class Action:
    name: str
    cost: int
    traits: list[str]

    def kind(self):
        return self.__class__.__name__

    def to_json(self) -> dict[str, Any]:
        return dict(
            kind=self.kind(),
            name=self.name,
            cost=self.cost,
            traits=self.traits,
        )

    @staticmethod
    def from_json(data: dict):
        match data.pop('kind'):
            case 'SimpleAction':
                return SimpleAction(**data)
            case 'Strike':
                return Strike(**data)
            case _ as kind:
                raise ValueError(f'Unknown kind {kind} for action {data}')


@dataclass
class SimpleAction(Action):
    desc: str

    def to_json(self):
        data = super().to_json()
        data['desc'] = self.desc
        return data


@dataclass
class Strike(Action):
    weapon_type: str
    bonus: int
    damage: list[tuple[str, str]]
    effects: list[str]

    def attack_maluses(self):
        if 'agile' in self.traits:
            return [0, 4, 8]
        return [0, 5, 10]

    def to_json(self):
        data = super().to_json()
        data.update(
            weapon_type=self.weapon_type,
            bonus=self.bonus,
            damage=self.damage,
            effects=self.effects
        )
        return data
