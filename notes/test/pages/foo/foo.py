from dnd_scribe.bestiary.apis import DND5EAPI
from dnd_scribe.bestiary.creature.templates import rename

exports = {
    'CHICKEN': DND5EAPI.creature('eagle').derive(rename('Chicken'))
}
