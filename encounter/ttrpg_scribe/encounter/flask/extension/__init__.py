import flask

_blueprint = flask.Blueprint(import_name='ttrpg_scribe.encounter.flask.extension',
    name='encounter_extension',
    static_folder='static', template_folder='templates')


def extend(app: flask.Flask, url_prefix: str):
    app.register_blueprint(_blueprint, url_prefix=url_prefix)
    tools: list[tuple[str, str, dict]] = app.config['TOOLS']
    tools += [
        ('/encounter', 'Launch Encounter', {'method': 'post'}),
        ('/encounter/party/configure', 'Configure Party', {}),
    ]
