import math
import re

from ttrpg_scribe.pf2e_compendium.actions import Strike
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, SAVING_THROWS, SKILLS,
    STRIKE_ATTACK_BONUS, STRIKE_DAMAGE)


def analyse(creature: PF2Creature):
    print(creature.name)

    print('Perception', PERCEPTION.classify(creature.level, creature.perception))

    print('Skills')
    for skill in creature.skills:
        print(f'\t{skill.name} {SKILLS.classify(creature.level, skill.mod)}')

    print('Attributes')
    for ability, value in creature.abilities.items():
        print(f'\t{ability} {ATTRIBUTE_MODIFIERS.classify(creature.level, value)}')

    print('AC', ARMOR_CLASS.classify(creature.level, creature.ac))

    print('Saves')
    for save, value in creature.saves.items():
        print(f'\t{save} {SAVING_THROWS.classify(creature.level, value)}')

    print('HP', HIT_POINTS.classify(creature.level, creature.max_hp))

    print('Strikes')
    for action in creature.actions:
        if isinstance(action, Strike):
            print(f'\t{action.name}')
            bonus_bracket = STRIKE_ATTACK_BONUS.classify(creature.level, action.bonus)
            print(f'\t\tAttack Bonus {bonus_bracket}')
            if action.damage:
                average_damage: int = 0
                for dice, _ in action.damage:
                    result = re.fullmatch(
                        r'(?P<count>\d+)d(?P<size>\d+)(?:[+-](?P<mod>\d+))?',
                        dice
                    )
                    assert result
                    groups = result.groupdict()
                    count = int(groups['count'] or '1')
                    size = int(groups['size'])
                    mod = int(groups['mod'] or '0')
                    average_damage += count * math.floor((size + 1) / 2) + mod
                damage_bracket = STRIKE_DAMAGE.classify(creature.level, average_damage)
                print(f'\t\tDamage {damage_bracket}')
