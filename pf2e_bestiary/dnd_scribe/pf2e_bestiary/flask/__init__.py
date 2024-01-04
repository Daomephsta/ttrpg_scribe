import math
from typing import Any

import flask
from flask import Blueprint, Flask, render_template

import dnd_scribe.core.flask
import dnd_scribe.encounter.flask
from dnd_scribe.encounter.flask import Creature, System
from dnd_scribe.pf2e_bestiary.creature import PF2Creature
from dnd_scribe.pf2e_bestiary.foundry import packs as foundry_packs

blueprint = Blueprint('pf2e_bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/creatures')

_EXCLUDED_PACKS = [
    'bestiary-ability-glossary-srd',
    'bestiary-effects',
    'bestiary-family-ability-glossary'
]


@blueprint.get('/')
def list_packs():
    return render_template('pack_list.j2.html',
        packs=[pack.name
               for pack in (foundry_packs.pf2e_dir()/'packs').iterdir()
               if 'bestiary' in pack.name and pack.name not in _EXCLUDED_PACKS])


@blueprint.get('/pack/<string:pack>')
def list_creatures(pack: str):
    path = foundry_packs.pf2e_dir()/'packs'/pack
    return render_template('creature_list.j2.html', pack=pack,
        creatures=[creature.stem for creature in path.glob('*.json')])


@blueprint.get('/view/<path:id>')
def creature(id: str):
    return render_template(
        'creature.j2.html',
        creature=foundry_packs.creature(id),
        render=True)


@blueprint.app_template_filter()
def action(kind: int | str):
    match kind:
        case int(i):
            return '\u25C6' * i
        case 're' | 'reaction':
            return '\u2B8C'
        case 'free':
            return '\u25C7'


def create_app():
    app = Flask('dnd_scribe.pf2e_bestiary.flask')
    app.register_blueprint(blueprint)
    dnd_scribe.core.flask.extend(app)
    return app


class Pf2eSystem(System):
    bestiary_blueprint = blueprint
    _CREATURE_XP_BY_DELTA = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120}

    def read_creature(self, json) -> Creature:
        return PF2Creature.from_json(json)

    def encounter_xp(self, npcs: list[tuple[int, PF2Creature]],
                     party: dict[str, dict[str, Any]]) -> str:
        party_level: int = flask.current_app.config['PARTY_LEVEL']

        def xp(creature: PF2Creature):
            delta = creature.level - party_level
            if delta < -4:
                return 0
            elif delta >= 4:
                return 160
            return Pf2eSystem._CREATURE_XP_BY_DELTA[delta]
        total = sum(count * xp(creature) for count, creature in npcs)

        reward = math.ceil(total * 4 // len(party) / 10) * 10  # round up to nearest 10
        extra_players = len(party) - 4
        threat_levels = [
            (160 + extra_players * 40, 'Extreme', reward),
            (120 + extra_players * 30, 'Severe', reward),
            (80 + extra_players * 20, 'Moderate', reward),
            (60 + extra_players * 15, 'Low', reward),
            (40 + extra_players * 10, 'Trivial', 0),
        ]

        def describe_threat(threshold: int, threat: str, reward: int):
            return f'{reward} ({total / threshold:.0%} {threat})'
        for threshold, threat, reward in threat_levels:
            if total >= threshold:
                return describe_threat(threshold, threat, reward)
        return describe_threat(*threat_levels[0])
