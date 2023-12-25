import json
from dnd_scribe.pf2e_bestiary import foundry

from flask import Blueprint, Flask, render_template

from dnd_scribe.pf2e_bestiary.creature import PF2Creature
import dnd_scribe.core.flask

blueprint = Blueprint('pf2e_bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/creatures')


@blueprint.get('/')
def list_creatures():
    packs_dir = foundry.pf2e_pack_dir()/'packs'
    packs = foundry.pf2e_pack_dir().glob('packs/*-bestiary')
    creatures = (
        (pack.name, (entry.relative_to(packs_dir)
                     for entry in pack.glob('*.json')))
        for pack in packs
    )
    return render_template('creature_list.j2.html', creatures=creatures)


@blueprint.get('/view/<path:id>')
def creature(id: str):
    with foundry.pf2e_pack_open(f'packs/{id}.json') as data:
        return render_template(
            'pf2e_creature.j2.html',
            creature=PF2Creature.from_json(json.load(data)),
            render=True)


def create_app():
    app = Flask('dnd_scribe.pf2e_bestiary.flask')
    app.register_blueprint(blueprint)
    dnd_scribe.core.flask.extend(app)
    return app
