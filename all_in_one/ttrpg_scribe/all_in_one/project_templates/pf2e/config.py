from ttrpg_scribe.npc import namelists
from ttrpg_scribe.npc.entity import FormattedNamer
from ttrpg_scribe.npc.race.pf2e import (DWARF, ELF, GNOME, GOBLIN, HALF_ELF,
                                        HALF_ORC, HALFLING, HUMAN)

SYSTEM = 'pf2e'

REGIONS = {
    'Default': {
        'races': {
            HUMAN: 16,
            HALFLING: {
                'Gutsy': 2, 'Hillock': 3, 'Jinxed': 1, 'Nomadic': 2,
                'Observant': 2, 'Twilight': 2, 'Wildwood': 3
            },
            HALF_ORC: 16,
            DWARF: 8,
            GNOME: 8,
            GOBLIN: 4,
            ELF: 2,
            HALF_ELF: 1,
        },
        'cultures': {
            'English': 1
        }
    }
}

CULTURES = {
    'English': FormattedNamer(['Gender', 'Group'], namelists.English)
}

PARTY = ['Alice', 'Bob', 'Charlie', 'Danielle']
PARTY_LEVEL = 1
