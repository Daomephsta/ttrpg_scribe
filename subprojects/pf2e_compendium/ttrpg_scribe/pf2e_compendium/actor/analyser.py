import math
from typing import TypedDict

from werkzeug.exceptions import BadRequest

from ttrpg_scribe.core.dice import SimpleDice
from ttrpg_scribe.pf2e_compendium.actor.statistics import Table
from ttrpg_scribe.pf2e_compendium.creature import \
    statistics as creature_statistics
from ttrpg_scribe.pf2e_compendium.hazard import statistics as hazard_statistics


class _Value(TypedDict):
    id: str
    value: int | list[str]
    table: str


class _AnalyseRequest(TypedDict):
    level: int
    values: list[_Value]


_TABLES: dict[str, dict[str, Table]] = {
    'npc': {
        'armour-class': creature_statistics.ARMOUR_CLASS,
        'attribute': creature_statistics.ATTRIBUTE_MODIFIERS,
        'hit-points': creature_statistics.HIT_POINTS,
        'perception': creature_statistics.PERCEPTION,
        'resistance': creature_statistics.RESISTANCES,
        'save': creature_statistics.SAVING_THROWS,
        'skill': creature_statistics.SKILLS,
        'spell-attack': creature_statistics.SPELL_ATTACK_BONUS,
        'dc': creature_statistics.SPELL_DC,
        'strike-bonus': creature_statistics.STRIKE_ATTACK_BONUS,
        'strike-damage': creature_statistics.STRIKE_DAMAGE,
        'weakness': creature_statistics.WEAKNESSES,
    },
    'hazard': {
        'armour-class': hazard_statistics.ARMOUR_CLASS,
        'complex-strike-bonus': hazard_statistics.COMPLEX_ATTACK,
        'complex-strike-damage': hazard_statistics.COMPLEX_DAMAGE,
        'disable-dc': hazard_statistics.DISABLE_DC,
        'hardness': hazard_statistics.HARDNESS,
        'hit-points': hazard_statistics.HIT_POINTS,
        'offense-dc': hazard_statistics.OFFENSE_DC,
        'save': hazard_statistics.SAVING_THROWS,
        'simple-strike-bonus': hazard_statistics.SIMPLE_ATTACK,
        'simple-strike-damage': hazard_statistics.SIMPLE_DAMAGE,
        'stealth': hazard_statistics.STEALTH_MODIFIER,
        'notice-dc': hazard_statistics.STEALTH_DC,
    }
}


def analyse(doc_type: str, request: _AnalyseRequest):
    if doc_type not in _TABLES:
        raise BadRequest(f'No analyser for content type {doc_type}')

    def dice_averages(damage: list[str]):
        for part in damage:
            if part.isnumeric():
                yield int(part)
            else:
                yield math.floor(SimpleDice.parse(part).average())

    def classify(value: _Value):
        def error(message: str):
            return {'id': value['id'], 'bracket': 'Error', 'full': message}

        table = _TABLES[doc_type].get(value['table'])
        if table is None:
            return error(f'Unknown table {value['table']}')
        assert value['value'] is not None
        classification = table.classify(
            request['level'],
            sum(dice_averages(value['value']))
                if isinstance(value['value'], list)
                else value['value']
        )
        return {
            'id': value['id'],
            'bracket': classification.name,
            'full': str(classification)
        }

    return [classify(value) for value in request['values']]
