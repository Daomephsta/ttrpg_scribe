from typing import Any, Callable, Self


class Movement:
    def __init__(self, name: str, amount: int, desc_format: str | None = None) -> None:
        self.name = name
        self.amount = amount
        self.desc_format = desc_format if desc_format else f'{name} {{:d}} ft.'

    @classmethod
    def from_dict(cls, speeds: dict[str, Any],
            value_parser: Callable[[Any], int] = lambda x: x) -> dict[str, Self]:

        movement = {}
        for name, value in speeds.items():
            match name:
                case 'walk': movement[name] = Walk(value_parser(value))
                case 'climb': movement[name] = Climb(value_parser(value))
                case 'swim': movement[name] = Swim(value_parser(value))
                case 'burrow': movement[name] = Burrow(value_parser(value))
                case 'fly': movement[name] = Fly(value_parser(value), hover='hover' in speeds)
                case 'hover': pass
                case _: raise ValueError(f'Unknown movement type {name}')
        return movement

    def to_json(self):
        return {
            'name': self.name,
            'amount': self.amount,
            'desc_format': self.desc_format
        }

    @staticmethod
    def from_json(json):
        return Movement(**json)

    def __str__(self) -> str:
        return self.desc_format.format(self.amount)

    __repr__ = __str__

def Walk(amount: int):
    return Movement('walk', amount, desc_format='{:d} ft.')

def Climb(amount: int):
    return Movement('climb', amount)

def Swim(amount: int):
    return Movement('swim', amount)

def Burrow(amount: int):
    return Movement('burrow', amount)

class Fly(Movement):
    def __init__(self, amount: int, hover: bool=False) -> None:
        super().__init__('fly', amount)
        self.desc_format = '{:d} ft. (hover)' if hover else '{:d} ft.'