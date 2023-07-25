from argparse import ArgumentParser

import waitress
from werkzeug.middleware.dispatcher import DispatcherMiddleware

import dnd_scribe.encounter.flask
import dnd_scribe.encounter.flask.extension
import dnd_scribe.notes
import dnd_scribe.npc.flask_app
import dnd_scribe.npc.flask_app.extension


def make_app(project_dir: str):
    app = dnd_scribe.notes.create_app(project_dir)
    dnd_scribe.encounter.flask.extension.extend(app, '/encounter_extension')
    dnd_scribe.npc.flask_app.extension.extend(app, '/npc_extension')
    app.config['TOOLS'] = [
        ('/encounter', 'Launch Encounter', {'method': 'post'}),
        ('/npc/gui', 'NPC Generator', {})
    ]
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/encounter': dnd_scribe.encounter.flask.create_app(project_dir),
        '/npc': dnd_scribe.npc.flask_app.create_app(project_dir)
    })
    return app

def start_production():
    parser = ArgumentParser('dnd_scribe.all_in_one')
    parser.add_argument('project_dir')
    args = parser.parse_args()

    app = make_app(args.project_dir)
    waitress.serve(app, listen='127.0.0.1:48164')