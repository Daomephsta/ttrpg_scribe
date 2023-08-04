from pathlib import Path

import flask
from flask_session import Session
from werkzeug.exceptions import Forbidden

import dnd_scribe.core.flask
from dnd_scribe.npc import EntityGenerator, Features
from dnd_scribe.npc.race import Race


def create_app(instance_path: str):
    instance_path = Path(instance_path).absolute().as_posix()
    app = flask.Flask('dnd_scribe.npc.flask_app',
        instance_path=instance_path,
        instance_relative_config=True)
    app.config.from_pyfile('config.py')
    app.config.update(SESSION_TYPE = 'filesystem',
                      SESSION_PERMANENT = False,
                      SESSION_FILE_DIR = f'{instance_path}/_build/_session')
    Session().init_app(app)
    dnd_scribe.core.flask.extend(app)
    npc_generator = EntityGenerator(config=app.config)

    @app.get('/gui')
    def npc_generator_gui():
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
        entity = npc_generator.generate(*template_features)
        flask.session['current_npc'] = entity.to_json()
        return entity.for_display(
            order=list(features_by_id.keys()),
            exclude=[Features.REGION])

    npcs = Path(app.instance_path)/'npcs'
    npcs.mkdir(exist_ok=True)

    @app.post('/save')
    def save_npc():
        if 'current_npc' in flask.session:
            npc = flask.session['current_npc']
            path = npcs/f"{npc['name']}.json"
            path.write_text(flask.json.dumps(npc, indent=4))
            return f"Saved {npc['name']}"
        raise Forbidden('No NPCs have been generated during this session')

    return app