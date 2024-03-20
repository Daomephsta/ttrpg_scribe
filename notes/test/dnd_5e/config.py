from ttrpg_scribe.npc import namelists
from ttrpg_scribe.npc.entity import FormattedNamer
from ttrpg_scribe.npc.race import phb

SYSTEM = 'dnd_5e'

REGIONS = {
    'Default': {
        'cultures': {
            'English': 1
        }
    }
}

CULTURES = {
    'English': {
        'namer': FormattedNamer(['Gender', 'Group'], namelists.English),
        'races': {
            phb.HUMAN: 16,
            phb.HALFLING: 16,
            phb.HALF_ORC: 16,
            phb.DWARF: 8,
            phb.GNOME: 8,
            phb.DRAGONBORN: 4,
            phb.TIEFLING: 4,
            phb.ELF: 2,
            phb.HALF_ELF: 1,
        },
    }
}

PARTY = ['Alice', 'Bob', 'Charlie', 'Danielle']
