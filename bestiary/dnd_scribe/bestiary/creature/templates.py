from typing import Callable, Iterable, TypedDict, Unpack

from dnd_scribe.bestiary.creature import Creature, ability
from dnd_scribe.bestiary.creature.armour import ArmourClass


def compose(*templates: Creature.Template) -> Creature.Template:
    def composed(creature: Creature.TemplateArgs):
        for template in templates:
            template(creature)
    return composed

Score = int | Callable[[int], int]
Scores = TypedDict('Scores', {'str': Score, 'dex': Score, 'con': Score, 'int': Score, 'wis': Score, 'cha': Score}, total=False)
def scores(**values: Unpack[Scores]):
    def template(creature: Creature.TemplateArgs):
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
    def template(args: Creature.TemplateArgs):
        ac = base_ac + min(dex_limit, ability.mod(args['statistics'][1]))
        args['ac'] = [ArmourClass(ac, f'{ac} ({reason})')]
    return template

leather_armour = armour(11, 'leather')
studded_leather_armour = armour(12, 'studded leather')