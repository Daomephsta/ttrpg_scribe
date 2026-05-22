from abc import ABC
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator, Literal, overload

from ttrpg_scribe.pf2e_compendium.actions import Action, Strike

type Save = Literal['fortitude', 'reflex', 'will']
type Saves[V] = dict[Save, V]


class ActionsContainer(Iterable[Action]):
    def __init__(self, actions: Iterable[Action] = []) -> None:
        self._by_name: dict[str, Action] = {}
        self._names_by_group: dict[Action.Category | Strike.WeaponType, list[str]] =\
            {group: [] for group in Action.CATEGORIES + Strike.WEAPON_TYPES}
        for action in actions:
            self.add(action)

    def _group(self, action: Action) -> Action.Category | Strike.WeaponType:
        return action.weapon_type if isinstance(action, Strike) else action.category

    def add(self, action: Action):
        self._by_name[action.name] = action
        self._names_by_group[self._group(action)].append(action.name)

    def remove(self, name: str):
        action = self._by_name.pop(name)
        self._names_by_group[self._group(action)].remove(name)

    def replace(self, action: Action):
        self.remove(action.name)
        self.add(action)

    def __iter__(self) -> Iterator[Action]:
        return iter(self._by_name.values())

    @overload
    def by_group(self, group: Strike.WeaponType) -> Iterable[Strike]:
        ...

    @overload
    def by_group(self, group: Action.Category) -> Iterable[Action]:
        ...

    def by_group(self, group) -> Iterable[Action]:
        names = self._names_by_group[group]
        return (self._by_name[name] for name in names)

    def to_json(self) -> dict[str, Any]:
        return {name: action.to_json() for name, action in self._by_name.items()}

    @staticmethod
    def from_json(data: dict[str, Any]):
        return ActionsContainer(Action.from_json(action) for action in data.values())


class PF2Actor(ABC):
    name: str
    level: int
    rarity: str
    traits: list[str]
    ac: int
    saves: Saves[int]
    hardness: int
    max_hp: int
    actions: ActionsContainer

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
