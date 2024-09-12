import math
from dataclasses import dataclass

from ttrpg_scribe.pf2e_compendium.actions import Strike
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, SAVING_THROWS,
    SKILLS, STRIKE_ATTACK_BONUS, STRIKE_DAMAGE)


@dataclass
class Report:
    name: str
    perception: str
    skills: list[tuple[str, str]]
    attributes: list[tuple[str, str]]
    ac: str
    saves: list[tuple[str, str]]
    hp: str

    @dataclass
    class Strike:
        name: str
        bonus: str
        damage: str
    strikes: list[Strike]


def analyse(creature: PF2Creature):
    def analyse_strike(strike: Strike) -> Report.Strike:
        bonus_bracket = STRIKE_ATTACK_BONUS.classify(creature.level, strike.bonus)
        if strike.damage:
            average_damage = sum(
                math.floor(amount if isinstance(amount, int) else amount.average())
                for amount, _ in strike.damage
            )
            damage_bracket = STRIKE_DAMAGE.classify(creature.level, average_damage)
            return Report.Strike(strike.name, bonus_bracket, damage_bracket)
        return Report.Strike(strike.name, bonus_bracket, '')

    return Report(
        creature.name,
        PERCEPTION.classify(creature.level, creature.perception),
        [(skill.name, SKILLS.classify(creature.level, skill.mod))
         for skill in creature.skills],
        [(ability, ATTRIBUTE_MODIFIERS.classify(creature.level, value))
         for ability, value in creature.abilities.items()],
        ARMOR_CLASS.classify(creature.level, creature.ac),
        [(save, SAVING_THROWS.classify(creature.level, value))
         for save, value in creature.saves.items()],
        HIT_POINTS.classify(creature.level, creature.max_hp),
        [analyse_strike(action) for action in creature.actions if isinstance(action, Strike)]
    )
