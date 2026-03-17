from abc import ABC, abstractmethod
from typing import Callable, Mapping

from ttrpg_scribe.pf2e_compendium.actor import Save


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

    @property
    @abstractmethod
    def ac(self) -> int:
        ...

    @ac.setter
    def ac(self, ac: int):
        ...

    @property
    @abstractmethod
    def saves(self) -> Mapping[Save, int | None]:
        ...

    @abstractmethod
    def set_save(self, save: Save, value: int):
        ...

    @property
    @abstractmethod
    def max_hp(self) -> int:
        ...

    @max_hp.setter
    def max_hp(self, hp: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        if rename:
            self.name = f'{name.title()} {self.name}'
        starting_level = self.level
        self.level += level_delta(starting_level)
        # Increase AC and DCs
        self.ac += mod_delta
        # adapter.apply(adjust_all_dcs(adjustment.mod_delta))
        # # Increase attack bonus & damage
        # for action in adapter.iter_actions():
        #     match action:
        #         case Strike():
        #             action.bonus += adjustment.mod_delta
        #             # Some strikes do no damage
        #             if len(action.damage) > 0:
        #                 # Only boost the main/first damage type
        #                 amount, damage_type = action.damage[0]
        #                 action.damage[0] = amount + adjustment.mod_delta, damage_type
        for save in self.saves:
            if (value := self.saves[save]) is not None:  # Hazard saves can be None
                self.set_save(save, value + mod_delta)
        # Adjust hp
        self.max_hp += hp_delta(starting_level)
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
    @property
    @abstractmethod
    def perception(self) -> int:
        ...

    @perception.setter
    def perception(self, perception: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        super().apply(name, level_delta, mod_delta, hp_delta, rename)
        self.perception += mod_delta
        # for skill in self.skills.values():
        #    skill.mod += adjustment.mod_delta

        # for casting in creature.spellcasting:
        #     casting.attack += adjustment.mod_delta  # Increase attack bonus
        #     casting.dc += adjustment.mod_delta  # Increase DC
        return self.obj


class HazardAdjuster[T](Adjuster[T]):
    @property
    @abstractmethod
    def stealth(self) -> int:
        ...

    @stealth.setter
    def stealth(self, stealth: int):
        ...

    def apply(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
              hp_delta: Callable[[int], int], rename: bool) -> T:
        super().apply(name, level_delta, mod_delta, hp_delta, rename)
        self.stealth += mod_delta
        return self.obj
