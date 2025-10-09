from . import phb

DRAGONBORN = phb.DRAGONBORN.derive(subraces={
    'Black': {}, 'Blue': {}, 'Green': {}, 'Red': {}, 'White': {},  # Chromatic
    'Brass': {}, 'Bronze': {}, 'Copper': {}, 'Gold': {}, 'Silver': {},  # Metallic
    'Amethyst': {}, 'Crystal': {}, 'Emerald': {}, 'Sapphire': {}, 'Topaz': {}})  # Gem
