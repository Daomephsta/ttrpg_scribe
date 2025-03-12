from pathlib import Path

import flask

import ttrpg_scribe.npc.flask_app
from ttrpg_scribe.core.plugin import Plugin


class NpcPlugin(Plugin):
    _blueprint = flask.Blueprint(import_name='ttrpg_scribe.npc.flask_app.plugin',
        name='npc_plugin',
        static_folder='static', template_folder='templates')

    @classmethod
    def create_app(cls, instance_path: Path, config: flask.Config) -> flask.Flask:
        return ttrpg_scribe.npc.flask_app.create_app(instance_path, config)

    @classmethod
    def configure(cls, main_app: flask.Flask):
        main_app.register_blueprint(cls._blueprint, url_prefix='/npc_plugin')
        tools: list[tuple[str, str, dict]] = main_app.config['TOOLS']
        tools.append(('/npc/gui', 'NPC Generator', {}))
