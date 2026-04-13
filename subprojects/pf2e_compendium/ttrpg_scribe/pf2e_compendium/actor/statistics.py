import itertools
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Self

from ttrpg_scribe.core.dice import SimpleDice
from ttrpg_scribe.core.html import Tag


@dataclass
class StatisticBracket:
    name: str
    rank: int = 1
    adjustment: int = 0
    maximum: int | None = None  # Maximum rank or adjustment

    def __post_init__(self):
        if self.rank != 1 and self.adjustment != 0:
            raise ValueError('Rank and adjustment are mutually exclusive')

    def __call__(self, rank: int):
        return StatisticBracket(self.name, rank, self.adjustment)

    def __add__(self, bonus: int):
        return StatisticBracket(self.name, self.rank, self.adjustment + bonus)

    def __sub__(self, penalty: int):
        return StatisticBracket(self.name, self.rank, self.adjustment - penalty)

    def __str__(self) -> str:
        parts = [self.name]
        if self.rank != 1:
            parts.append(str(self.rank))
        if self.adjustment > 0:
            parts.append(f'+ {self.adjustment}')
        elif self.adjustment < 0:
            parts.append(f'- {abs(self.adjustment)}')
        if self.maximum is not None:
            parts.append(f'(of {self.maximum})')
        return ' '.join(parts)

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} {self}>'

    def to_json(self):
        return {
            'name': self.name,
            'rank': self.rank,
            'adjustment': self.adjustment,
            'maximum': self.maximum,
            'human': str(self)
        }


class TableCell[V, PARSE](ABC):
    @classmethod
    @abstractmethod
    def parse(cls, data: PARSE) -> Self: ...

    @abstractmethod
    def value_for(self, rank: int, adjustment: int) -> V: ...

    @abstractmethod
    def in_bracket(self, name: str, value: int) -> StatisticBracket: ...

    @abstractmethod
    def above_bracket(self, name: str, value: int) -> StatisticBracket: ...

    @abstractmethod
    def below_bracket(self, name: str, value: int) -> StatisticBracket: ...

    @classmethod
    def _between_brackets_helper(cls, lower_bound: int, lower_name: str,
                            upper_bound: int, upper_name: str,
                            value: int) -> StatisticBracket:
        diff_lower = value - lower_bound
        diff_upper = upper_bound - value
        maximum = upper_bound - lower_bound - 1
        if abs(diff_upper) < abs(diff_lower):
            return StatisticBracket(upper_name, adjustment=-diff_upper, maximum=maximum)
        elif abs(diff_upper) == abs(diff_lower):
            return StatisticBracket(lower_name, adjustment=value - lower_bound, maximum=maximum)
        else:
            return StatisticBracket(lower_name, adjustment=diff_lower, maximum=maximum)

    @classmethod
    @abstractmethod
    def between_brackets(cls, lower: 'TableCell', lower_name: str,
                         upper: 'TableCell', upper_name: str, value: int) -> StatisticBracket: ...

    @abstractmethod
    def __contains__(self, value: int) -> bool: ...

    @abstractmethod
    def __gt__(self, value: int) -> bool: ...

    @abstractmethod
    def __lt__(self, value: int) -> bool: ...


class NumberCell(TableCell[int, int | tuple[int, int]]):
    def __init__(self, low: int, high: int | None = None) -> None:
        self.low = low
        self.high = high if high is not None else low

    @classmethod
    def parse(cls, data):
        match data:
            case int():
                return NumberCell(data)
            case tuple():
                return NumberCell(*data)

    def value_for(self, rank: int, adjustment: int) -> int:
        if adjustment > 0:
            return self.high + adjustment
        elif adjustment < 0:
            return self.low + adjustment
        else:  # self.adjustment == 0
            return self.low + rank - 1  # Rank 1 is +0

    def in_bracket(self, name: str, value: int) -> StatisticBracket:
        if self.high == self.low:
            return StatisticBracket(name)
        return StatisticBracket(name, rank=value - self.low + 1, maximum=self.high - self.low + 1)

    def above_bracket(self, name: str, value: int) -> StatisticBracket:
        return StatisticBracket(name, adjustment=value - self.high)

    def below_bracket(self, name: str, value: int) -> StatisticBracket:
        return StatisticBracket(name, adjustment=-(self.low - value))

    @classmethod
    def between_brackets(cls, lower: TableCell, lower_name: str, upper: TableCell, upper_name: str,
                         value: int) -> StatisticBracket:
        assert isinstance(lower, NumberCell) and isinstance(upper, NumberCell)
        return cls._between_brackets_helper(
            lower.high, lower_name,
            upper.low, upper_name,
            value
        )

    def __contains__(self, value: int) -> bool:
        return self.low <= value <= self.high

    def __eq__(self, value: object) -> bool:
        match value:
            case int():
                return self.high == self.low == value
            case _:
                return super().__eq__(value)

    def __gt__(self, value: int) -> bool:
        return self.low > value

    def __lt__(self, value: int) -> bool:
        return self.high < value

    def __str__(self) -> str:
        if self.low == self.high:
            return f'NumberCell({self.low})'
        return f'NumberCell({self.low} to {self.high})'

    def __repr__(self):
        return self.__str__()


