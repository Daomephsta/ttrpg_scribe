from dataclasses import dataclass
from typing import Any

import flask

from ttrpg_scribe.pf2e_compendium.foundry import mongo_client

_blueprint = flask.Blueprint('oracle', __name__, static_folder='static',
                      template_folder='templates', url_prefix='/oracle')


@_blueprint.get('/encounter')
def encounter_ui():
    return flask.render_template('oracle/encounter.j2.html')


@_blueprint.post('/encounter')
def encounter():
    return EncounterSpecification.from_json(flask.request.get_json()).resolve()


def extend(app: flask.Flask):
    app.register_blueprint(_blueprint)


_SIZES = {
    'tiny': 'tiny', 'small': 'sm', 'medium': 'med',
    'large': 'lg', 'huge': 'huge', 'gargantuan': 'grg'
}


@dataclass
class EncounterSpecification:
    @dataclass
    class CombatantSpecification:
        quantity: int
        level: int | tuple[int, int] | None
        rarities: list[str] | None
        sizes: list[str] | None
        traits: list[str] | None

        def __init__(self, quantity: int, level: int | tuple[int, int] | None = None,
                     rarities: list[str] | None = None, sizes: list[str] | None = None,
                     traits: list[str] | None = None):
            self.quantity = quantity
            self.level = level
            self.rarities = rarities
            self.sizes = sizes
            self.traits = traits

        @classmethod
        def from_json(cls, json: dict[str, Any]):
            return EncounterSpecification.CombatantSpecification(
                json['quantity'],
                (json['level-min'], json['level-max']),
                json['rarity'],
                json['size'],
                None
            )

        def to_mongo_query(self) -> dict:
            query = {}
            match self.level:
                case int() as level:
                    query['system.details.level.value'] = level
                case int() as min_level, int() as max_level:
                    query['system.details.level.value'] = {'$gte': min_level, '$lte': max_level}
                case None:
                    pass
            if self.rarities is not None:
                query['system.traits.rarity'] = {'$in': self.rarities}
            if self.sizes is not None:
                query['system.traits.size.value'] = {'$in': [_SIZES[s] for s in self.sizes]}
            if self.traits is not None:
                query['system.traits.value'] = {'$all': self.traits}
            return query

    combatants: list[CombatantSpecification]

    @classmethod
    def from_json(cls, json: list[dict[str, Any]]):
        return EncounterSpecification([EncounterSpecification.CombatantSpecification.from_json(e)
                                       for e in json])

    def resolve(self):
        def to_pipeline(spec: EncounterSpecification.CombatantSpecification):
            return [
                {'$match': spec.to_mongo_query()},
                {'$sample': {'size': 1}},
                {
                    '$project': {
                        '_id': 0,
                        'name': 1,
                        'level': '$system.details.level.value',
                        'rarity': '$system.traits.rarity'
                    }
                }
            ]

        pipeline = [{
                '$facet': {
                    f'combatant{i}': to_pipeline(spec)
                    for i, spec in enumerate(self.combatants)
                }
            },
            {
                '$project': {
                    f'combatant{i}': {'$first': f'$combatant{i}'}
                    for i in range(len(self.combatants))
                }
            }
        ]
        [results] = list(mongo_client.db.npc.aggregate(pipeline))
        return [{'quantity': c.quantity, **r} for c, r in zip(self.combatants, results.values())]
