from flask import Blueprint, render_template, Flask

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