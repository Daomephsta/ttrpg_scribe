import itertools
import re
from typing import Callable, Iterable, Mapping, overload

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction
from ttrpg_scribe.pf2e_compendium.actor import PF2Actor, Save
from ttrpg_scribe.pf2e_compendium.actor.adjustments import Adjuster
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard


def compose[A](*templates: PF2Actor.GenericTemplate[A]) -> PF2Actor.GenericTemplate[A]:
    def composed(actor: A):
        for template in templates:
            template(actor)
    return composed


def iter_actions(actor: PF2Actor) -> Iterable[Action]:
    match actor:
        case PF2Hazard() as hazard:
            return hazard.actions
        case PF2Creature() as creature:
            return itertools.chain(creature.actions, creature.defenses,
                                      creature.interactions)
        case unknown:
            raise ValueError(f'Unknown actor type {type(unknown)}')


def map_all_text(mapper: Callable[[str], str]) -> PF2Actor.Template:
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


class PF2ActorAdjuster[A: PF2Actor](Adjuster):
    def __init__(self, actor: A) -> None:
        self.actor = actor

    @property
    def name(self) -> str:
        return self.actor.name

    @name.setter
    def name(self, name: str):
        self.actor.name = name

    @property
    def level(self) -> int:
        return self.actor.level

    @level.setter
    def level(self, level: int):
        self.actor.level = level

    @property
    def ac(self) -> int:
        return self.actor.ac

    @ac.setter
    def ac(self, ac: int):
        self.actor.ac = ac

    @property
    def saves(self) -> Mapping[Save, int | None]:
        return self.actor.saves

    def set_save(self, save: Save, value: int):
        self.actor.saves[save] = value

    @property
    def max_hp(self) -> int:
        return self.actor.max_hp

    @max_hp.setter
    def max_hp(self, hp: int):
        self.actor.max_hp = hp


class PF2CreatureAdjuster(PF2ActorAdjuster[PF2Creature], Adjuster[PF2Creature]):
    def __init__(self, creature: PF2Creature) -> None:
        super().__init__(creature)

    @property
    def perception(self) -> int:
        return self.actor.perception

    @perception.setter
    def perception(self, perception: int):
        self.actor.perception = perception


class PF2HazardAdjuster(PF2ActorAdjuster[PF2Hazard], Adjuster[PF2Hazard]):
    def __init__(self, hazard: PF2Hazard) -> None:
        super().__init__(hazard)

    @property
    def stealth(self) -> int:
        return self.actor.stealth.value

    @stealth.setter
    def stealth(self, stealth: int):
        self.actor.stealth.value = stealth


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
