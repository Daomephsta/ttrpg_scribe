from dnd_scribe.npc.race import Race

DWARF = Race('Dwarf',
    subraces={'Hill': {}, 'Mountain': {}})
ELF = Race('Elf',
    subraces={'High': {}, 'Wood': {}})
HALFLING = Race('Halfling',
    subraces={'Stout': {}, 'Lightfoot': {}})
HUMAN = Race('Human')
GNOME = Race('Gnome',
    subraces={'Deep': {}, 'Forest': {}, 'Rock': {}})
HALF_ELF = Race('Half-Elf')
HALF_ORC = Race('Half-Orc')
DRAGONBORN = Race('Dragonborn', subraces={
    'Black': {}, 'Blue': {}, 'Green': {}, 'Red': {}, 'White': {},
    'Brass': {}, 'Bronze': {}, 'Copper': {}, 'Gold': {}, 'Silver': {}
})
TIEFLING = Race('Tiefling')
