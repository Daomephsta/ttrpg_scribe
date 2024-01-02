import json

from flask import Blueprint, Flask, render_template

import dnd_scribe.core.flask
import dnd_scribe.encounter.flask
from dnd_scribe.pf2e_bestiary import foundry
from dnd_scribe.pf2e_bestiary.creature import PF2Creature

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
               for pack in (foundry.pf2e_pack_dir()/'packs').iterdir()
               if 'bestiary' in pack.name and pack.name not in _EXCLUDED_PACKS])


@blueprint.get('/pack/<string:pack>')
def list_creatures(pack: str):
    path = foundry.pf2e_pack_dir()/'packs'/pack
    return render_template('creature_list.j2.html', pack=pack,
        creatures=[creature.stem for creature in path.glob('*.json')])


@blueprint.get('/view/<path:id>')
def creature(id: str):
    with foundry.pf2e_pack_open(f'packs/{id}.json') as data:
        return render_template(
            'creature.j2.html',
            creature=PF2Creature.from_json(json.load(data)),
            render=True)


def create_app():
    app = Flask('dnd_scribe.pf2e_bestiary.flask')
    app.register_blueprint(blueprint)
    dnd_scribe.core.flask.extend(app)
    return app


class Pf2eSystem(dnd_scribe.encounter.flask.System):
    bestiary_blueprint = blueprint
