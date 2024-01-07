import itertools
import random
from abc import ABC, abstractmethod
from http import HTTPStatus
from pathlib import Path

import flask

import dnd_scribe.core.flask


class Creature(ABC):
    name: str

    @abstractmethod
    def initiative_mod(self) -> int: ...

    @abstractmethod
    def default_hp(self) -> int: ...


class System:
    bestiary_blueprint: flask.Blueprint

    def read_creature(self, json) -> Creature:
        raise NotImplementedError()

    def encounter_xp(self, npcs, party) -> str:
        raise NotImplementedError()


def create_app(instance_path: str | Path, system: System):
    app = flask.Flask('dnd_scribe.encounter.flask',
        instance_path=Path(instance_path).absolute().as_posix(),
        instance_relative_config=True)
    app.config.from_pyfile('config.py')
    dnd_scribe.core.flask.extend(app)
    app.jinja_env.globals['system'] = system
    app.register_blueprint(system.bestiary_blueprint, url_prefix='/creatures')

    @app.post('/')
    def create_encounter():
        encounter = Encounter.from_json(flask.request.json) if flask.request.is_json\
            else Encounter([], flask.current_app.config['PARTY'], '')
        return flask.redirect(flask.url_for('view_encounter',
            id=Encounter.add(encounter),
            code=HTTPStatus.SEE_OTHER))

    @app.get('/<int:id>')
    def view_encounter(id: int):
        if Encounter.exists(id):
            encounter = Encounter.get(id)
            return flask.render_template('encounter_engine.j2.html', npcs=encounter.npcs,
                                         pcs=encounter.pcs, creatures=encounter.creatures.values(),
                                         description=encounter.description, encounter_id=id)
        return (f'Encounter {id} not found', HTTPStatus.NOT_FOUND)

    @app.post('/<int:id>')
    def reinforce_encounter(id: int):
        if Encounter.exists(id):
            encounter = Encounter.get(id)
            match flask.request.form['reinforcement_type']:
                case 'with_existing':
                    creature = encounter.creatures[flask.request.form['creature']]
                    for _ in range(int(flask.request.form['quantity'])):
                        encounter.add_npc(creature)
                case 'with_new':
                    for _ in range(int(flask.request.form['quantity'])):
                        encounter.add_simple_npc(
                            flask.request.form['name'],
                            int(flask.request.form['initiative_mod']),
                            int(flask.request.form['max_hp']))
            return ('Reinforced', HTTPStatus.NO_CONTENT)
        return (f'Encounter {id} not found', HTTPStatus.OK)

    @app.delete('/<int:id>')
    def delete_encounter(id: int):
        if Encounter.exists(id):
            Encounter.delete(id)
            return f'Encounter {id} deleted'
        return (f'Encounter {id} not found', HTTPStatus.NOT_FOUND)

    class __Encounter(type):
        _encounters: dict[int, 'Encounter'] = {}
        _ids = itertools.count()

        def add(self, encounter: 'Encounter') -> int:
            id = next(self._ids)
            self._encounters[id] = encounter
            return id

        def exists(self, id: int):
            return id in self._encounters

        def get(self, index: int):
            return self._encounters[index]

        def delete(self, index: int):
            del self._encounters[index]

        def __getitem__(self, index: int):
            return self._encounters[index]

    class Encounter(metaclass=__Encounter):
        def __init__(self, npc_specs: list[tuple[int, Creature]],
                     pcs: list[str], description: str):
            self.npcs = []
            self.creatures = {creature.name: creature for _, creature in npc_specs}
            self.pcs = pcs
            self.description = description
            self.npc_ids = itertools.count(start=1)
            for count, creature in npc_specs:
                for _ in range(count):
                    self.add_npc(creature)

        @staticmethod
        def from_json(json):
            return Encounter([(count, system.read_creature(creature_json))
                for [count, creature_json] in json['npcs']], json['pcs'], json['description'])

        def add_simple_npc(self, name: str, initiative_mod: int, initial_hp):
            return self.npcs.append(dict(
                name=f'{name} {next(self.npc_ids)}',
                initiative=random.randint(1, 20) + initiative_mod,
                initial_hp=initial_hp))

        def add_npc(self, creature: Creature):
            self.add_simple_npc(
                name=creature.name,
                initiative_mod=creature.initiative_mod(),
                initial_hp=creature.default_hp())

    return app
