from importlib import resources
from typing import Any, Mapping

import yaml

type Names = Mapping[str, list[str]]

with resources.open_text('ttrpg_scribe.npc', 'namelists.yaml') as file:
    __namelists: dict[str, Any] = yaml.safe_load(file)


def from_yaml(key: str) -> Names:
    return __namelists[key]


def combine(*namelists: Names) -> Names:
    combined = dict()
    for namelist in namelists:
        for kind, names in namelist.items():
            if kind not in combined:
                combined[kind] = names.copy()
            else:
                combined[kind] += names
    return combined


Dragonborn: Names = from_yaml('Dragonborn')
Dwarf: Names = from_yaml('Dwarf')
Elf: Names = from_yaml('Elf')
Gnome: Names = from_yaml('Gnome')
Halfling: Names = from_yaml('Halfling')
Orc: Names = from_yaml('Orc')
Tiefling: Names = from_yaml('Tiefling')
Calishite: Names = from_yaml('Calishite')
Chondathan: Names = from_yaml('Chondathan')
Damaran: Names = from_yaml('Damaran')
Illuskan: Names = from_yaml('Illuskan')
Mulan: Names = from_yaml('Mulan')
Rashemi: Names = from_yaml('Rashemi')
Shou: Names = from_yaml('Shou')
Turami: Names = from_yaml('Turami')
Human: Names = combine(Calishite, Chondathan, Damaran, Illuskan, Mulan, Rashemi, Shou, Turami)
Arabic: Names = from_yaml('Arabic')
Celtic: Names = from_yaml('Celtic')
Chinese: Names = from_yaml('Chinese')
Egyptian: Names = from_yaml('Egyptian')
English: Names = from_yaml('English')
French: Names = from_yaml('French')
German: Names = from_yaml('German')
Greek: Names = from_yaml('Greek')
Indian: Names = from_yaml('Indian')
Japanese: Names = from_yaml('Japanese')
Mesoamerican: Names = from_yaml('Mesoamerican')
NigerCongo: Names = from_yaml('NigerCongo')
Norse: Names = from_yaml('Norse')
Polynesian: Names = from_yaml('Polynesian')
Roman: Names = from_yaml('Roman')
Slavic: Names = from_yaml('Slavic')
Spanish: Names = from_yaml('Spanish')
