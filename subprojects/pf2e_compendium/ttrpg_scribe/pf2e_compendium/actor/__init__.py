from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterable, Literal

from ttrpg_scribe.pf2e_compendium.actions import Action

type Save = Literal['fortitude', 'reflex', 'will']
type Saves[V] = dict[Save, V]


class PF2Actor(ABC):
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

    @abstractmethod
    def iter_actions(self) -> Iterable[Action]:
        ...


@dataclass
class DetailedValue[T]:
    value: T
    details: str
