from dataclasses import dataclass
from random import Random
from random import _inst as default_random


class Rollable:
    def roll(self) -> int:
        raise NotImplementedError()

class DiceFormulaPart:
    def apply(self, total) -> int:
        raise NotImplementedError()

    def average(self) -> float:
        raise NotImplementedError()

@dataclass
class DiceFormula(Rollable):
    parts: list[DiceFormulaPart]

    def roll(self) -> int:
        total: int = 0
        for part in self.parts:
            total = part.apply(total)
        return total

    def average_floored(self) -> int:
        return int(self.average())

    def average(self) -> float:
        return sum(part.average() for part in self.parts)

    def damage_notation(self) -> str:
        return f'{self.average_floored()} ({self})'

    def __str__(self) -> str:
        return ' '.join(map(str, self.parts))

class Symbol(str, DiceFormulaPart):
    def apply(self, total) -> int:
        return total

    def average(self) -> float:
        return 0

@dataclass
class Constant(DiceFormulaPart):
    value: int

    def apply(self, total) -> int:
        return total + self.value

    def average(self) -> float:
        return self.value

    def __str__(self) -> str:
        return str(abs(self.value))

@dataclass
class Dice(DiceFormulaPart, Rollable):
    count: int
    size: int

    def roll(self, rng: Random = default_random) -> int:
        return sum(rng.randrange(1, self.size + 1)
            for _ in range(self.count))

    def apply(self, total) -> int:
        return total + self.roll()

    def average(self) -> float:
        return self.count * (self.size + 1) / 2

    def __str__(self) -> str:
        return f'{self.count}d{self.size}'

    def __mul__(self, mult: int):
        return Dice(mult * self.count, self.size)

    def __rmul__(self, mult: int):
        return self.__mul__(mult)

    def __add__(self, bonus: 'int | Dice') -> DiceFormula:
        match bonus:
            case 0:
                return DiceFormula([self])
            case int(bonus):
                symbol = '+' if bonus > 0 else '-'
                return DiceFormula([self, Symbol(symbol), Constant(bonus)])
            case Dice():
                return DiceFormula([self, Symbol('+'), bonus])

    def __radd__(self, bonus: int):
        return self.__add__(bonus)

    def __sub__(self, malus: int):
        if malus == 0:
            return DiceFormula([self])
        return DiceFormula([self, Symbol('-'), Constant(-malus)])

def d(size: int) -> Dice:
    return Dice(1, size)
