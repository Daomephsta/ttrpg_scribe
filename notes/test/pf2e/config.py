from ttrpg_scribe.npc import namelists
from ttrpg_scribe.npc.entity import FormattedNamer
from ttrpg_scribe.npc.race import Race

PLUGINS = ['pf2e', 'encounter', 'npc']

halfling = Race('Halfling', ['Gutsy', 'Hillock', 'Jinxed', 'Nomadic',
                             'Observant', 'Twilight', 'Wildwood'])

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
            Race('Human', ['Skilled', 'Versatile', 'Wintertouched']): 16,
            halfling: {
                'Gutsy': 2, 'Hillock': 3, 'Jinxed': 1, 'Nomadic': 2,
                'Observant': 2, 'Twilight': 2, 'Wildwood': 3
            },
            Race('Half-Orc'): 16,
            Race('Dwarf', ['Ancient-Blooded', 'Anvil', 'Death Warden',
                           'Elemental Heart', 'Forge-Blessed', 'Oathkeeper',
                           'Rock', 'Strong-Blooded']): 8,
            Race('Gnome', ['Fey-Touched', 'Sensate', 'Umbral', 'Vivacious',
                           'Wellspring']): 8,
            Race('Goblin', ['Charhide', 'Irongut', 'Razortooth', 'Snow',
                            'Tailed', 'Treedweller', 'Unbreakable']): 4,
            Race('Elf', ['Ancient', 'Arctic', 'Cavern', 'Desert', 'Seer',
                         'Whisper', 'Woodland']): 2,
            Race('Half-Elf'): 1,
        }
    }
}

PARTY = ['Alice', 'Bob', 'Charlie', 'Danielle']
PARTY_LEVEL = 1
