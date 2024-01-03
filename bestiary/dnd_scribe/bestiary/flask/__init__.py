from typing import Any

from flask import Blueprint, Flask, render_template

from dnd_scribe.bestiary import apis
from dnd_scribe.bestiary.creature import DndCreature as DndCreature
from dnd_scribe.encounter.flask import Creature, System

blueprint = Blueprint('bestiary', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/creatures')


@blueprint.get('/view/<string:id>')
def creature(id: str):
    creature = apis.DND5EAPI.creature(id)
    return render_template('creature.j2.html',
                           creature=creature, render=True)


def create_app():
    app = Flask('dnd_scribe.bestiary.flask')
    app.register_blueprint(blueprint)
    return app


class Dnd5eSystem(System):
    bestiary_blueprint = blueprint

    def read_creature(self, json) -> Creature:
        return DndCreature.from_json(json)

    def encounter_xp(self, npcs: list[tuple[int, DndCreature]],
                     party: dict[str, dict[str, Any]]) -> str:
        total = sum(count * creature.xp for count, creature in npcs)
        return f'{total} ({total // len(party)} per player)'
