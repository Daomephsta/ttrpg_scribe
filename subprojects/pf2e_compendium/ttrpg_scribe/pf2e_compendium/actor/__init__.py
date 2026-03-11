from dataclasses import dataclass
from typing import Callable, Literal

type Saves[V] = dict[Literal['fortitude', 'reflex', 'will'], V]


class PF2Actor:
    name: str
    level: int
    rarity: str
    traits: list[str]
    ac: int
    saves: Saves[int]
    hardness: int
    max_hp: int

    type GenericTemplate[T] = Callable[[T], None]
    type Template = GenericTemplate['PF2Actor']

    def apply(self, *templates: Template):
        for template in templates:
            template(self)
        return self


@dataclass
class DetailedValue[T]:
    value: T
    details: str
