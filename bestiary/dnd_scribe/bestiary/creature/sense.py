from dataclasses import dataclass


@dataclass
class Sense:
    name: str
    range: int
    condition: str = ''

    @staticmethod
    def parse(name: str, value: str):
        value, condition = map(str.strip, value.split(' ft.'))
        return Sense(name, int(value), condition)

    def to_json(self):
        return {
            'name': self.name,
            'range': self.range,
            'condition': self.condition
        }

    @staticmethod
    def from_json(json):
        return Sense(**json)

    def __str__(self) -> str:
        return f'{self.name} {self.range} ft. {self.condition}'\
        if self.condition else f'{self.name} {self.range} ft.'

def Blindsight(range: int):
    return Sense('Blindsight', range)

def Darkvision(range: int):
    return Sense('Darkvision', range)

def Truesight(range: int):
    return Sense('Truesight', range)