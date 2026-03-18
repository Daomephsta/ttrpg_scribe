import itertools
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Self

from ttrpg_scribe.core.dice import SimpleDice, d


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
        highest, *_, lowest = row
        if value < lowest:
            return lowest.below_bracket(self.brackets[-1], value)
        if value > highest:
            return highest.above_bracket(self.brackets[0], value)
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

ATTRIBUTE_MODIFIERS = Table('ATTRIBUTE_MODIFIERS', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low'],
    [  # E   H   M  L
        [4,  3,  2, 0],  # -1
        [4,  3,  2, 0],  # 00
        [5,  4,  3, 1],  # 01
        [5,  4,  3, 1],  # 02
        [5,  4,  3, 1],  # 03
        [6,  5,  3, 2],  # 04
        [6,  5,  4, 2],  # 05
        [7,  5,  4, 2],  # 06
        [7,  6,  4, 2],  # 07
        [7,  6,  4, 3],  # 08
        [7,  6,  4, 3],  # 09
        [8,  7,  5, 3],  # 10
        [8,  7,  5, 3],  # 11
        [8,  7,  5, 4],  # 12
        [9,  8,  5, 4],  # 13
        [9,  8,  5, 4],  # 14
        [9,  8,  6, 4],  # 15
        [10, 9,  6, 5],  # 16
        [10, 9,  6, 5],  # 17
        [10, 9,  6, 5],  # 18
        [11, 10, 6, 5],  # 19
        [11, 10, 7, 6],  # 20
        [11, 10, 7, 6],  # 21
        [11, 10, 8, 6],  # 22
        [11, 10, 8, 6],  # 23
        [13, 12, 9, 7],  # 24
    ])

PERCEPTION = Table('PERCEPTION', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low', 'Terrible'],
    [   # E    H    M    L    T
        [+9,  +8,  +5,  +2,  +0],   # -1
        [+10, +9,  +6,  +3,  +1],   # 00
        [+11, +10, +7,  +4,  +2],   # 01
        [+12, +11, +8,  +5,  +3],   # 02
        [+14, +12, +9,  +6,  +4],   # 03
        [+15, +14, +11, +8,  +6],   # 04
        [+17, +15, +12, +9,  +7],   # 05
        [+18, +17, +14, +11, +8],   # 06
        [+20, +18, +15, +12, +10],  # 07
        [+21, +19, +16, +13, +11],  # 08
        [+23, +21, +18, +15, +12],  # 09
        [+24, +22, +19, +16, +14],  # 10
        [+26, +24, +21, +18, +15],  # 11
        [+27, +25, +22, +19, +16],  # 12
        [+29, +26, +23, +20, +18],  # 13
        [+30, +28, +25, +22, +19],  # 14
        [+32, +29, +26, +23, +20],  # 15
        [+33, +30, +28, +25, +22],  # 16
        [+35, +32, +29, +26, +23],  # 17
        [+36, +33, +30, +27, +24],  # 18
        [+38, +35, +32, +29, +26],  # 19
        [+39, +36, +33, +30, +27],  # 20
        [+41, +38, +35, +32, +28],  # 21
        [+43, +39, +36, +33, +30],  # 22
        [+44, +40, +37, +34, +31],  # 23
        [+46, +42, +38, +36, +32],  # 24
    ])

SKILLS = Table('SKILLS', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low'],
    [   # E    H    M       L
        [+8,  +5,  +4,  (+1,  +2)],   # -1
        [+9,  +6,  +5,  (+2,  +3)],   # 00
        [+10, +7,  +6,  (+3,  +4)],   # 01
        [+11, +8,  +7,  (+4,  +5)],   # 02
        [+13, +10, +9,  (+5,  +7)],   # 03
        [+15, +12, +10, (+7,  +8)],   # 04
        [+16, +13, +12, (+8,  +10)],  # 05
        [+18, +15, +13, (+9,  +11)],  # 06
        [+20, +17, +15, (+11, +13)],  # 07
        [+21, +18, +16, (+12, +14)],  # 08
        [+23, +20, +18, (+13, +16)],  # 09
        [+25, +22, +19, (+15, +17)],  # 10
        [+26, +23, +21, (+16, +19)],  # 11
        [+28, +25, +22, (+17, +20)],  # 12
        [+30, +27, +24, (+19, +22)],  # 13
        [+31, +28, +25, (+20, +23)],  # 14
        [+33, +30, +27, (+21, +25)],  # 15
        [+35, +32, +28, (+23, +26)],  # 16
        [+36, +33, +30, (+24, +28)],  # 17
        [+38, +35, +31, (+25, +29)],  # 18
        [+40, +37, +33, (+27, +31)],  # 19
        [+41, +38, +34, (+28, +32)],  # 20
        [+43, +40, +36, (+29, +34)],  # 21
        [+45, +42, +37, (+31, +35)],  # 22
        [+46, +43, +38, (+32, +36)],  # 23
        [+48, +45, +40, (+33, +38)],  # 24
    ])

