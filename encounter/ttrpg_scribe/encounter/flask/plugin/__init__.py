from pathlib import Path

import flask

import ttrpg_scribe.encounter.flask
from ttrpg_scribe.core.plugin import Plugin


class EncounterPlugin(Plugin):
    _blueprint = flask.Blueprint(import_name='ttrpg_scribe.encounter.flask.plugin',
        name='encounter_plugin',
        static_folder='static', template_folder='templates')

    @classmethod
    def create_app(cls, instance_path: Path, config: flask.Config) -> flask.Flask:
        if 'SYSTEM' not in config:
            raise ValueError('EncounterPlugin requires an active system plugin')
        return ttrpg_scribe.encounter.flask.create_app(instance_path, config['SYSTEM'], config)

    @classmethod
    def configure(cls, main_app: flask.Flask):
        main_app.register_blueprint(cls._blueprint, url_prefix='/encounter_plugin')
        tools: list[tuple[str, str, dict]] = main_app.config['TOOLS']
        tools += [
            ('/encounter', 'Launch Encounter', {'method': 'post'}),
            ('/encounter/party/configure', 'Configure Party', {}),
        ]
