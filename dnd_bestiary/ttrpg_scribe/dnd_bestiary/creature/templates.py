from typing import Callable, TypedDict, Unpack

from ttrpg_scribe.dnd_bestiary.creature import DndCreature, ability
from ttrpg_scribe.dnd_bestiary.creature.armour import ArmourClass


def compose(*templates: DndCreature.Template) -> DndCreature.Template:
    def composed(creature: DndCreature.TemplateArgs):
        for template in templates:
            template(creature)
    return composed


Score = int | Callable[[int], int]
Scores = TypedDict('Scores', {'str': Score, 'dex': Score, 'con': Score,
                              'int': Score, 'wis': Score, 'cha': Score}, total=False)


def scores(**values: Unpack[Scores]):
    def template(creature: DndCreature.TemplateArgs):
        def adjust_score(ability: str, current: int) -> int:
            if ability not in values:
                return current
            return values[ability] if isinstance(values[ability], int)\
                else values[ability](current)

        str_, dex, con, int_, wis, cha = creature['statistics']
        creature['statistics'] = (
            adjust_score('str', str_),
            adjust_score('dex', dex),
            adjust_score('con', con),
            adjust_score('int', int_),
            adjust_score('wis', wis),
            adjust_score('cha', cha),
        )
    return template


def bonus(modifier: int, limit: int = 20) -> Callable[[int], int]:
    return lambda value: min(value + modifier, limit)


def malus(modifier: int, fallback: int = 0) -> Callable[[int], int]:
    return lambda value: max(max(fallback, 0), value + modifier)


def armour(base_ac: int, reason: str, dex_limit: int = 10):
    def template_factory(shield: bool = False):
        def template(args: DndCreature.TemplateArgs):
            ac = base_ac + min(dex_limit, ability.mod(args['statistics'][1]))
            if shield:
                ac += 2
                args['ac'] = [ArmourClass(ac, f'{{ac:d}} ({reason}, shield)')]
            else:
                args['ac'] = [ArmourClass(ac, f'{{ac:d}} ({reason})')]
        return template
    return template_factory


# Light armour
padded_armour = armour(11, 'padded')
leather_armour = armour(11, 'leather')
studded_leather_armour = armour(12, 'studded leather')

# Medium armour
hide_armour = armour(12, 'hide')
chain_shirt_armour = armour(13, 'chain shirt', dex_limit=2)
scale_mail_armour = armour(14, 'scale mail', dex_limit=2)
breastplate_armour = armour(14, 'breastplate', dex_limit=2)
half_plate_armour = armour(15, 'half plate', dex_limit=2)

# Heavy armour
ring_mail_armour = armour(14, 'ring mail', dex_limit=0)
chain_mail_armour = armour(16, 'chain mail', dex_limit=0)
splint_armour = armour(17, 'splint', dex_limit=0)
plate_armour = armour(18, 'plate', dex_limit=0)


def rename(full: str, *other_names: tuple[str, str]):
    replacements = list(other_names)

    def process(target: str) -> str:
        for replacement in replacements:
            target = target.replace(*replacement)
        return target

    def process_feature(x: DndCreature.Feature):
        match x:
            case (n, d):
                return process(n), process(d)
            case _ as template:
                return lambda creature: process_feature(template(creature))

    def template(creature: DndCreature.TemplateArgs):
        for case in [str.lower, str.title]:
            replacements.append((case(creature['name']), case(full)))
        creature['name'] = full
        for feature in ['traits', 'actions', 'bonus_actions', 'reactions']:
            creature[feature] = [process_feature(x) for x in creature[feature]]
        creature['lore'] = process(creature['lore'])
    return template
