from typing import Any

from flask import Blueprint, Flask, render_template

from ttrpg_scribe.dnd_bestiary import apis
from ttrpg_scribe.dnd_bestiary.creature import DndCreature as DndCreature
from ttrpg_scribe.encounter.flask import InitiativeParticipant, SystemPlugin

blueprint = Blueprint('dnd_bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/compendium')


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
    def read_participant(cls, json) -> InitiativeParticipant:
        return DndCreature.from_json(json)

    @classmethod
    def encounter_xp(cls, enemies: list[tuple[int, DndCreature]],
                     allies: list[tuple[int, DndCreature]],
                     party: dict[str, dict[str, Any]]) -> str:
        total = sum(count * creature.xp for count, creature in enemies)
        return f'{total} ({total // len(party)} per player)'
