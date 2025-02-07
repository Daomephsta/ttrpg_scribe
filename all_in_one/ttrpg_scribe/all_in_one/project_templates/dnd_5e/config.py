from ttrpg_scribe.npc import namelists
from ttrpg_scribe.npc.entity import FormattedNamer
from ttrpg_scribe.npc.race import phb

PLUGINS = ['dnd_5e', 'encounter', 'npc']

REGIONS = {
    'Default': {
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
        'cultures': {
            'English': 1
        }
    }
}

CULTURES = {
    'English': FormattedNamer(['Gender', 'Group'], namelists.English)
}

PARTY = ['Alice', 'Bob', 'Charlie', 'Danielle']
