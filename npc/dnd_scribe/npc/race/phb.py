from dnd_scribe.npc import namelists
from dnd_scribe.npc.race import Race

DWARF = Race('Dwarf', ['Gender', 'Group'], namelists.Dwarf,
    subraces={'Hill': {}, 'Mountain': {}})
ELF = Race('Elf', ['Gender', 'Child', 'Group'], namelists.Elf,
    subraces={'High': {}, 'Wood': {}})
HALFLING = Race('Halfling', ['Gender', 'Group'], namelists.Halfling,
    subraces={'Stout': {}, 'Lightfoot': {}})
HUMAN = Race('Human', ['Gender', 'Group'], namelists.Human)
GNOME = Race('Gnome', ['Gender', 'Nickname', 'Group'], namelists.Gnome,
    subraces={'Deep': {}, 'Forest': {}, 'Rock': {}})
HALF_ELF = Race('Half-Elf', ['Gender', 'Group'],
    namelists.combine(namelists.Human, namelists.Elf))
HALF_ORC = Race('Half-Orc', ['Gender', 'Group'],
    namelists.combine(namelists.Human, namelists.Orc))
DRAGONBORN = Race('Dragonborn', ['Gender', 'Child', 'Group'], namelists.Dragonborn,
    subraces={'Black': {}, 'Blue': {}, 'Green': {}, 'Red': {}, 'White': {}, 'Brass': {}, 'Bronze': {}, 'Copper': {}, 'Gold': {}, 'Silver': {}})
TIEFLING = Race('Tiefling', [['Gender', 'Virtue'], 'Group'],
    namelists.combine(namelists.Tiefling, namelists.Human))
