import math
import re
from dataclasses import dataclass

from ttrpg_scribe.pf2e_compendium.actions import SimpleAction, Strike
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, RESISTANCES, SAVING_THROWS,
    SKILLS, SPELL_DC, STRIKE_ATTACK_BONUS, STRIKE_DAMAGE, WEAKNESSES, StatisticBracket, Table)


@dataclass
class Report:
    name: str
    perception: StatisticBracket
    skills: list[tuple[str, StatisticBracket]]
    attributes: dict[str, StatisticBracket]
    ac: StatisticBracket
    saves: dict[str, StatisticBracket]
    hp: StatisticBracket

    @dataclass
    class Action:
        name: str
        bonus: StatisticBracket | None = None
        dc: StatisticBracket | None = None
        damage: StatisticBracket | None = None

    actions: list[Action]
    resistances: dict[str, StatisticBracket | int]
    weaknesses: dict[str, StatisticBracket | int]


def analyse(creature: PF2Creature):
    def classify(table: Table, value: int):
        return table.classify(creature.level, value)

    def analyse_strike(strike: Strike) -> Report.Action:
        bonus_bracket = classify(STRIKE_ATTACK_BONUS, strike.bonus)
        if strike.damage:
            average_damage = sum(
                math.floor(amount if isinstance(amount, int) else amount.average())
                for amount, _ in strike.damage
            )
            damage_bracket = classify(STRIKE_DAMAGE, average_damage)
            return Report.Action(strike.name, bonus=bonus_bracket, damage=damage_bracket)
        return Report.Action(strike.name, bonus=bonus_bracket)

    actions = []
    for action in creature.actions:
        match action:
            case Strike():
                actions.append(analyse_strike(action))
            case SimpleAction():
                dc = re.search(r'DC (\d+)', action.desc)
                dc = classify(SPELL_DC, int(dc[1])) if dc else None
                actions.append(Report.Action(action.name, dc=dc))

    return Report(
        creature.name,
        perception=classify(PERCEPTION, creature.perception),
        skills=[(skill.name, classify(SKILLS, skill.mod))
         for skill in creature.skills],
        attributes={ability: classify(ATTRIBUTE_MODIFIERS, value)
         for ability, value in creature.abilities.items()},
        ac=classify(ARMOR_CLASS, creature.ac),
        saves={save: classify(SAVING_THROWS, value)
         for save, value in creature.saves.items()},
        hp=HIT_POINTS.classify(creature.level, creature.max_hp),
        actions=actions,
        resistances={damage_type: classify(RESISTANCES, value)
         for damage_type, value in creature.resistances.items()},
        weaknesses={damage_type: classify(WEAKNESSES, value)
         for damage_type, value in creature.weaknesses.items()}
    )
