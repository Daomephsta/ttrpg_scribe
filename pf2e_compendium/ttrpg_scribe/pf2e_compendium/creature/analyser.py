import math
from typing import Any, Callable, TypedDict

from ttrpg_scribe.core.dice import SimpleDice
from ttrpg_scribe.pf2e_compendium.creature.statistics import (
    ARMOR_CLASS, ATTRIBUTE_MODIFIERS, HIT_POINTS, PERCEPTION, RESISTANCES,
    SAVING_THROWS, SKILLS, SPELL_ATTACK_BONUS, SPELL_DC, STRIKE_ATTACK_BONUS,
    STRIKE_DAMAGE, WEAKNESSES, StatisticBracket, Table)


class _AnalyseStrikes[B, D](TypedDict):
    bonuses: dict[str, B]
    damage: dict[str, D]


class _Analyse[T](TypedDict):
    perception: T
    skills: dict[str, T]
    attributes: dict[str, T]
    saves: dict[str, T]
    ac: T
    hp: T
    resistances: dict[str, T]
    weaknesses: dict[str, T]
    dcs: dict[str, T]
    spell_attack_bonuses: dict[str, T]


class _AnalyseRequest(_Analyse[int]):
    level: int
    strikes: _AnalyseStrikes[int, list[str]]
    damage: dict[str, list[str]]


class _AnalyseResponse(_Analyse[StatisticBracket]):
    strikes: _AnalyseStrikes[StatisticBracket, StatisticBracket]
    damage: dict[str, StatisticBracket]


def analyse(request: _AnalyseRequest) -> _AnalyseResponse:
    def classify(table: Table[Any], value: int):
        return table.classify(request['level'], value)

    def classify_dict[V](table: Table[Any], value: dict[str, V],
                         classifier: Callable[[Table[Any], V], StatisticBracket] = classify
                         ) -> dict[str, StatisticBracket]:
        return {k: classifier(table, v) for k, v in value.items()}

    def classify_damage(table: Table[Any], damage: list[str]) -> StatisticBracket:

        def dice_averages():
            for part in damage:
                if part.isnumeric():
                    yield int(part)
                else:
                    yield math.floor(SimpleDice.parse(part).average())

        return classify(table, sum(dice_averages()))

    return {
        'perception': classify(PERCEPTION, request['perception']),
        'skills': classify_dict(SKILLS, request['skills']),
        'ac': classify(ARMOR_CLASS, request['ac']),
        'attributes': classify_dict(ATTRIBUTE_MODIFIERS, request['attributes']),
        'saves': classify_dict(SAVING_THROWS, request['saves']),
        'hp': classify(HIT_POINTS, request['hp']),
        'resistances': classify_dict(RESISTANCES, request['resistances']),
        'weaknesses': classify_dict(WEAKNESSES, request['weaknesses']),
        'strikes': {
            'bonuses': classify_dict(STRIKE_ATTACK_BONUS, request['strikes']['bonuses']),
            'damage': classify_dict(STRIKE_DAMAGE, request['strikes']['damage'], classify_damage)
        },
        'dcs': classify_dict(SPELL_DC, request['dcs']),
        'spell_attack_bonuses': classify_dict(SPELL_ATTACK_BONUS, request['spell_attack_bonuses']),
        'damage': classify_dict(STRIKE_DAMAGE, request['damage'], classify_damage)
    }
