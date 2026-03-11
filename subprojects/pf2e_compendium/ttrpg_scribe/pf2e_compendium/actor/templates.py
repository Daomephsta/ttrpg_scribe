import itertools
import re
from typing import Callable, Iterable, overload

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.actor import PF2Actor
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


class _Adjustment:
    def __init__(self, name: str, level_delta: Callable[[int], int], mod_delta: int,
                 hp_delta: Callable[[int], int]) -> None:
        self.name = name
        self.level_delta = level_delta
        self.mod_delta = mod_delta
        self.hp_delta = hp_delta

    # Backwards compat so `apply(elite)` is equivalent to `apply(elite())``
    @overload
    def __call__(self, actor: PF2Actor) -> None:
        ...

    @overload
    def __call__(self, rename: bool) -> PF2Actor.Template:
        ...

    def __call__(self, *args, **kwargs) -> PF2Actor.Template | None:
        def adjust_actor(actor: PF2Actor):
            if kwargs.get('rename', True):
                actor.name = f'{self.name.title()} {actor.name}'
            starting_level = actor.level
            actor.level += self.level_delta(starting_level)
            # Increase AC and DCs
            actor.apply(adjust_all_dcs(self.mod_delta))
            # Increase attack bonus & damage
            for action in iter_actions(actor):
                match action:
                    case Strike():
                        action.bonus += self.mod_delta
                        # Some strikes do no damage
                        if len(action.damage) > 0:
                            # Only boost the main/first damage type
                            amount, damage_type = action.damage[0]
                            action.damage[0] = amount + self.mod_delta, damage_type
            for save in actor.saves:
                if actor.saves[save] is not None:  # Hazard saves can be None
                    actor.saves[save] += self.mod_delta
            # Adjust hp
            actor.max_hp += self.hp_delta(starting_level)

        def adjust_creature(creature: PF2Creature):
            adjust_actor(creature)
            creature.perception += self.mod_delta
            for skill in creature.skills.values():
                skill.mod += self.mod_delta

            for casting in creature.spellcasting:
                casting.attack += self.mod_delta  # Increase attack bonus
                casting.dc += self.mod_delta  # Increase DC

        def adjust_hazard(hazard: PF2Hazard):
            adjust_actor(hazard)
            hazard.stealth.value += self.mod_delta

        def adjust(actor: PF2Actor):
            match actor:
                case PF2Creature():
                    return adjust_creature(actor)
                case PF2Hazard():
                    return adjust_hazard(actor)
                case _:
                    raise ValueError(f'Unknown actor type {type(actor)}')

        match args, kwargs:
            case [PF2Creature() as creature], {}:
                return adjust_creature(creature)
            case [PF2Hazard() as hazard], {}:
                return adjust_hazard(hazard)
            case [], {'rename': _}:
                return adjust
            case _:
                raise ValueError(f'Unexpected {args=} {kwargs=}')


elite = _Adjustment(
    'elite',
    level_delta=lambda level: 1 if level > 0 else 2,
    mod_delta=2,
    hp_delta=lambda level: (10 if level <= 1 else
                            15 if 2 <= level <= 4 else
                            20 if 5 <= level <= 19 else
                            30)
)

weak = _Adjustment(
    'weak',
    level_delta=lambda level: -1 if level != 1 else -2,
    mod_delta=-2,
    hp_delta=lambda level: (-10 if level <= 2 else
                            -15 if 3 <= level <= 5 else
                            -20 if 6 <= level <= 20 else
                            -30)
)
