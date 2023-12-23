from pathlib import Path

import flask
from flask_session import Session
from werkzeug.exceptions import Forbidden, NotFound

import dnd_scribe.core.flask
from dnd_scribe.npc.entity import Entity, EntityGenerator, Features


def create_app(instance_path: str | Path):
    instance_path = Path(instance_path).absolute().as_posix()
    app = flask.Flask('dnd_scribe.npc.flask_app',
        instance_path=instance_path,
        instance_relative_config=True)
    app.config.from_pyfile('config.py')
    app.config.update(SESSION_TYPE='filesystem',
                      SESSION_PERMANENT=False,
                      SESSION_FILE_DIR=f'{instance_path}/_build/_session')

    Session().init_app(app)
    dnd_scribe.core.flask.extend(app)
    npc_generator = EntityGenerator(config=app.config)

    @app.get('/gui')
    def npc_generator_gui():
        def race_data(race):
            return (
                race.name,
                [(subrace.name, subrace.subname) for subrace in race.subraces.values()]
            )
        regions = {
            region_name: {
                'races': [race_data(race) for race in data['races'].keys()],
                'cultures': list(data['cultures'].keys())
            } for region_name, data in app.config['REGIONS'].items()
        }

        all_races = set()
        for _, data in app.config['REGIONS'].items():
            all_races.update(data['races'])
        all_races = [race_data(race) for race in all_races]

        return flask.render_template('npc_generator.j2.html',
            regions=regions,
            all_races=all_races,
            all_cultures=list(app.config['CULTURES'].keys()))

    @app.post('/generate')
    def generate_npc():
        features = dict()
        for feature_id, value in flask.request.form.items():
            Features[feature_id].read_into(features, value)
        entity = npc_generator.generate(features)
        flask.session['current_npc'] = entity
        return entity.for_display(
            order=list(features.keys()),
            exclude=[Features.REGION])

    npcs = Path(app.instance_path)/'npcs'
    npcs.mkdir(exist_ok=True)

    @app.post('/save')
    def save_npc():
        if 'current_npc' in flask.session:
            npc: Entity = flask.session['current_npc']
            path = npcs/f"{npc.name}.json"
            if path.exists():
                raise Forbidden(f'{npc.name} is already in use')
            path.write_text(flask.json.dumps(npc.for_display(order=[
                Features.NAME, Features.AGE, Features.RACE, Features.SUBRACE,
                Features.SEX, Features.HEIGHT, Features.WEIGHT,
                Features.HIGH_STAT, Features.LOW_STAT, Features.APPEARANCE,
                Features.POSITIVE_PERSONALITY, Features.NEGATIVE_PERSONALITY,
                Features.MANNERISM]), indent=4))
            return f"Saved {npc.name}"
        raise Forbidden('No NPCs have been generated during this session')

    @app.get('/view')
    def list_npcs():
        return flask.render_template('npc_list.j2.html',
            npcs=[(path.stem, path.stem) for path in npcs.glob('*.json')])

    @app.get('/view/<name>')
    def view_npc(name):
        path = npcs/f'{name}.json'
        if not path.exists():
            raise NotFound(f'No NPC named {name}')
        npc = [tuple(pair) for pair in flask.json.loads(path.read_text())]
        [name] = [v for f, v in npc if f == 'Name']
        return flask.render_template('npc.j2.html', name=name, npc=npc)

    return app
