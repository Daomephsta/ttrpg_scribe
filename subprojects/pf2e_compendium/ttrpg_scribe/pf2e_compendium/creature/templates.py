import itertools
import re
from typing import Callable

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


def elite(creature: PF2Creature):
    creature.name = f'Elite {creature.name}'
    starting_level = creature.level
    creature.level += 1 if creature.level > 0 else 2
    # Increase AC and DCs
    creature.apply(adjust_all_dcs(2))
    # Increase attack bonus & damage
    for action in creature.actions:
        match action:
            case Strike():
                action.bonus += 2
                # Only boost the main/first damage type
                amount, damage_type = action.damage[0]
                action.damage[0] = amount + 2, damage_type

    for save in creature.saves:
        creature.saves[save] += 2
    creature.perception += 2
    for skill in creature.skills:
        skill.mod += 2
    if starting_level <= 1:
        creature.max_hp += 10
    elif 2 <= starting_level <= 4:
        creature.max_hp += 15
    elif 5 <= starting_level <= 19:
        creature.max_hp += 20
    else:
        creature.max_hp += 30


def weak(creature: PF2Creature):
    creature.name = f'Weak {creature.name}'
    starting_level = creature.level
    creature.level -= 1 if creature.level != 1 else 2
    # Decrease AC and DCs
    creature.apply(adjust_all_dcs(-2))
    # Decrease attack bonus & damage
    for action in creature.actions:
        match action:
            case Strike():
                action.bonus -= 2
                # Only reduce the main/first damage type
                amount, damage_type = action.damage[0]
                action.damage[0] = amount - 2, damage_type
    for save in creature.saves:
        creature.saves[save] -= 2
    creature.perception -= 2
    for skill in creature.skills:
        skill.mod -= 2
    if starting_level <= 2:
        creature.max_hp -= 10
    elif 3 <= starting_level <= 5:
        creature.max_hp -= 15
    elif 6 <= starting_level <= 20:
        creature.max_hp -= 20
    else:
        creature.max_hp -= 30
