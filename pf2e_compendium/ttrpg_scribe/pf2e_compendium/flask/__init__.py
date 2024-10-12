import json
import math
from typing import Any

import flask
from flask import Blueprint, Flask, render_template, request
from werkzeug.exceptions import BadRequest

import ttrpg_scribe.core.flask
import ttrpg_scribe.encounter.flask
from ttrpg_scribe.encounter.flask import InitiativeParticipant, System
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature import analyser as creature_analyser
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

blueprint = Blueprint('pf2e_compendium', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')

_EXCLUDED_PACKS = {
    'bestiary-ability-glossary-srd',
    'bestiary-effects',
    'bestiary-family-ability-glossary'
}


@blueprint.get('/')
def list_packs():
    return render_template('pack_list.j2.html', packs=[
        pack.name for pack in (foundry.pf2e_dir()/'packs').iterdir()])


@blueprint.get('/pack/<string:pack>')
def list_content(pack: str):
    path = foundry.pf2e_dir()/'packs'/pack
    return render_template('content_list.j2.html', pack=pack,
        content=(path.stem for path in path.glob('*.json')
                 if not path.name.startswith('_')))


@blueprint.get('/view/<path:id>')
def content(id: str):
    type, content = foundry_packs.content(id)
    if isinstance(content, (dict, list)):
        return content
    return render_template(f'{type}.j2.html', **{
        type: content,
        'render': True,
    })


@blueprint.get('/analyse/<path:id>')
def analyse(id: str):
    type, content = foundry_packs.content(id)
    match type, content:
        case 'creature', PF2Creature():
            report = creature_analyser.analyse(content)
        case _:
            raise BadRequest(f'No analyser for content type {type}')
    return render_template(f'analyse/{type}.j2.html', report=report)


@blueprint.get('/view/<path:id>.json')
def raw_content(id: str):
    with foundry.open_pf2e_file(f'packs/{id}.json') as file:
        return json.load(file)


@blueprint.get('/search')
def search():
    query = request.args.get('query', '')

    def results():
        packs_dir = foundry.pf2e_dir()/'packs'
        for pack in (foundry.pf2e_dir()/'packs').iterdir():
            for path in pack.iterdir():
                if query in path.stem:
                    yield path.relative_to(packs_dir).with_suffix('')
    return render_template('search_results.j2.html', content=results())


@blueprint.app_template_filter()
def action(kind: int | str):
    match kind:
        case 0:
            return ''
        case int(i):
            return str(i)
        case 're' | 'reaction':
            return 'r'
        case 'free':
            return 'f'


def create_app():
    app = Flask('ttrpg_scribe.pf2e_compendium.flask')
    app.register_blueprint(blueprint)
    ttrpg_scribe.core.flask.extend(app)
    return app


class Pf2eSystem(System):
    compendium_blueprint = blueprint
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
        total = sum(max(0, count) * xp(creature) for count, creature in enemies)

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
