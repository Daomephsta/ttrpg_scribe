import flask

_blueprint = flask.Blueprint(import_name='dnd_scribe.encounter.flask.extension',
    name='encounter_extension',
    static_folder='static', template_folder='templates')

def extend(app: flask.Flask, url_prefix: str):
    app.register_blueprint(_blueprint, url_prefix=url_prefix)
    if 'dnd_scribe.notes.index.tools' in app.config:
        app.config['dnd_scribe.notes.index.tools'].append(
            ('/encounter', 'Launch Encounter', {'method': 'post'}))