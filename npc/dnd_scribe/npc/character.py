from typing import Literal, TypeAlias

Sex: TypeAlias = Literal['Male', 'Female']
SEXES: list[Sex] = ['Male', 'Female']

Ability: TypeAlias = Literal['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
ABILITIES: list[Ability] = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