class DiceCell(TableCell[SimpleDice, SimpleDice]):
    def __init__(self, dice: SimpleDice):
        self.dice = dice
        self.average = math.floor(self.dice.average())

    @classmethod
    def parse(cls, data):
        return DiceCell(data)

    def value_for(self, rank: int, adjustment: int) -> SimpleDice:
        if adjustment != 0:
            return self.dice + adjustment
        else:  # self.adjustment == 0
            return self.dice + rank - 1  # Rank 1 is +0

    def in_bracket(self, name: str, value: int) -> StatisticBracket:
        return StatisticBracket(name)

    def above_bracket(self, name: str, value: int) -> StatisticBracket:
        return StatisticBracket(name, adjustment=value - self.average)

    def below_bracket(self, name: str, value: int) -> StatisticBracket:
        return StatisticBracket(name, adjustment=value - self.average)

    @classmethod
    def between_brackets(cls, lower: TableCell, lower_name: str,
                         upper: TableCell, upper_name: str, value: int) -> StatisticBracket:
        assert isinstance(lower, DiceCell) and isinstance(upper, DiceCell)
        return cls._between_brackets_helper(
            lower.average, lower_name,
            upper.average, upper_name,
            value)

    def __contains__(self, value: int) -> bool:
        return value == self.average

    def __gt__(self, value: int) -> bool:
        return self.average > value

    def __lt__(self, value: int) -> bool:
        return self.average < value

    def __str__(self) -> str:
        return f'DiceCell({self.dice})'

    def __repr__(self):
        return self.__str__()


class Table[E](ABC):
    name: str
    brackets: list[str]
    rows: list[list[TableCell]]
    cell_type: type[TableCell]

    def __init__[F](self, name: str, cell_type: type[TableCell[E, F]],
                 brackets: list[str], rows: list[list[F]]):
        assert len({len(row) for row in rows}) == 1, \
            'all rows must be the same length'
        assert len(brackets) == len(rows[0]), \
            'brackets length must match lengths of rows'
        self.name = name
        self.cell_type = cell_type
        self.brackets = brackets
        self.rows = [
            [cell_type.parse(cell) for cell in row] for row in rows
        ]

    def classify(self, level: int, value: int) -> StatisticBracket:
        row = self.rows[level + 1]
        thresholds = itertools.pairwise(zip(self.brackets, row))

        for (upper_name, upper), (lower_name, lower) in thresholds:
            if value in upper:
                return upper.in_bracket(upper_name, value)
            elif value in lower:
                return lower.in_bracket(lower_name, value)
            elif lower < value < upper:
                return self.cell_type.between_brackets(lower, lower_name,
                                                          upper, upper_name, value)
        if len(row) > 1:
            [highest, *_, lowest] = row
            if value < lowest:
                return lowest.below_bracket(self.brackets[-1], value)
            if value > highest:
                return highest.above_bracket(self.brackets[0], value)
        else:
            singleton, bracket = row[0], self.brackets[0]
            if value < singleton:
                return singleton.below_bracket(bracket, value)
            elif value > singleton:
                return singleton.above_bracket(self.brackets[0], value)
            else:
                return singleton.in_bracket(self.brackets[0], value)
        cell_str = ', '.join(str(cell) for cell in row)
        raise ValueError(f'Cannot classify {value} for level {level} thresholds: {cell_str}')

    def lookup(self, level: int, bracket: StatisticBracket) -> E:
        row: list[TableCell[E, Any]] = self.rows[level + 1]  # -1 is row 0
        try:
            cell = row[self.brackets.index(bracket.name)]
            return cell.value_for(bracket.rank, bracket.adjustment)
        except ValueError:
            raise ValueError(f'No {bracket.name} bracket exists in this table. '
                             f'Brackets: {self.brackets}')

    def __getitem__(self, key: tuple[int, StatisticBracket]):
        return self.lookup(*key)


TERRIBLE = StatisticBracket('Terrible')
LOW = StatisticBracket('Low')
MODERATE = StatisticBracket('Moderate')
HIGH = StatisticBracket('High')
EXTREME = StatisticBracket('Extreme')

_STATISTIC_ID = itertools.count(1)


def inline_html(text: str, table: str, **data_attrs: str):
    return Tag('span', text=text, attrs={
        'class': 'statistic',
        'data-table': table,
        'id': f'statistic-{table}-{next(_STATISTIC_ID)}',
        **{f'data-{k.replace('_', '-')}': v for k, v in data_attrs.items()}
    })
