import flask


_blueprint = flask.Blueprint(import_name='dnd_scribe.encounter.flask.extension', 
    name='encounter/contribution', template_folder='templates')

def extend(app: flask.Flask):
    app.register_blueprint(_blueprint)
    if 'dnd_scribe.notes.index.tools' in app.config:
        app.config['dnd_scribe.notes.index.tools'].append(
            ('/combat', 'Launch Combat', {'method': 'post'}))