from abc import ABC, abstractmethod
from typing import Callable


class Adjuster[T](ABC):
    def __init__(self, obj: T) -> None:
        self.obj: T = obj

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @name.setter
    def name(self, name: str):
        ...

    @property
    @abstractmethod
    def level(self) -> int:
        ...

    @level.setter
    def level(self, level: int):
        ...

    @abstractmethod
    def ac(self, delta: int):
        ...

    @abstractmethod
    def dcs(self, delta: int):
        ...

    @abstractmethod
    def saves(self, delta: int):
        ...

    @abstractmethod
    def max_hp(self, delta: int):
        ...

    @abstractmethod
    def damaging_actions(self, attack_delta: int, damage_delta: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        if rename:
            self.name = f'{name.title()} {self.name}'
        starting_level = self.level
        self.level += level_delta(starting_level)
        self.ac(mod_delta)
        self.dcs(mod_delta)
        self.damaging_actions(attack_delta=mod_delta, damage_delta=mod_delta)
        self.saves(mod_delta)
        self.max_hp(hp_delta(starting_level))
        return self.obj

    def elite(self, rename: bool) -> T:
        return self.apply('elite',
            level_delta=lambda level: 1 if level > 0 else 2,
            mod_delta=2,
            hp_delta=lambda level: (10 if level <= 1 else
                                    15 if 2 <= level <= 4 else
                                    20 if 5 <= level <= 19 else
                                    30),
            rename=rename)

    def weak(self, rename: bool) -> T:
        return self.apply(
            'weak',
            level_delta=lambda level: -1 if level != 1 else -2,
            mod_delta=-2,
            hp_delta=lambda level: (-10 if level <= 2 else
                                    -15 if 3 <= level <= 5 else
                                    -20 if 6 <= level <= 20 else
                                    -30),
            rename=rename)


class CreatureAdjuster[T](Adjuster[T]):
    @abstractmethod
    def perception(self, delta: int):
        ...

    @abstractmethod
    def skills(self, delta: int):
        ...

    @abstractmethod
    def spellcasting(self, attack_delta: int, dc_delta: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        super().apply(name, level_delta, mod_delta, hp_delta, rename)
        self.perception(mod_delta)
        self.skills(mod_delta)
        self.spellcasting(attack_delta=mod_delta, dc_delta=mod_delta)
        return self.obj


class HazardAdjuster[T](Adjuster[T]):
    @abstractmethod
    def stealth(self, delta: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        super().apply(name, level_delta, mod_delta, hp_delta, rename)
        self.stealth(mod_delta)
        return self.obj
