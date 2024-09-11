from dataclasses import dataclass
from random import Random
from random import _inst as default_random


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


def d(size: int) -> SimpleDice:
    return SimpleDice(1, size, 0)
