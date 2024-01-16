import math
from typing import Any

import flask
from flask import Blueprint, Flask, render_template

import ttrpg_scribe.core.flask
import ttrpg_scribe.encounter.flask
from ttrpg_scribe.encounter.flask import InitiativeParticipant, System
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

blueprint = Blueprint('pf2e_compendium', __name__,
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
def list_content(pack: str):
    path = foundry_packs.pf2e_dir()/'packs'/pack
    return render_template('content_list.j2.html', pack=pack,
        content=[path.stem for path in path.glob('*.json')])


@blueprint.get('/view/<path:id>')
def content(id: str):
    type, content = foundry_packs.content(id)
    if isinstance(content, dict):
        return content
    print(f'{type}.j2.html')
    return render_template(f'{type}.j2.html', **{
        type: content,
        'render': True
    })


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
    app = Flask('ttrpg_scribe.pf2e_compendium.flask')
    app.register_blueprint(blueprint)
    ttrpg_scribe.core.flask.extend(app)
    return app


class Pf2eSystem(System):
    bestiary_blueprint = blueprint
    _CREATURE_XP_BY_DELTA = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120}

    def read_participant(self, json) -> InitiativeParticipant:
        match json['kind']:
            case 'PF2Creature':
                return PF2Creature.from_json(json)
            case 'PF2Hazard':
                return PF2Hazard.from_json(json)
            case unknown:
                raise ValueError(f'Unknown participant kind {unknown}')

    def encounter_xp(self, enemies: list[tuple[int, PF2Creature]],
                     allies: list[tuple[int, PF2Creature]],
                     party: dict[str, dict[str, Any]]) -> str:
        party_level: int = flask.current_app.config['PARTY_LEVEL']

        def xp(creature: PF2Creature):
            delta = creature.level - party_level
            if delta < -4:
                return 0
            elif delta >= 4:
                return 160
            return Pf2eSystem._CREATURE_XP_BY_DELTA[delta]
        total = sum(count * xp(creature) for count, creature in enemies)

        reward = math.ceil(total * 4 // len(party) / 10) * 10  # round up to nearest 10
        extra_players = len(party) - 4
        threat_levels: list[tuple[int, str, int]] = [
            (40 + extra_players * 10, 'Trivial', reward),
            (60 + extra_players * 15, 'Low', reward),
            (80 + extra_players * 20, 'Moderate', reward),
            (120 + extra_players * 30, 'Severe', reward),
            (160 + extra_players * 40, 'Extreme', reward),
        ]

        def describe_threat(threshold: int, threat: str, reward: int, threat_idx: int):
            delta = total - threshold
            if delta > 0:
                if threat_idx == len(threat_levels) - 1:
                    return f'{reward} ({threat} + {delta})'
                upper_threshold, _, _ = threat_levels[threat_idx + 1]
                return f'{reward} ({threat} + {delta}/{upper_threshold - threshold})'
            elif delta < 0:
                lower_threshold = threat_levels[threat_idx][0] if threat_idx > 0 else 0
                return f'{reward} ({threat} - {abs(delta)}/{threshold - lower_threshold})'
            else:
                return f'{reward} ({threat})'
        for i, (threshold, threat, reward) in enumerate(reversed(threat_levels)):
            if total >= threshold:
                return describe_threat(threshold, threat, reward, len(threat_levels) - i - 1)
        return describe_threat(*threat_levels[0], 0)
