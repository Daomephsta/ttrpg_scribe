from typing import Callable, TypedDict, Unpack

from dnd_scribe.bestiary.creature import Creature, ability
from dnd_scribe.bestiary.creature.armour import ArmourClass

Score = int | Callable[[int], int]
Scores = TypedDict('Scores', {'str': Score, 'dex': Score, 'con': Score, 'int': Score, 'wis': Score, 'cha': Score}, total=False)
def scores(**values: Unpack[Scores]):
    def template(creature: Creature.TemplateArgs):
        def adjust_score(ability: str, current: int) -> int:
            if ability not in values:
                return current
            return values[ability] if isinstance(values[ability], int)\
                else values[ability](current)

        str, dex, con, int, wis, cha = values
        creature['statistics'] = (
            adjust_score('str', str),
            adjust_score('dex', dex),
            adjust_score('con', con),
            adjust_score('int', int),
            adjust_score('wis', wis),
            adjust_score('cha', cha),
        )
    return template

def score(modifier: int, fallback: int=0) -> Callable[[int], int]:
    if modifier >= 0:
        return lambda value: min(value + modifier, 20)
    else:
        return lambda value: max(max(fallback, 0), value + modifier)

def armour(base_ac: int, reason: str, dex_limit: int = 10):
    def template(args: Creature.TemplateArgs):
        ac = base_ac + min(dex_limit, ability.mod(args['statistics'][1]))
        args['ac'] = [ArmourClass(ac, f'{ac} ({reason})')]
    return template

leather_armour = armour(11, 'leather')
studded_leather_armour = armour(12, 'studded leather')