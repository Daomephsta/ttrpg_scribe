import math
import re
from typing import Any

import flask
from flask import Blueprint, Flask, render_template, request
from markupsafe import Markup
from werkzeug.exceptions import BadRequest

import ttrpg_scribe.core.flask
from ttrpg_scribe.encounter.flask import InitiativeParticipant, SystemPlugin
from ttrpg_scribe.pf2e_compendium import foundry
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature
from ttrpg_scribe.pf2e_compendium.creature import analyser as creature_analyser
from ttrpg_scribe.pf2e_compendium.creature import templates
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs
from ttrpg_scribe.pf2e_compendium.hazard import PF2Hazard

blueprint = Blueprint('pf2e_compendium', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')


@blueprint.get('/')
@blueprint.get('/list')
def list_collections():
    return render_template('collection_list.j2.html', types=foundry.get_collections())


@blueprint.get('/list/<doc_type>')
def list_packs(doc_type: str):
    packs = foundry.db[doc_type].distinct('path.pack')
    return render_template('pack_list.j2.html', type=doc_type, packs=packs)


@blueprint.get('/list/<doc_type>/<pack>')
@blueprint.get('/list/<doc_type>/<pack>/<path:subpath>')
def list_content(doc_type: str, pack: str, subpath: str = ''):
    pack_content = foundry.db[doc_type].find(
        {'path': {'pack': pack, 'subpath': subpath}}, {'name': True})
    if subpath == '':
        subpaths = foundry.db[doc_type].distinct('path.subpath',
                                                 {'path.pack': pack, 'path.subpath': {'$ne': ''}})
    else:
        subpaths = []
    return render_template(
        'content_list.j2.html', type=doc_type, pack=pack, subpath=subpath,
        content=[(content['_id'], content['name']) for content in pack_content], subpaths=subpaths
    )


@blueprint.get('/view/<doc_type>/<path:id>')
def content(doc_type: str, id: str):
    type, content = foundry_packs.read(doc_type, id)
    if isinstance(content, (dict, list)):
        return content
    _apply_adjustments(content)
    return render_template(f'{type}.j2.html', **{
        type: content,
        'render': True,
    })


@blueprint.get('/view/<doc_type>/<path:id>.json')
def raw_content(doc_type: str, id: str):
    return foundry.get_document(doc_type, id) or f'{id} does not exist in {doc_type}'


@blueprint.get('/analyse/<doc_type>/<path:id>')
def analyse(doc_type: str, id: str):
    type, content = foundry_packs.read(doc_type, id)
    match type, content:
        case 'creature', PF2Creature():
            _apply_adjustments(content)
            report = creature_analyser.analyse(content)
        case _:
            raise BadRequest(f'No analyser for content type {type}')
    return render_template(f'analyse/{type}.j2.html', report=report)


def _apply_adjustments(content):
    if not isinstance(content, PF2Creature):
        return
    for adjustment in flask.request.args.getlist('adjustment'):
        match adjustment:
            case 'elite':
                content.apply(templates.elite)
            case 'weak':
                content.apply(templates.weak)


@blueprint.get('/search')
def search():
    query = request.args.get('query', '')
    doc_types = request.args.getlist('doc-type')
    if len(doc_types) == 0:
        doc_types = foundry.get_collections()

    def results():
        pattern = re.compile(query)
        for doc_type in doc_types:
            yield from foundry.db[doc_type].find({'path.stem': pattern},
                                                 {'name': True, 'doc_type': doc_type})
    return render_template('search_results.j2.html', content=results())


@blueprint.app_template_filter()
def action(kind: int | str):
    glyph: str | int = '?'
    match kind:
        case 0:
            glyph = ''
        case int(i):
            glyph = i
        case 're' | 'reaction':
            glyph = 'r'
        case 'free':
            glyph = 'f'
        case _:
            glyph = '?'
    return Markup(f'<span class="action-symbol">{glyph}</span>')


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