ARMOR_CLASS = Table('ARMOR_CLASS', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low'],
    [  # E   H   M   L
        [18, 15, 14, 12],  # -1
        [19, 16, 15, 13],  # 00
        [19, 16, 15, 13],  # 01
        [21, 18, 17, 15],  # 02
        [22, 19, 18, 16],  # 03
        [24, 21, 20, 18],  # 04
        [25, 22, 21, 19],  # 05
        [27, 24, 23, 21],  # 06
        [28, 25, 24, 22],  # 07
        [30, 27, 26, 24],  # 08
        [31, 28, 27, 25],  # 09
        [33, 30, 29, 27],  # 10
        [34, 31, 30, 28],  # 11
        [36, 33, 32, 30],  # 12
        [37, 34, 33, 31],  # 13
        [39, 36, 35, 33],  # 14
        [40, 37, 36, 34],  # 15
        [42, 39, 38, 36],  # 16
        [43, 40, 39, 37],  # 17
        [45, 42, 41, 39],  # 18
        [46, 43, 42, 40],  # 19
        [48, 45, 44, 42],  # 20
        [49, 46, 45, 43],  # 21
        [51, 48, 47, 45],  # 22
        [52, 49, 48, 46],  # 23
        [54, 51, 50, 48],  # 24
    ])

SAVING_THROWS = Table('SAVING_THROWS', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low', 'Terrible'],
    [   # E    H    M    L    T
        [+9,  +8,  +5,  +2,  +0],   # -1
        [+10, +9,  +6,  +3,  +1],   # 00
        [+11, +10, +7,  +4,  +2],   # 01
        [+12, +11, +8,  +5,  +3],   # 02
        [+14, +12, +9,  +6,  +4],   # 03
        [+15, +14, +11, +8,  +6],   # 04
        [+17, +15, +12, +9,  +7],   # 05
        [+18, +17, +14, +11, +8],   # 06
        [+20, +18, +15, +12, +10],  # 07
        [+21, +19, +16, +13, +11],  # 08
        [+23, +21, +18, +15, +12],  # 09
        [+24, +22, +19, +16, +14],  # 10
        [+26, +24, +21, +18, +15],  # 11
        [+27, +25, +22, +19, +16],  # 12
        [+29, +26, +23, +20, +18],  # 13
        [+30, +28, +25, +22, +19],  # 14
        [+32, +29, +26, +23, +20],  # 15
        [+33, +30, +28, +25, +22],  # 16
        [+35, +32, +29, +26, +23],  # 17
        [+36, +33, +30, +27, +24],  # 18
        [+38, +35, +32, +29, +26],  # 19
        [+39, +36, +33, +30, +27],  # 20
        [+41, +38, +35, +32, +28],  # 21
        [+43, +39, +36, +33, +30],  # 22
        [+44, +40, +37, +34, +31],  # 23
        [+46, +42, +38, +36, +32],  # 24
    ])

HIT_POINTS = Table('HIT_POINTS', NumberCell,
    ['High', 'Moderate', 'Low'],
    [       # H             M             L
         [+9,          (+7,   +8),   (+5,   +6)],    # -1
        [(+17,  +20),  (+14,  +16),  (+11,  +13)],   # 00
        [(+24,  +26),  (+19,  +21),  (+14,  +16)],   # 01
        [(+36,  +40),  (+28,  +32),  (+21,  +25)],   # 02
        [(+53,  +59),  (+42,  +48),  (+31,  +37)],   # 03
        [(+72,  +78),  (+57,  +63),  (+42,  +48)],   # 04
        [(+91,  +97),  (+72,  +78),  (+53,  +59)],   # 05
        [(+115, +123), (+91,  +99),  (+67,  +75)],   # 06
        [(+140, +148), (+111, +119), (+82,  +90)],   # 07
        [(+165, +173), (+131, +139), (+97,  +105)],  # 08
        [(+190, +198), (+151, +159), (+112, +120)],  # 09
        [(+215, +223), (+171, +179), (+127, +135)],  # 10
        [(+240, +248), (+191, +199), (+142, +150)],  # 11
        [(+265, +273), (+211, +219), (+157, +165)],  # 12
        [(+290, +298), (+231, +239), (+172, +180)],  # 13
        [(+315, +323), (+251, +259), (+187, +195)],  # 14
        [(+340, +348), (+271, +279), (+202, +210)],  # 15
        [(+365, +373), (+291, +299), (+217, +225)],  # 16
        [(+390, +398), (+311, +319), (+232, +240)],  # 17
        [(+415, +423), (+331, +339), (+247, +255)],  # 18
        [(+440, +448), (+351, +359), (+262, +270)],  # 19
        [(+465, +473), (+371, +379), (+277, +285)],  # 20
        [(+495, +505), (+395, +405), (+295, +305)],  # 21
        [(+532, +544), (+424, +436), (+317, +329)],  # 22
        [(+569, +581), (+454, +466), (+339, +351)],  # 23
        [(+617, +633), (+492, +508), (+367, +383)],  # 24
    ])

