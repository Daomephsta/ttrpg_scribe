from abc import ABC, abstractmethod
import itertools
import math
import re
import sys
from typing import Self


class TableCell[V](ABC):
    @classmethod
    @abstractmethod
    def parse(cls, value: str) -> Self: ...

    @abstractmethod
    def value_for(self, rank: int, adjustment: int) -> V: ...

    @abstractmethod
    def in_description(self, name: str, value: int) -> str: ...

    @abstractmethod
    def above_description(self, name: str, value: int) -> str: ...

    @abstractmethod
    def below_description(self, name: str, value: int) -> str: ...

    @classmethod
    def _between_description0(cls, lower_bound: int, lower_name: str,
                            upper_bound: int, upper_name: str,
                            value: int) -> str:
        diff_lower = value - lower_bound
        diff_upper = upper_bound - value
        if abs(diff_upper) < abs(diff_lower):
            return f'{upper_name} - {diff_upper} ' +\
                   f'(of {upper_bound - lower_bound - 1})'
        elif abs(diff_upper) == abs(diff_lower):
            return f'{lower_name} + {value - lower_bound} ' +\
                   f'(of {upper_bound - lower_bound - 1})'
        else:
            return f'{lower_name} + {diff_lower} ' +\
                   f'(of {upper_bound - lower_bound - 1})'

    @classmethod
    @abstractmethod
    def between_description(cls, lower: Self, lower_name: str,
                            upper: Self, upper_name: str,
                            value: int) -> str: ...

    @abstractmethod
    def __contains__(self, value: int) -> bool: ...

    @abstractmethod
    def __gt__(self, value: int) -> bool: ...

    @abstractmethod
    def __lt__(self, value: int) -> bool: ...


