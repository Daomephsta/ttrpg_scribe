import itertools
import re
from typing import Callable, overload

from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature, Sense


def compose(*templates: PF2Creature.Template) -> PF2Creature.Template:
    def composed(creature: PF2Creature):
        for template in templates:
            template(creature)
    return composed


def with_actions(*actions: Action) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions += actions
    return template


def without_actions(*action_names: str) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions = [a for a in creature.actions
                            if a.name not in action_names]
    return template


def replace_actions(actions: dict[str, Action]) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions = [actions.get(a.name, a) for a in creature.actions]
    return template


def map_all_text(mapper: Callable[[str], str]) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        for action in itertools.chain(creature.actions, creature.defenses):
            match action:
                case SimpleAction():
                    action.name = mapper(action.name)
                    action.desc = mapper(action.desc)
        creature.interactions = [(mapper(name), mapper(desc))
                                 for name, desc in creature.interactions]
    return template


def replace_in_all_text(*replacements: tuple[str, str]) -> PF2Creature.Template:
    def apply_replacements(target: str) -> str:
        for old, new in replacements:
            target = target.replace(old, new)
        return target
    return map_all_text(apply_replacements)


def rename(full: str, *other_names: tuple[str, str]) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        name_cases = ((case(creature.name), case(full))
            for case in [str.lower, str.title, str.capitalize])
        creature.apply(replace_in_all_text(*other_names, *name_cases))
        # Change the name after, so name replacement in other text works
        creature.name = full
    return template


def darkvision(creature: PF2Creature):
    for i in range(len(creature.senses)):
        if creature.senses[i].name == 'low-light-vision':
            creature.senses[i] = Sense('darkvision')
            return
    creature.senses.append(Sense('darkvision'))


def adjust_all_dcs(delta: int):
    def template(creature: PF2Creature):
        creature.ac += delta
        creature.apply(map_all_text(lambda s: re.sub(
            r'([AD]C) (\d+)',
            lambda match: f'{match[1]} {int(match[2]) + delta}', s)
        ))
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
    def __call__(self, creature: PF2Creature) -> None:
        ...

    @overload
    def __call__(self, rename: bool) -> PF2Creature.Template:
        ...

    def __call__(self, *args, **kwargs) -> PF2Creature.Template | None:
        def template(creature: PF2Creature):
            if kwargs.get('rename', True):
                creature.name = f'{self.name.title()} {creature.name}'
            starting_level = creature.level
            creature.level += self.level_delta(starting_level)
            # Increase AC and DCs
            creature.apply(adjust_all_dcs(self.mod_delta))
            # Increase attack bonus & damage
            for action in creature.actions:
                match action:
                    case Strike():
                        action.bonus += self.mod_delta
                        # Some strikes do no damage
                        if len(action.damage) > 0:
                            # Only boost the main/first damage type
                            amount, damage_type = action.damage[0]
                            action.damage[0] = amount + self.mod_delta, damage_type

            for save in creature.saves:
                creature.saves[save] += self.mod_delta
            creature.perception += self.mod_delta
            for skill in creature.skills.values():
                skill.mod += self.mod_delta
            # Adjust hp
            creature.max_hp += self.hp_delta(starting_level)

        match args, kwargs:
            case [creature], {}:
                return template(creature)
            case [], {'rename': _}:
                return template
            case _:
                raise ValueError(f'Unexpected {args=} {kwargs=}')


elite = _Adjustment(
    'elite',
    level_delta=lambda level: 1 if level > 0 else 2,
    mod_delta=-2,
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
