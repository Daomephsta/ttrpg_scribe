import re
from dataclasses import dataclass
from random import Random
from random import _inst as default_random
from typing import Any, Self


class Rollable:
    def roll(self) -> int:
        raise NotImplementedError()


@dataclass
class SimpleDice(Rollable):
    count: int
    size: int
    mod: int

    def roll(self, rng: Random = default_random) -> int:
        return sum(rng.randrange(1, self.size + 1)
            for _ in range(self.count))

    def average(self) -> float:
        return (self.size + 1) / 2 * self.count + self.mod

    @classmethod
    def parse(cls, value: str) -> Self:
        value = value.replace(' ', '')  # Remove all spaces
        result = re.match(r'(?P<count>\d+)d(?P<size>\d+)(?P<mod>[+-]\d+)?', value,
                          flags=re.IGNORECASE)
        if result is None:
            raise ValueError(f'Cannot parse {value}')
        groups = result.groupdict()
        return cls(
            int(groups['count'] or '1'),
            int(groups['size']),
            int(groups['mod'] or '0')
        )

    def __mul__(self, mult: int) -> 'SimpleDice':
        return SimpleDice(mult * self.count, self.size, self.mod)

    def __rmul__(self, mult: int) -> 'SimpleDice':
        return self.__mul__(mult)

    def __add__(self, bonus: int) -> 'SimpleDice':
        return SimpleDice(self.count, self.size, self.mod + bonus)

    def __radd__(self, bonus: int) -> 'SimpleDice':
        return self + bonus

    def __sub__(self, malus: int) -> 'SimpleDice':
        return SimpleDice(self.count, self.size, self.mod - malus)

    def __str__(self, joiner='') -> str:
        if self.mod:
            return f'{self.count}d{self.size} + {self.mod}'
        return f'{self.count}d{self.size}'

    def to_json(self) -> dict[str, Any]:
        return dict(
            count=self.count,
            size=self.size,
            mod=self.mod
        )

    @staticmethod
    def from_json(data: dict):
        return SimpleDice(data['count'], data['size'], data['mod'])


def d(size: int) -> SimpleDice:
    return SimpleDice(1, size, 0)