RESISTANCES = Table('RESISTANCES', NumberCell,
    ['High', 'Moderate', 'Low'],
    [  # H   M   L
        [1,  1,  1],   # -1
        [3,  2,  1],   # 00
        [3,  2,  2],   # 01
        [5,  3,  2],   # 02
        [6,  4,  3],   # 03
        [7,  5,  4],   # 04
        [8,  6,  4],   # 05
        [9,  7,  5],   # 06
        [10, 7,  5],   # 07
        [11, 8,  6],   # 08
        [12, 9,  6],   # 09
        [13, 10, 7],   # 10
        [14, 10, 7],   # 11
        [15, 11, 8],   # 12
        [16, 12, 8],   # 13
        [17, 13, 9],   # 14
        [18, 13, 9],   # 15
        [19, 14, 9],   # 16
        [19, 14, 10],  # 17
        [20, 15, 10],  # 18
        [21, 16, 11],  # 19
        [22, 16, 11],  # 20
        [23, 17, 12],  # 21
        [24, 18, 12],  # 22
        [25, 19, 13],  # 23
        [26, 19, 13],  # 24
    ])

WEAKNESSES = Table('WEAKNESSES', NumberCell,
    ['High', 'Moderate', 'Low'],
    [  # H   M   L
        [1,  1,  1],   # -1
        [3,  2,  1],   # 00
        [3,  2,  2],   # 01
        [5,  3,  2],   # 02
        [6,  4,  3],   # 03
        [7,  5,  4],   # 04
        [8,  6,  4],   # 05
        [9,  7,  5],   # 06
        [10, 7,  5],   # 07
        [11, 8,  6],   # 08
        [12, 9,  6],   # 09
        [13, 10, 7],   # 10
        [14, 10, 7],   # 11
        [15, 11, 8],   # 12
        [16, 12, 8],   # 13
        [17, 13, 9],   # 14
        [18, 13, 9],   # 15
        [19, 14, 9],   # 16
        [19, 14, 10],  # 17
        [20, 15, 10],  # 18
        [21, 16, 11],  # 19
        [22, 16, 11],  # 20
        [23, 17, 12],  # 21
        [24, 18, 12],  # 22
        [25, 19, 13],  # 23
        [26, 19, 13],  # 24
    ])

STRIKE_ATTACK_BONUS = Table('STRIKE_ATTACK_BONUS', NumberCell,
    ['Extreme', 'High', 'Moderate', 'Low'],
    [   # E    H    M    L
        [+10, +8,  +6,  +4],   # -1
        [+10, +8,  +6,  +4],   # 00
        [+11, +9,  +7,  +5],   # 01
        [+13, +11, +9,  +7],   # 02
        [+14, +12, +10, +8],   # 03
        [+16, +14, +12, +9],   # 04
        [+17, +15, +13, +11],  # 05
        [+19, +17, +15, +12],  # 06
        [+20, +18, +16, +13],  # 07
        [+22, +20, +18, +15],  # 08
        [+23, +21, +19, +16],  # 09
        [+25, +23, +21, +17],  # 10
        [+27, +24, +22, +19],  # 11
        [+28, +26, +24, +20],  # 12
        [+29, +27, +25, +21],  # 13
        [+31, +29, +27, +23],  # 14
        [+32, +30, +28, +24],  # 15
        [+34, +32, +30, +25],  # 16
        [+35, +33, +31, +27],  # 17
        [+37, +35, +33, +28],  # 18
        [+38, +36, +34, +29],  # 19
        [+40, +38, +36, +31],  # 20
        [+41, +39, +37, +32],  # 21
        [+43, +41, +39, +33],  # 22
        [+44, +42, +40, +35],  # 23
        [+46, +44, +42, +36],  # 24
    ])

