from typing import Any, cast

import flask
from flask import Blueprint, Flask, render_template

import ttrpg_scribe.core.typescript
from ttrpg_scribe.dnd_bestiary import apis
from ttrpg_scribe.dnd_bestiary.creature import DndCreature as DndCreature
from ttrpg_scribe.encounter.flask import (EncounterSpec, InitiativeParticipant,
                                          SystemPlugin)

blueprint = Blueprint('dnd_bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')
ttrpg_scribe.core.typescript.extend(blueprint)


@blueprint.get('/view/<string:id>')
def creature(id: str):
    creature = apis.DND5EAPI.creature(id)
    return render_template('creature.j2.html',
                           creature=creature, render=True)


def create_app():
    app = Flask('ttrpg_scribe.dnd_bestiary.flask')
    app.register_blueprint(blueprint)
    return app


class Dnd5ePlugin(SystemPlugin):
    compendium_blueprint = blueprint

    @classmethod
    def read_participant(cls, data, extra={}) -> InitiativeParticipant:
        return DndCreature.from_json(data)

    @classmethod
    def encounter_xp(cls, encounter: EncounterSpec) -> str:
        party: dict[str, dict[str, Any]] = flask.current_app.config['PARTY']
        total = sum(count * cast(DndCreature, creature).xp
                    for count, creature in encounter.enemies)
        return f'{total} ({total // len(party)} per player)'
