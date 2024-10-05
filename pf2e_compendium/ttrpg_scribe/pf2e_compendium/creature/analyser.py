import math
import re
from dataclasses import dataclass

from ttrpg_scribe.pf2e_compendium.actions import SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, SAVING_THROWS,
    SKILLS, SPELL_DC, STRIKE_ATTACK_BONUS, STRIKE_DAMAGE)


@dataclass
class Report:
    name: str
    perception: str
    skills: list[tuple[str, str]]
    attributes: dict[str, str]
    ac: str
    saves: dict[str, str]
    hp: str

    @dataclass
    class Action:
        name: str
        bonus: str = ''
        dc: str = ''
        damage: str = ''

    actions: list[Action]


def analyse(creature: PF2Creature):
    def analyse_strike(strike: Strike) -> Report.Action:
        bonus_bracket = STRIKE_ATTACK_BONUS.classify(creature.level, strike.bonus)
        if strike.damage:
            average_damage = sum(
                math.floor(amount if isinstance(amount, int) else amount.average())
                for amount, _ in strike.damage
            )
            damage_bracket = STRIKE_DAMAGE.classify(creature.level, average_damage)
            return Report.Action(strike.name, bonus=bonus_bracket, damage=damage_bracket)
        return Report.Action(strike.name, bonus=bonus_bracket)

    actions = []
    for action in creature.actions:
        match action:
            case Strike():
                actions.append(analyse_strike(action))
            case SimpleAction():
                dc = re.search(r'DC (\d+)', action.desc)
                dc = SPELL_DC.classify(creature.level, int(dc[1])) if dc else ''
                actions.append(Report.Action(action.name, dc=dc))

    return Report(
        creature.name,
        PERCEPTION.classify(creature.level, creature.perception),
        [(skill.name, SKILLS.classify(creature.level, skill.mod))
         for skill in creature.skills],
        {ability: ATTRIBUTE_MODIFIERS.classify(creature.level, value)
         for ability, value in creature.abilities.items()},
        ARMOR_CLASS.classify(creature.level, creature.ac),
        {save: SAVING_THROWS.classify(creature.level, value)
         for save, value in creature.saves.items()},
        HIT_POINTS.classify(creature.level, creature.max_hp),
        actions
    )
