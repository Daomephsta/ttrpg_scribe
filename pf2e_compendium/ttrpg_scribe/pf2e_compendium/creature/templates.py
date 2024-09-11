import itertools
from typing import Callable
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.actions import Action, SimpleAction


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
