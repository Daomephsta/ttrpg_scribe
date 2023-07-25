from pathlib import Path
from typing import OrderedDict

import flask

import dnd_scribe.core.flask
from dnd_scribe.npc import Features
from dnd_scribe.npc.template import Template
from npc.dnd_scribe.npc.race import Race


def create_app(instance_path: str):
    app = flask.Flask('dnd_scribe.npc.flask_app',
        instance_path=Path(instance_path).absolute().as_posix(),
        instance_relative_config=True)
    app.config.from_pyfile('config.py')
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
        read_features = OrderedDict()
        for feature_id, value in flask.request.form.items():
            feature = Features.BY_NAME[feature_id]
            read_features[feature] = feature.from_str(read_features, value) if value else None
        template_features = ((feature, value) if value else feature
            for feature, value in read_features.items())
        entity = Template(*template_features).into_entity()
        entity_features={feature.display: feature.to_str(entity[feature])
            for feature in entity.feature_order if feature != Features.REGION}
        return entity_features

    return app