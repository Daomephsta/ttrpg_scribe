from typing import Callable, TypedDict, Unpack, cast

from dnd_scribe.bestiary.creature import Creature, ability
from dnd_scribe.bestiary.creature.ability import Ability
from dnd_scribe.bestiary.creature.armour import ArmourClass


def adjust_scores(abilities: set[str], adjuster: Callable[[str, int], int]):
    # Apply filter to adjuster
    filtered_adjuster = lambda ability, value: (adjuster(ability, value)\
        if ability in abilities else value)
    def template(args: Creature.TemplateArgs):
        args['statistics'] = cast(Creature.Statistics,
            tuple(filtered_adjuster(ability.abbreviation, value)
            for ability, value in zip(Ability, args['statistics'])))
    return template

def civilised(args: Creature.TemplateArgs):
    args['name'] = f"'Civilised' {args['name']}"
    adjust_scores({'int'}, lambda _, val: max(6, val))(args)

Scores = TypedDict('Scores', {'str': int, 'dex': int, 'con': int, 'int': int, 'wis': int, 'cha': int}, total=False)
def scores(**values: Unpack[Scores]):
    return adjust_scores(set(values.keys()), values.get)

def armour(base_ac: int, reason: str, dex_limit: int = 10):
    def template(args: Creature.TemplateArgs):
        ac = base_ac + min(dex_limit, ability.mod(args['statistics'][1]))
        args['ac'] = [ArmourClass(ac, f'{ac} ({reason})')]
    return template

leather_armour = armour(11, 'leather')
studded_leather_armour = armour(12, 'studded leather')