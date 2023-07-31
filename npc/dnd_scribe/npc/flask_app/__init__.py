from pathlib import Path

import flask
from flask_session import Session
from werkzeug.exceptions import Forbidden

import dnd_scribe.core.flask
import dnd_scribe.npc.database
from dnd_scribe.npc import Features
from dnd_scribe.npc.race import Race
from dnd_scribe.npc.template import Template


def create_app(instance_path: str):
    instance_path = Path(instance_path).absolute().as_posix()
    app = flask.Flask('dnd_scribe.npc.flask_app',
        instance_path=instance_path,
        instance_relative_config=True)
    app.config.from_pyfile('config.py')
    app.config['SESSION_FILE_DIR'] = instance_path
    Session().init_app(app)
    dnd_scribe.core.flask.extend(app)

    @app.get('/gui')
    def npc_generator():
        race_weights: dict[str, dict[Race, int]] = app.config['RACE_WEIGHTS']
        races = [(race.name, list(race.subraces.values()))
                for race in race_weights['']]
        for _, subraces in races:
            subraces.sort(key=lambda x: x.name)
        races.sort()
        return flask.render_template('npc_generator.j2.html',
            regions=((r, r.title()) if r else ('', 'Default')
                for r in race_weights.keys()),
            races=races)

    @app.post('/generate')
    def generate_npc():
        features_by_id = dict()
        for feature_id, value in flask.request.form.items():
            Features[feature_id].read_into(features_by_id, value)
        template_features = ((feature, value) if value else feature
            for feature, value in features_by_id.items())
        entity = Template.from_entries(*template_features).into_entity()
        flask.session['current_npc'] = entity
        return {feature.display: feature.to_str(value)
            for feature, value in entity if feature != Features.REGION}

    return app