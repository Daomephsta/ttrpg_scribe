from dnd_scribe.bestiary.apis import DND5EAPI

exports = {
    'CHICKEN': DND5EAPI.creature('eagle').derive(name='Chicken')
}
