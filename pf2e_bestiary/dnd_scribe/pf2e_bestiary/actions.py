from typing import Any


class Action:
    def __init__(self, name: str, cost: int = 1, traits: list[str] = []):
        self.name = name
        self.cost = cost
        self.traits = list(traits)  # Copy to avoid sharing with other actions

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


class SimpleAction(Action):
    def __init__(self, name: str, desc: str = '', cost: int = 1, traits: list[str] = []):
        super().__init__(name, cost, traits)
        self.desc = desc

    def to_json(self):
        data = super().to_json()
        data['desc'] = self.desc
        return data


class Strike(Action):
    def __init__(self, name: str, weapon_type: str, bonus: int, damage: list[tuple[str, str]],
                 cost: int = 1, traits: list[str] = [], effects: list[str] = []):
        super().__init__(name, cost, traits)
        self.weapon_type = weapon_type
        self.bonus = bonus
        self.damage = list(damage)
        self.effects = list(effects)

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
