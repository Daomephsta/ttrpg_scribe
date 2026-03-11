from ttrpg_scribe.pf2e_compendium.actor.templates import rename
from ttrpg_scribe.pf2e_compendium.foundry import packs as foundry_packs

exports = {
    'CHICKEN': foundry_packs.creature('pathfinder-monster-core/eagle')
        .apply(rename('Chicken'))
}
