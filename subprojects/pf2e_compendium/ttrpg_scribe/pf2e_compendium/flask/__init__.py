import math
import re
from typing import Any, Iterable

import flask
from flask import Blueprint, Flask, json, render_template, request
from markupsafe import Markup

import ttrpg_scribe.core.flask
import ttrpg_scribe.core.typescript
import ttrpg_scribe.pf2e_compendium.foundry.enrich
import ttrpg_scribe.pf2e_compendium.oracle
from ttrpg_scribe.encounter.flask import (EncounterSpec, InitiativeParticipant,
                                          SystemPlugin)
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.actor import PF2Actor, analyser, templates
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.foundry import mongo_client
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

blueprint = Blueprint('pf2e_compendium', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')
ttrpg_scribe.core.typescript.extend(blueprint)


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
        'render': True
    })


@blueprint.get('/view/<doc_type>/<path:id>.json')
def raw_content(doc_type: str, id: str):
    return mongo_client.get_document(doc_type, id) or f'{id} does not exist in {doc_type}'


@blueprint.post('/analyse/<doc_type>/')
def analyse(doc_type: str):
    return analyser.analyse(doc_type, flask.request.get_json())


def _apply_adjustments(content):
    if not isinstance(content, PF2Actor):
        return
    for adjustment in flask.request.args.getlist('adjustment'):
        match adjustment:
            case 'elite':
                content.apply(templates.elite)
            case 'weak':
                content.apply(templates.weak)


@blueprint.get('/search/')
@blueprint.get('/search/<doc_type>')
def search_ui(doc_type: str | None = None):
    return flask.render_template('search_results.j2.html', doc_type=doc_type)


@blueprint.post('/search')
def search():
    doc_types = request.args.getlist('doc_type')
    if len(doc_types) == 0:
        doc_types = mongo_client.get_collection_names()
    query_type = request.args.get('query_type', 'simple')

    def create_match_args():
        match query_type:
            case 'simple':
                query = request.args.get('query', '')
                pattern = re.compile(query, re.IGNORECASE)
                return {'name': pattern}
            case 'complex':
                return request.get_json()
            case _:
                raise ValueError(query_type)

    return list(mongo_client.db.aggregate([
        *mongo_client.unionOf(doc_types),
        {'$match': create_match_args()},
        {
            '$project': {
                'doc_type': True,
                'name': True,
                'level': {
                    '$ifNull': ['$system.level.value', '$system.details.level.value']
                },
                'rarity': '$system.traits.rarity',
                'worldContent': '$volatile'
            }
        },
        {
            '$sort': {
                'level': 1,
                'name': 1
            }
        }
    ]))


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
    return Markup(f'<span class="action-glyph">{glyph}</span>')


@blueprint.app_template_filter()
def enrich(text: str, context: dict[str, Any] = {}):
    return ttrpg_scribe.pf2e_compendium.foundry.enrich.enrich(text, context)


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
        ttrpg_scribe.pf2e_compendium.oracle.extend(main_app)
        main_app.config['TOOLS'].insert(-1, (blueprint.url_prefix, 'Compendium', {}))
        main_app.config['TOOLS'].append(('/oracle/encounter', 'Encounter Oracle', {}))
        foundry.initialise()

    @classmethod
    def participant_from_id(cls, mongo_id: str) -> PF2Creature | PF2Hazard:
        _, data = foundry_packs.read_doc('all', mongo_id)
        assert isinstance(data, PF2Creature | PF2Hazard), \
            f'{mongo_id} does not resolve to PF2Creature | PF2Hazard'
        return data

    @classmethod
    def read_participant(cls, data: dict[str, Any] | InitiativeParticipant | str,
                         extra: dict[str, Any] = {}) -> InitiativeParticipant:
        def read_base() -> PF2Creature | PF2Hazard:
            match data:
                case {'kind': 'PF2Creature', **json}:
                    return PF2Creature.from_json(json)
                case PF2Creature() | PF2Hazard():
                    return data
                case {'kind': 'PF2Hazard', **json}:
                    return PF2Hazard.from_json(json)
                case str() as mongo_id:
                    return cls.participant_from_id(mongo_id)
                case dict():
                    raise ValueError(f'Unknown participant kind {data.get('kind')}')
                case unknown:
                    raise ValueError(f'Unknown participant kind {type(unknown)}')

        participant = read_base()

        from ttrpg_scribe.pf2e_compendium.actor.templates import (elite,
                                                                  rename, weak)
        match extra.get('adjustment'):
            case 'weak':
                participant = participant.apply(weak)
            case 'elite':
                participant = participant.apply(elite)

        if (name := extra.get('name')) is not None:
            participant = participant.apply(rename(name))

        if 'initiative' in extra:
            if isinstance(participant, PF2Hazard):
                raise TypeError(f'Cannot set initiative source for {participant}')
            participant.initiative_source = extra['initiative']

        return participant

    @classmethod
    def encounter_xp(cls, encounter: EncounterSpec) -> str:
        def resolve_level(participant: InitiativeParticipant) -> int:
            match participant:
                case PF2Creature() | PF2Hazard():
                    return participant.level
                case unknown:
                    raise ValueError(unknown)

        party: dict[str, dict[str, Any]] = flask.current_app.config['PARTY']
        party_level: int = flask.current_app.config['PARTY_LEVEL']
        return cls.compute_xp(
            ((count, resolve_level(creature)) for count, creature in encounter.enemies),
            ((count, resolve_level(creature)) for count, creature in encounter.allies),
            party_level, len(party))

    @classmethod
    def compute_xp(cls, enemies: Iterable[tuple[int, int]], allies: Iterable[tuple[int, int]],
                   party_level: int, party_size: int) -> str:
        def xp(creature_level: int):
            delta = creature_level - party_level
            if delta < -4:
                return 0
            elif delta >= 4:
                return 160
            return Pf2ePlugin._CREATURE_XP_BY_DELTA[delta]
        total = sum(max(0, count) * xp(level) for count, level in enemies)

        reward = math.ceil(total * 4 // party_size / 10) * 10  # round up to nearest 10
        extra_players = party_size - 4
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