class NumberCell(TableCell[int]):
    def __init__(self, low: int, high: int | None = None) -> None:
        self.low = low
        self.high = high if high is not None else low

    @classmethod
    def parse(cls, value: str) -> Self:
        def read_single(single_value: str):
            if single_value.startswith('\u2013'):
                return -int(single_value[1:])
            if single_value == '—':
                return sys.maxsize
            return int(single_value)
        if ' to ' in value:
            [a, _, b] = value.partition(' to ')
            return cls(read_single(b), read_single(a))
        else:
            return cls(read_single(value))

    def value_for(self, rank: int, adjustment: int) -> int:
        if adjustment > 0:
            return self.high + adjustment
        elif adjustment < 0:
            return self.low + adjustment
        else:  # self.adjustment == 0
            return self.low + rank - 1  # Rank 1 is +0

    def in_description(self, name: str, value: int) -> str:
        if self.high == self.low:
            return name
        return f'{name} {value - self.low + 1} (of {self.high - self.low + 1})'

    def above_description(self, name: str, value: int) -> str:
        return f'{name} + {value - self.high}'

    def below_description(self, name: str, value: int) -> str:
        return f'{name} - {self.low - value}'

    @classmethod
    def between_description(cls, lower: Self, lower_name: str,
                            upper: Self, upper_name: str,
                            value: int) -> str:
        return cls._between_description0(
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


class Dice:
    def __init__(self, count: int, size: int, mod: int):
        self.count = count
        self.size = size
        self.mod = mod
        self.average = count * math.floor((size + 1) / 2) + mod

    def unparse(self) -> str:
        if self.mod > 0:
            return f'{self.count}d{self.size}+{self.mod}'
        if self.mod < 0:
            return f'{self.count}d{self.size}-{abs(self.mod)}'
        return f'{self.count}d{self.size}'

    def __str__(self) -> str:
        if self.mod > 0:
            return f'{self.count}d{self.size} + {self.mod}'
        if self.mod < 0:
            return f'{self.count}d{self.size} - {abs(self.mod)}'
        return f'{self.count}d{self.size}'


class DiceCell(TableCell[str]):
    def __init__(self, count: int, size: int, mod: int):
        self.dice = Dice(count, size, mod)
        self.average = count * math.floor((size + 1) / 2) + mod

    @classmethod
    def parse(cls, value: str) -> Self:
        result = re.fullmatch(r'(?P<count>\d+)d(?P<size>\d+)(?P<mod>[+-]\d+)? \(\d+\)', value)
        if result is None:
            raise ValueError(f'Cannot parse {value}')
        groups = result.groupdict()
        return cls(
            int(groups['count'] or '1'),
            int(groups['size']),
            int(groups['mod'] or '0')
        )

    def value_for(self, rank: int, adjustment: int) -> str:
        if adjustment != 0:
            mod = self.dice.mod + adjustment
        else:  # self.adjustment == 0
            mod = self.dice.mod + rank - 1  # Rank 1 is +0
        return Dice(self.dice.count, self.dice.size, mod).unparse()

    def in_description(self, name: str, value: int) -> str:
        return name

    def above_description(self, name: str, value: int) -> str:
        return f'{name} + {value - self.average}'

    def below_description(self, name: str, value: int) -> str:
        return f'{name} - {self.average - value}'

    @classmethod
    def between_description(cls, lower: Self, lower_name: str,
                            upper: Self, upper_name: str,
                            value: int) -> str:
        return cls._between_description0(
            lower.average, lower_name,
            upper.average, upper_name,
            value
            )

    def __contains__(self, value: int) -> bool:
        return value == self.average

    def __gt__(self, value: int) -> bool:
        return self.average > value

    def __lt__(self, value: int) -> bool:
        return self.average < value

    def __str__(self) -> str:
        return f'DiceCell({self.dice})'


class Table[C: TableCell](ABC):
    brackets: list[str]
    rows: list[list[C]]
    cell_type: type[C]

    def __init__(self, cell_type: type[C], table: str):
        self.cell_type = cell_type
        header, *rows = table.splitlines()
        level, *self.brackets = re.split(r'\s+', header)

        def read_row(row: str):
            level, *values = row.split('\t')
            return [cell_type.parse(value) for value in values]

        self.rows = [read_row(row) for row in rows]

    def classify(self, level: int, value: int) -> str:
        row = self.rows[level + 1]
        thresholds = itertools.pairwise(zip(self.brackets, row))

        for (upper_name, upper), (lower_name, lower) in thresholds:
            if value in upper:
                return upper.in_description(upper_name, value)
            elif value in lower:
                return lower.in_description(lower_name, value)
            elif lower < value < upper:
                return self.cell_type.between_description(lower, lower_name,
                                                          upper, upper_name, value)
        highest, *_, lowest = row
        if value < lowest:
            return lowest.below_description(self.brackets[-1], value)
        if value > highest:
            return highest.above_description(self.brackets[0], value)
        cell_str = ', '.join(str(cell) for cell in row)
        raise ValueError(f'Cannot classify {value} for level {level} thresholds: {cell_str}')

    def cell_for(self, level: int, bracket: str):
        row = self.rows[level + 1]  # -1 is row 0
        try:
            return row[self.brackets.index(bracket)]
        except ValueError:
            raise ValueError(f'No {bracket} bracket exists in this table. '
                             f'Brackets: {self.brackets}')


class StatisticBracket:
    def __init__(self, bracket: str, rank=1, adjustment=0) -> None:
        self.bracket = bracket
        self.rank = rank
        self.adjustment = adjustment

    def __call__(self, rank: int):
        return StatisticBracket(self.bracket, rank, self.adjustment)

    def __add__(self, bonus: int):
        return StatisticBracket(self.bracket, self.rank, self.adjustment + bonus)

    def __sub__(self, penalty: int):
        return StatisticBracket(self.bracket, self.rank, self.adjustment - penalty)

    def lookup[C: TableCell](self, table: Table[C], level: int):
        return table.cell_for(level, self.bracket).value_for(self.rank, self.adjustment)

    def attribute(self, level: int):
        return self.lookup(ATTRIBUTE_MODIFIERS, level)


TERRIBLE = StatisticBracket('Terrible')
LOW = StatisticBracket('Low')
MODERATE = StatisticBracket('Moderate')
HIGH = StatisticBracket('High')
EXTREME = StatisticBracket('Extreme')


ATTRIBUTE_MODIFIERS = Table(NumberCell, '''Level	Extreme	High	Moderate	Low
-1	—	+3	+2	+0
0	—	+3	+2	+0
1	+5	+4	+3	+1
2	+5	+4	+3	+1
3	+5	+4	+3	+1
4	+6	+5	+3	+2
5	+6	+5	+4	+2
6	+7	+5	+4	+2
7	+7	+6	+4	+2
8	+7	+6	+4	+3
9	+7	+6	+4	+3
10	+8	+7	+5	+3
11	+8	+7	+5	+3
12	+8	+7	+5	+4
13	+9	+8	+5	+4
14	+9	+8	+5	+4
15	+9	+8	+6	+4
16	+10	+9	+6	+5
17	+10	+9	+6	+5
18	+10	+9	+6	+5
19	+11	+10	+6	+5
20	+11	+10	+7	+6
21	+11	+10	+7	+6
22	+11	+10	+8	+6
23	+11	+10	+8	+6
24	+13	+12	+9	+7''')

PERCEPTION = Table(NumberCell, '''Level	Extreme	High	Moderate	Low	Terrible
-1	+9	+8	+5	+2	+0
0	+10	+9	+6	+3	+1
1	+11	+10	+7	+4	+2
2	+12	+11	+8	+5	+3
3	+14	+12	+9	+6	+4
4	+15	+14	+11	+8	+6
5	+17	+15	+12	+9	+7
6	+18	+17	+14	+11	+8
7	+20	+18	+15	+12	+10
8	+21	+19	+16	+13	+11
9	+23	+21	+18	+15	+12
10	+24	+22	+19	+16	+14
11	+26	+24	+21	+18	+15
12	+27	+25	+22	+19	+16
13	+29	+26	+23	+20	+18
14	+30	+28	+25	+22	+19
15	+32	+29	+26	+23	+20
16	+33	+30	+28	+25	+22
17	+35	+32	+29	+26	+23
18	+36	+33	+30	+27	+24
19	+38	+35	+32	+29	+26
20	+39	+36	+33	+30	+27
21	+41	+38	+35	+32	+28
22	+43	+39	+36	+33	+30
23	+44	+40	+37	+34	+31
24	+46	+42	+38	+36	+32''')

SKILLS = Table(NumberCell, '''Level	Extreme	High	Moderate	Low
-1	+8	+5	+4	+2 to +1
0	+9	+6	+5	+3 to +2
1	+10	+7	+6	+4 to +3
2	+11	+8	+7	+5 to +4
3	+13	+10	+9	+7 to +5
4	+15	+12	+10	+8 to +7
5	+16	+13	+12	+10 to +8
6	+18	+15	+13	+11 to +9
7	+20	+17	+15	+13 to +11
8	+21	+18	+16	+14 to +12
9	+23	+20	+18	+16 to +13
10	+25	+22	+19	+17 to +15
11	+26	+23	+21	+19 to +16
12	+28	+25	+22	+20 to +17
13	+30	+27	+24	+22 to +19
14	+31	+28	+25	+23 to +20
15	+33	+30	+27	+25 to +21
16	+35	+32	+28	+26 to +23
17	+36	+33	+30	+28 to +24
18	+38	+35	+31	+29 to +25
19	+40	+37	+33	+31 to +27
20	+41	+38	+34	+32 to +28
21	+43	+40	+36	+34 to +29
22	+45	+42	+37	+35 to +31
23	+46	+43	+38	+36 to +32
24	+48	+45	+40	+38 to +33''')

ARMOR_CLASS = Table(NumberCell, '''Level	Extreme	High	Moderate	Low
-1	18	15	14	12
0	19	16	15	13
1	19	16	15	13
2	21	18	17	15
3	22	19	18	16
4	24	21	20	18
5	25	22	21	19
6	27	24	23	21
7	28	25	24	22
8	30	27	26	24
9	31	28	27	25
10	33	30	29	27
11	34	31	30	28
12	36	33	32	30
13	37	34	33	31
14	39	36	35	33
15	40	37	36	34
16	42	39	38	36
17	43	40	39	37
18	45	42	41	39
19	46	43	42	40
20	48	45	44	42
21	49	46	45	43
22	51	48	47	45
23	52	49	48	46
24	54	51	50	48''')

SAVING_THROWS = Table(NumberCell, '''Level	Extreme	High	Moderate	Low	Terrible
-1	+9	+8	+5	+2	+0
0	+10	+9	+6	+3	+1
1	+11	+10	+7	+4	+2
2	+12	+11	+8	+5	+3
3	+14	+12	+9	+6	+4
4	+15	+14	+11	+8	+6
5	+17	+15	+12	+9	+7
6	+18	+17	+14	+11	+8
7	+20	+18	+15	+12	+10
8	+21	+19	+16	+13	+11
9	+23	+21	+18	+15	+12
10	+24	+22	+19	+16	+14
11	+26	+24	+21	+18	+15
12	+27	+25	+22	+19	+16
13	+29	+26	+23	+20	+18
14	+30	+28	+25	+22	+19
15	+32	+29	+26	+23	+20
16	+33	+30	+28	+25	+22
17	+35	+32	+29	+26	+23
18	+36	+33	+30	+27	+24
19	+38	+35	+32	+29	+26
20	+39	+36	+33	+30	+27
21	+41	+38	+35	+32	+28
22	+43	+39	+36	+33	+30
23	+44	+40	+37	+34	+31
24	+46	+42	+38	+36	+32''')

HIT_POINTS = Table(NumberCell, '''Level	High	Moderate	Low
-1	9	8 to 7	6 to 5
0	20 to 17	16 to 14	13 to 11
1	26 to 24	21 to 19	16 to 14
2	40 to 36	32 to 28	25 to 21
3	59 to 53	48 to 42	37 to 31
4	78 to 72	63 to 57	48 to 42
5	97 to 91	78 to 72	59 to 53
6	123 to 115	99 to 91	75 to 67
7	148 to 140	119 to 111	90 to 82
8	173 to 165	139 to 131	105 to 97
9	198 to 190	159 to 151	120 to 112
10	223 to 215	179 to 171	135 to 127
11	248 to 240	199 to 191	150 to 142
12	273 to 265	219 to 211	165 to 157
13	298 to 290	239 to 231	180 to 172
14	323 to 315	259 to 251	195 to 187
15	348 to 340	279 to 271	210 to 202
16	373 to 365	299 to 291	225 to 217
17	398 to 390	319 to 311	240 to 232
18	423 to 415	339 to 331	255 to 247
19	448 to 440	359 to 351	270 to 262
20	473 to 465	379 to 371	285 to 277
21	505 to 495	405 to 395	305 to 295
22	544 to 532	436 to 424	329 to 317
23	581 to 569	466 to 454	351 to 339
24	633 to 617	508 to 492	383 to 367''')

STRIKE_ATTACK_BONUS = Table(NumberCell, '''Level	Extreme	High	Moderate	Low
-1	+10	+8	+6	+4
0	+10	+8	+6	+4
1	+11	+9	+7	+5
2	+13	+11	+9	+7
3	+14	+12	+10	+8
4	+16	+14	+12	+9
5	+17	+15	+13	+11
6	+19	+17	+15	+12
7	+20	+18	+16	+13
8	+22	+20	+18	+15
9	+23	+21	+19	+16
10	+25	+23	+21	+17
11	+27	+24	+22	+19
12	+28	+26	+24	+20
13	+29	+27	+25	+21
14	+31	+29	+27	+23
15	+32	+30	+28	+24
16	+34	+32	+30	+25
17	+35	+33	+31	+27
18	+37	+35	+33	+28
19	+38	+36	+34	+29
20	+40	+38	+36	+31
21	+41	+39	+37	+32
22	+43	+41	+39	+33
23	+44	+42	+40	+35
24	+46	+44	+42	+36''')


STRIKE_DAMAGE = Table(DiceCell, '''Level	Extreme	High	Moderate	Low
-1	1d6+1 (4)	1d4+1 (3)	1d4 (3)	1d4 (2)
0	1d6+3 (6)	1d6+2 (5)	1d4+2 (4)	1d4+1 (3)
1	1d8+4 (8)	1d6+3 (6)	1d6+2 (5)	1d4+2 (4)
2	1d12+4 (11)	1d10+4 (9)	1d8+4 (8)	1d6+3 (6)
3	1d12+8 (15)	1d10+6 (12)	1d8+6 (10)	1d6+5 (8)
4	2d10+7 (18)	2d8+5 (14)	2d6+5 (12)	2d4+4 (9)
5	2d12+7 (20)	2d8+7 (16)	2d6+6 (13)	2d4+6 (11)
6	2d12+10 (23)	2d8+9 (18)	2d6+8 (15)	2d4+7 (12)
7	2d12+12 (25)	2d10+9 (20)	2d8+8 (17)	2d6+6 (13)
8	2d12+15 (28)	2d10+11 (22)	2d8+9 (18)	2d6+8 (15)
9	2d12+17 (30)	2d10+13 (24)	2d8+11 (20)	2d6+9 (16)
10	2d12+20 (33)	2d12+13 (26)	2d10+11 (22)	2d6+10 (17)
11	2d12+22 (35)	2d12+15 (28)	2d10+12 (23)	2d8+10 (19)
12	3d12+19 (38)	3d10+14 (30)	3d8+12 (25)	3d6+10 (20)
13	3d12+21 (40)	3d10+16 (32)	3d8+14 (27)	3d6+11 (21)
14	3d12+24 (43)	3d10+18 (34)	3d8+15 (28)	3d6+13 (23)
15	3d12+26 (45)	3d12+17 (36)	3d10+14 (30)	3d6+14 (24)
16	3d12+29 (48)	3d12+18 (37)	3d10+15 (31)	3d6+15 (25)
17	3d12+31 (50)	3d12+19 (38)	3d10+16 (32)	3d6+16 (26)
18	3d12+34 (53)	3d12+20 (40)	3d10+17 (33)	3d6+17 (27)
19	4d12+29 (55)	4d10+20 (42)	4d8+17 (35)	4d6+14 (28)
20	4d12+32 (58)	4d10+22 (44)	4d8+19 (37)	4d6+15 (29)
21	4d12+34 (60)	4d10+24 (46)	4d8+20 (38)	4d6+17 (31)
22	4d12+37 (63)	4d10+26 (48)	4d8+22 (40)	4d6+18 (32)
23	4d12+39 (65)	4d12+24 (50)	4d10+20 (42)	4d6+19 (33)
24	4d12+42 (68)	4d12+26 (52)	4d10+22 (44)	4d6+21 (35)''')


SPELL_DC = Table(NumberCell, '''Level Extreme High Moderate
-1	19	16	13
0	19	16	13
1	20	17	14
2	22	18	15
3	23	20	17
4	25	21	18
5	26	22	19
6	27	24	21
7	29	25	22
8	30	26	23
9	32	28	25
10	33	29	26
11	34	30	27
12	36	32	29
13	37	33	30
14	39	34	31
15	40	36	33
16	41	37	34
17	43	38	35
18	44	40	37
19	46	41	38
20	47	42	39
21	48	44	41
22	50	45	42
23	51	46	43
24	52	48	45''')


SPELL_ATTACK_BONUS = Table(NumberCell, '''Level Extreme High Moderate
-1	+11	+8	+5
0	+11	+8	+5
1	+12	+9	+6
2	+14	+10	+7
3	+15	+12	+9
4	+17	+13	+10
5	+18	+14	+11
6	+19	+16	+13
7	+21	+17	+14
8	+22	+18	+15
9	+24	+20	+17
10	+25	+21	+18
11	+26	+22	+19
12	+28	+24	+21
13	+29	+25	+22
14	+31	+26	+23
15	+32	+28	+25
16	+33	+29	+26
17	+35	+30	+27
18	+36	+32	+29
19	+38	+33	+30
20	+39	+34	+31
21	+40	+36	+33
22	+42	+37	+34
23	+43	+38	+35
24	+44	+40	+37''')
