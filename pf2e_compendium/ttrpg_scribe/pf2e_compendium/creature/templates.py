from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.actions import Action


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


def rename(full: str) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.name = full
    return template


# def rename(full: str, *other_names: tuple[str, str]):
#     replacements = list(other_names)
#
#     def process(target: str) -> str:
#         for replacement in replacements:
#             target = target.replace(*replacement)
#         return target
#
#     def process_feature(x: PF2Creature.Feature):
#         match x:
#             case (n, d):
#                 return process(n), process(d)
#             case _ as template:
#                 return lambda creature: process_feature(template(creature))
#
#     def template(creature: PF2Creature):
#         for case in [str.lower, str.title]:
#             replacements.append((case(creature['name']), case(full)))
#         creature['name'] = full
#         for feature in ['traits', 'actions', 'bonus_actions', 'reactions']:
#             creature[feature] = [process_feature(x) for x in creature[feature]]
#         creature['lore'] = process(creature['lore'])
#     return template
