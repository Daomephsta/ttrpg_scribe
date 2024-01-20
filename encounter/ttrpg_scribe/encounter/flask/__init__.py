import itertools
import random
from abc import ABC, abstractmethod
from http import HTTPStatus
from pathlib import Path
from typing import Any

import flask

import ttrpg_scribe.core.flask


class InitiativeParticipant(ABC):
    name: str

    def kind(self):
        return self.__class__.__name__

    def to_json(self) -> dict[str, Any]:
        data = dict(kind=self.kind())
        self.write_json(data)
        return data

    @abstractmethod
    def write_json(self, data: dict[str, Any]): ...

    @abstractmethod
    def initiative_mod(self) -> int: ...

    @abstractmethod
    def default_hp(self) -> int: ...


class System:
    bestiary_blueprint: flask.Blueprint

    def read_participant(self, json) -> InitiativeParticipant:
        raise NotImplementedError()

    def encounter_xp(self, enemies, allies, party) -> str:
        raise NotImplementedError()


def create_app(instance_path: str | Path, system: System, config: Path):
    app = flask.Flask('ttrpg_scribe.encounter.flask',
        instance_path=Path(instance_path).absolute().as_posix(),
        instance_relative_config=True)
    app.config.from_pyfile(config)
    ttrpg_scribe.core.flask.extend(app)
    app.jinja_env.globals['system'] = system
    app.register_blueprint(system.bestiary_blueprint, url_prefix='/creatures')

    @app.post('/')
    def create_encounter():
        encounter = Encounter.from_json(flask.request.json) if flask.request.is_json\
            else Encounter([], [], flask.current_app.config['PARTY'], '')
        return flask.redirect(flask.url_for('view_encounter',
            id=Encounter.add(encounter),
            code=HTTPStatus.SEE_OTHER))

    @app.get('/<int:id>')
    def view_encounter(id: int):
        if Encounter.exists(id):
            encounter = Encounter.get(id)
            return flask.render_template('encounter_engine.j2.html',
                                         enemies=encounter.enemies, allies=encounter.allies,
                                         pcs=encounter.pcs,
                                         stat_block_data=encounter.stat_block_data.values(),
                                         description=encounter.description, encounter_id=id)
        return (f'Encounter {id} not found', HTTPStatus.NOT_FOUND)

    @app.post('/<int:id>')
    def reinforce_encounter(id: int):
        if Encounter.exists(id):
            encounter = Encounter.get(id)
            match flask.request.form['reinforcement_type']:
                case 'with_existing':
                    creature = encounter.stat_block_data[flask.request.form['stats']]
                    for _ in range(int(flask.request.form['quantity'])):
                        encounter.add_npc(creature, flask.request.form['side'])
                case 'with_new':
                    for _ in range(int(flask.request.form['quantity'])):
                        encounter.add_simple_npc(
                            flask.request.form['name'],
                            int(flask.request.form['initiative_mod']),
                            int(flask.request.form['max_hp']),
                            flask.request.form['side'])
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
        def __init__(self, enemies: list[tuple[int, InitiativeParticipant]],
                     allies: list[tuple[int, InitiativeParticipant]],
                     pcs: list[str], description: str):
            self.enemies = []
            self.allies = []
            self.stat_block_data = {participant.name: participant
                                    for _, participant in itertools.chain(enemies, allies)}
            self.pcs = pcs
            self.description = description
            self.npc_ids = itertools.count(start=1)
            for count, participant in enemies:
                for _ in range(count):
                    self.add_npc(participant, 'enemy')
            for count, participant in allies:
                for _ in range(count):
                    self.add_npc(participant, 'ally')

        @staticmethod
        def from_json(json):
            def read_participants(key: str):
                return [(count, system.read_participant(participant))
                        for [count, participant] in json[key]]
            return Encounter(read_participants('enemies'), read_participants('allies'),
                             json['pcs'], json['description'])

        def add_simple_npc(self, name: str, initiative_mod: int, initial_hp, side: str):
            side_npcs = self.allies if side == 'ally' else self.enemies
            return side_npcs.append(dict(
                name=f'{name} {next(self.npc_ids)}',
                initiative=random.randint(1, 20) + initiative_mod,
                initial_hp=initial_hp))

        def add_npc(self, participant: InitiativeParticipant, side: str):
            self.add_simple_npc(
                name=participant.name,
                initiative_mod=participant.initiative_mod(),
                initial_hp=participant.default_hp(),
                side=side)

    return app
