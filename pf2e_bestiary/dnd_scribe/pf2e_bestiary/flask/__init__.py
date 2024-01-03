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

        budget = total
        if budget <= 40:
            threat = 'Trivial'
        elif budget <= 60:
            threat = 'Low'
        elif budget <= 80:
            threat = 'Moderate'
        elif budget <= 120:
            threat = 'Severe'
        else:
            threat = 'Extreme'

        return f'{total} ({threat})'
