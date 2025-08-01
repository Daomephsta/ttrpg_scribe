import math
from typing import Any

import flask
from flask import Blueprint, Flask, json, render_template, request
from markupsafe import Markup
from werkzeug.exceptions import BadRequest

import ttrpg_scribe.core.flask
import ttrpg_scribe.pf2e_compendium.foundry.enrich
from ttrpg_scribe.encounter.flask import InitiativeParticipant, SystemPlugin
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature import analyser as creature_analyser
from ttrpg_scribe.pf2e_compendium.creature import templates
from ttrpg_scribe.pf2e_compendium.foundry import mongo_client
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

blueprint = Blueprint('pf2e_compendium', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')


@blueprint.get('/')
@blueprint.get('/list')
def list_collections():
    return render_template('collection_list.j2.html', types=mongo_client.get_collection_names())


@blueprint.get('/list/<doc_type>')
def list_packs(doc_type: str):
    return render_template('pack_list.j2.html', type=doc_type,
                           packs=mongo_client.get_pack_names(doc_type))


@blueprint.get('/list/<doc_type>/<pack>')
@blueprint.get('/list/<doc_type>/<pack>/<path:subpath>')
def list_content(doc_type: str, pack: str, subpath: str = ''):
    pack_content = mongo_client.get_pack_content(doc_type, pack, subpath)
    if subpath == '':
        subpaths = mongo_client.get_pack_subpaths(doc_type, pack)
    else:
        subpaths = []
    return render_template('content_list.j2.html', type=doc_type, pack=pack, subpath=subpath,
                           contents=pack_content, subpaths=subpaths)


@blueprint.post('/view')
def view_payload():
    if 'json' in flask.request.form:
        payload = json.loads(flask.request.form['json'])
    else:
        payload = flask.request.json
    assert isinstance(payload, dict)
    return _content(*foundry_packs.read(payload))


@blueprint.get('/view/<doc_type>/<path:id>')
def content(doc_type: str, id: str):
    return _content(*foundry_packs.read_doc(doc_type, id))


def _content(type: str, content):
    if type.startswith('raw') and isinstance(content, dict | list):
        return content
    _apply_adjustments(content)
    return render_template(f'{type}.j2.html', **{
        'data': content,
        'render': True,
    })


@blueprint.get('/view/<doc_type>/<path:id>.json')
def raw_content(doc_type: str, id: str):
    return mongo_client.get_document(doc_type, id) or f'{id} does not exist in {doc_type}'


@blueprint.post('/analyse/<doc_type>/')
def analyse(doc_type: str):
    match doc_type:
        case 'npc':
            return json.jsonify(creature_analyser.analyse(flask.request.get_json()))
        case _:
            raise BadRequest(f'No analyser for content type {type}')


def _apply_adjustments(content):
    if not isinstance(content, PF2Creature):
        return
    for adjustment in flask.request.args.getlist('adjustment'):
        match adjustment:
            case 'elite':
                content.apply(templates.elite)
            case 'weak':
                content.apply(templates.weak)


@blueprint.post('/search')
@blueprint.get('/search')
def search():
    query = request.args.get('query', '')
    doc_types = request.args.getlist('doc-type')
    return render_template('search_results.j2.html',
                           content=mongo_client.search_by_name(query, doc_types))


@blueprint.app_template_filter()
def action(kind: int | str):
    glyph: str
    match kind:
        case 0:
            return ''
        case int(i):
            glyph = str(i)
        case 're' | 'reaction':
            glyph = 'r'
        case 'free':
            glyph = 'f'
        case str():
            if kind.isdigit():
                return action(int(kind))
            if ' to ' in kind:
                left, sep, right = kind.partition(' to ')
            elif ' or ' in kind:
                left, sep, right = kind.partition(' or ')
            else:
                return kind
            return Markup(f'<span>{action(left)}{sep}{action(right)}</span>')
    return Markup(f'<span class="action-symbol">{glyph}</span>')


@blueprint.app_template_filter()
def enrich(text: str):
    return ttrpg_scribe.pf2e_compendium.foundry.enrich.enrich(text)


def create_app():
    app = Flask('ttrpg_scribe.pf2e_compendium.flask')
    app.register_blueprint(blueprint)
    ttrpg_scribe.core.flask.extend(app)
    return app


class Pf2ePlugin(SystemPlugin):
    _CREATURE_XP_BY_DELTA = {-4: 10, -3: 15, -2: 20, -1: 30, 0: 40, 1: 60, 2: 80, 3: 120}
    compendium_blueprint = blueprint

    @classmethod
    def configure(cls, main_app: Flask):
        super().configure(main_app)
        main_app.config['TOOLS'].insert(-1, ('/compendium', 'Compendium', {}))
        foundry.check_for_updates()

    @classmethod
    def read_participant(cls, json) -> InitiativeParticipant:
        match json['kind']:
            case 'PF2Creature':
                return PF2Creature.from_json(json)
            case 'PF2Hazard':
                return PF2Hazard.from_json(json)
            case unknown:
                raise ValueError(f'Unknown participant kind {unknown}')

    @classmethod
    def encounter_xp(cls, enemies: list[tuple[int, PF2Creature]],
                     allies: list[tuple[int, PF2Creature]],
                     party: dict[str, dict[str, Any]]) -> str:
        party_level: int = flask.current_app.config['PARTY_LEVEL']

        def xp(creature: PF2Creature):
            delta = creature.level - party_level
            if delta < -4:
                return 0
            elif delta >= 4:
                return 160
            return Pf2ePlugin._CREATURE_XP_BY_DELTA[delta]
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
