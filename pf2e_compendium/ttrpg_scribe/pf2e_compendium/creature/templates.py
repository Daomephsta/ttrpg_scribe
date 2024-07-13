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


def rename(full: str, *other_names: tuple[str, str]) -> PF2Creature.Template:
    replacements = list(other_names)

    def process(target: str) -> str:
        for replacement in replacements:
            target = target.replace(*replacement)
        return target

    def template(creature: PF2Creature):
        for case in [str.lower, str.title]:
            replacements.append((case(creature.name), case(full)))

        creature.name = full
        for action in creature.actions:
            match action:
                case SimpleAction():
                    action.desc = process(action.desc)
    return template
