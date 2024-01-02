from flask import Blueprint, Flask, render_template

import dnd_scribe.encounter.flask
from dnd_scribe.bestiary import apis

blueprint = Blueprint('bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/creatures')


@blueprint.get('/view/<string:id>')
def creature(id: str):
    creature = apis.DND5EAPI.creature(id)
    return render_template('creature.j2.html',
                           creature=creature, render=True)


def create_app():
    app = Flask('dnd_scribe.bestiary.flask')
    app.register_blueprint(blueprint)
    return app


class Dnd5eSystem(dnd_scribe.encounter.flask.System):
    bestiary_blueprint = blueprint