STRIKE_DAMAGE = Table('STRIKE_DAMAGE', DiceCell,
    ['Extreme', 'High', 'Moderate', 'Low'],
    [      # E           H           M          L
          [d(6)+1,     d(4)+1,     d(4),      d(4)],     # -1
          [d(6)+3,     d(6)+2,     d(4)+2,    d(4)+1],   # 00
          [d(8)+4,     d(6)+3,     d(6)+2,    d(4)+2],   # 01
          [d(12)+4,    d(10)+4,    d(8)+4,    d(6)+3],   # 02
          [d(12)+8,    d(10)+6,    d(8)+6,    d(6)+5],   # 03
        [2*d(10)+7,  2*d(8)+5,   2*d(6)+5,  2*d(4)+4],   # 04
        [2*d(12)+7,  2*d(8)+7,   2*d(6)+6,  2*d(4)+6],   # 05
        [2*d(12)+3,  2*d(10)+9,  2*d(8)+8,  2*d(6)+6],   # 06
        [2*d(12)+1,  2*d(8)+9,   2*d(6)+8,  2*d(4)+7],   # 07
        [2*d(12)+6,  2*d(10)+2,  2*d(8)+9,  2*d(6)+8],   # 08
        [2*d(12)+8,  2*d(10)+4,  2*d(8)+2,  2*d(6)+9],   # 09
        [2*d(12)+2,  2*d(12)+4,  2*d(10)+2, 2*d(6)+1],   # 10
        [2*d(12)+4,  2*d(12)+6,  2*d(10)+3, 2*d(8)+1],   # 11
        [3*d(12)+10, 3*d(10)+5,  3*d(8)+3,  3*d(6)+1],   # 12
        [3*d(12)+3,  3*d(10)+7,  3*d(8)+5,  3*d(6)+2],   # 13
        [3*d(12)+6,  3*d(10)+9,  3*d(8)+6,  3*d(6)+4],   # 14
        [3*d(12)+8,  3*d(12)+8,  3*d(10)+5, 3*d(6)+5],   # 15
        [3*d(12)+11, 3*d(12)+9,  3*d(10)+6, 3*d(6)+6],   # 16
        [3*d(12)+4,  3*d(12)+10, 3*d(10)+7, 3*d(6)+7],   # 17
        [3*d(12)+7,  3*d(12)+2,  3*d(10)+8, 3*d(6)+8],   # 18
        [4*d(12)+11, 4*d(10)+2,  4*d(8)+8,  4*d(6)+5],   # 19
        [4*d(12)+5,  4*d(10)+4,  4*d(8)+10, 4*d(6)+6],   # 20
        [4*d(12)+7,  4*d(10)+6,  4*d(8)+2,  4*d(6)+8],   # 21
        [4*d(12)+10, 4*d(10)+8,  4*d(8)+4,  4*d(6)+9],   # 22
        [4*d(12)+12, 4*d(12)+6,  4*d(10)+2, 4*d(6)+10],  # 23
        [4*d(12)+6,  4*d(12)+8,  4*d(10)+4, 4*d(6)+3],   # 24
    ])

SPELL_DC = Table('SPELL_DC', NumberCell,
    ['Extreme', 'High', 'Moderate'],
    [  # E   H   M
        [19, 16, 13],  # -1
        [19, 16, 13],  # 00
        [20, 17, 14],  # 01
        [22, 18, 15],  # 02
        [23, 20, 17],  # 03
        [25, 21, 18],  # 04
        [26, 22, 19],  # 05
        [27, 24, 21],  # 06
        [29, 25, 22],  # 07
        [30, 26, 23],  # 08
        [32, 28, 25],  # 09
        [33, 29, 26],  # 10
        [34, 30, 27],  # 11
        [36, 32, 29],  # 12
        [37, 33, 30],  # 13
        [39, 34, 31],  # 14
        [40, 36, 33],  # 15
        [41, 37, 34],  # 16
        [43, 38, 35],  # 17
        [44, 40, 37],  # 18
        [46, 41, 38],  # 19
        [47, 42, 39],  # 20
        [48, 44, 41],  # 21
        [50, 45, 42],  # 22
        [51, 46, 43],  # 23
        [52, 48, 45],  # 24
    ])

SPELL_ATTACK_BONUS = Table('SPELL_ATTACK_BONUS', NumberCell,
    ['Extreme', 'High', 'Moderate'],
    [   # E    H    M
        [+11, +8,  +5],   # -1
        [+11, +8,  +5],   # 00
        [+12, +9,  +6],   # 01
        [+14, +10, +7],   # 02
        [+15, +12, +9],   # 03
        [+17, +13, +10],  # 04
        [+18, +14, +11],  # 05
        [+19, +16, +13],  # 06
        [+21, +17, +14],  # 07
        [+22, +18, +15],  # 08
        [+24, +20, +17],  # 09
        [+25, +21, +18],  # 10
        [+26, +22, +19],  # 11
        [+28, +24, +21],  # 12
        [+29, +25, +22],  # 13
        [+31, +26, +23],  # 14
        [+32, +28, +25],  # 15
        [+33, +29, +26],  # 16
        [+35, +30, +27],  # 17
        [+36, +32, +29],  # 18
        [+38, +33, +30],  # 19
        [+39, +34, +31],  # 20
        [+40, +36, +33],  # 21
        [+42, +37, +34],  # 22
        [+43, +38, +35],  # 23
        [+44, +40, +37],  # 24
    ])
