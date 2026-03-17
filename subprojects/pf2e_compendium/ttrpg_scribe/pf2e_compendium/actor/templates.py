import itertools
import re
from abc import abstractmethod
from typing import Callable, Iterable, overload

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.actor import PF2Actor, Save
from ttrpg_scribe.pf2e_compendium.actor.adjustments import (Adjuster,
                                                            CreatureAdjuster,
                                                            HazardAdjuster)
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard


def compose[A](*templates: PF2Actor.GenericTemplate[A]) -> PF2Actor.GenericTemplate[A]:
    def composed(actor: A):
        for template in templates:
            template(actor)
    return composed


def map_all_text(mapper: Callable[[str], str]) -> PF2Actor.Template:
    def iter_actions(actor: PF2Actor) -> Iterable[Action]:
        match actor:
            case PF2Hazard() as hazard:
                return hazard.actions
            case PF2Creature() as creature:
                return itertools.chain(creature.actions, creature.defenses,
                                          creature.interactions)
            case unknown:
                raise ValueError(f'Unknown actor type {type(unknown)}')

    def template(actor: PF2Actor):
        for action in iter_actions(actor):
            match action:
                case SimpleAction():
                    action.name = mapper(action.name)
                    action.desc = mapper(action.desc)

    return template


def adjust_all_dcs(delta: int) -> PF2Actor.Template:
    def template(actor: PF2Actor):
        actor.ac += delta
        actor.apply(map_all_text(lambda s: re.sub(
            r'([AD]C) (\d+)',
            lambda match: f'{match[1]} {int(match[2]) + delta}', s)
        ))
    return template


def replace_in_all_text(*replacements: tuple[str, str]) -> PF2Actor.Template:
    def apply_replacements(target: str) -> str:
        for old, new in replacements:
            target = target.replace(old, new)
        return target
    return map_all_text(apply_replacements)


def rename(full: str, *other_names: tuple[str, str]) -> PF2Actor.Template:
    def template(actor: PF2Actor):
        name_cases = ((case(actor.name), case(full))
            for case in [str.lower, str.title, str.capitalize])
        actor.apply(replace_in_all_text(*other_names, *name_cases))
        # Change the name after, so name replacement in other text works
        actor.name = full
    return template


class PF2ActorAdjuster[A: PF2Actor](Adjuster[A]):
    @property
    def name(self) -> str:
        return self.obj.name

    @name.setter
    def name(self, name: str):
        self.obj.name = name

    @property
    def level(self) -> int:
        return self.obj.level

    @level.setter
    def level(self, level: int):
        self.obj.level = level

    def ac(self, delta: int):
        self.obj.ac += delta

    def dcs(self, delta: int):
        self.obj = self.obj.apply(adjust_all_dcs(delta))

    def saves(self, delta: int):
        self.obj.saves = {
            save: mod + delta
            for save, mod in self.obj.saves.items()
            if mod is not None
        }

    def set_save(self, save: Save, value: int):
        self.obj.saves[save] = value

    def max_hp(self, delta: int):
        self.obj.max_hp += delta

    @abstractmethod
    def iter_actions(self) -> Iterable[Action]:
        ...

    def damaging_actions(self, attack_delta: int, damage_delta: int):
        for action in self.iter_actions():
            match action:
                case Strike():
                    action.bonus += attack_delta
                    # Some strikes do no damage
                    if len(action.damage) == 0:
                        continue
                    # Only boost the main/first damage type
                    amount, damage_type = action.damage[0]
                    action.damage[0] = amount + damage_delta, damage_type


class PF2CreatureAdjuster(PF2ActorAdjuster[PF2Creature], CreatureAdjuster[PF2Creature]):
    def perception(self, delta: int):
        self.obj.perception += delta

    def skills(self, delta: int):
        for skill in self.obj.skills.values():
            skill.mod += delta

    def spellcasting(self, attack_delta: int, dc_delta: int):
        for casting in self.obj.spellcasting:
            casting.attack += attack_delta
            casting.dc += dc_delta

    def iter_actions(self) -> Iterable[Action]:
        return itertools.chain(self.obj.actions, self.obj.defenses, self.obj.interactions)


class PF2HazardAdjuster(PF2ActorAdjuster[PF2Hazard], HazardAdjuster[PF2Hazard]):
    def stealth(self, delta: int):
        self.obj.stealth.value += delta

    def iter_actions(self) -> Iterable[Action]:
        return self.obj.actions


class _Adjustment:
    def __init__(self, adjustment: Callable[[Adjuster, bool], None]) -> None:
        self.adjustment = adjustment

    # Backwards compat so `apply(elite)` is equivalent to `apply(elite())``
    @overload
    def __call__(self, actor: PF2Actor) -> None:
        ...

    @overload
    def __call__(self, *, rename: bool) -> PF2Actor.Template:
        ...

    def __call__(self, *args, **kwargs) -> PF2Actor.Template | None:
        def adjust(actor: PF2Actor) -> None:
            rename: bool = kwargs.get('rename', True)
            match actor:
                case PF2Creature():
                    self.adjustment(PF2CreatureAdjuster(actor), rename)
                case PF2Hazard():
                    self.adjustment(PF2HazardAdjuster(actor), rename)
                case _:
                    raise ValueError(f'Unknown actor type {type(actor)}')

        match args, kwargs:
            case [PF2Creature() as creature], {}:
                return adjust(creature)
            case [PF2Hazard() as hazard], {}:
                return adjust(hazard)
            case [], {'rename': _}:
                return adjust
            case _:
                raise ValueError(f'Unexpected {args=} {kwargs=}')


elite = _Adjustment(Adjuster.elite)
weak = _Adjustment(Adjuster.weak)
