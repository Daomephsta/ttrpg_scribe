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
    html = [
        '<html>',
        '<head><title>Creatures</title></head>',
        '<h1>Creatures</h1>',
    ]
    for pack, creatures in creatures:
        html.append(f'<h2>{pack}</h2>')
        html.append('<ul>')
        for creature in creatures:
            html.append(f'<li><a href="/creatures/view/{creature.with_suffix('').as_posix()}">{creature.stem.replace('-', ' ').title()}</a></li>')
        html.append('</ul>')
    html.append('</html>',)
    return '\n'.join(html)


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
