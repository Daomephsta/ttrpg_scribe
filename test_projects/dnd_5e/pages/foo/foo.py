from ttrpg_scribe.dnd_bestiary.apis import DND5EAPI
from ttrpg_scribe.dnd_bestiary.creature.templates import rename

exports = {
    'CHICKEN': DND5EAPI.creature('eagle').derive(rename('Chicken'))
}
