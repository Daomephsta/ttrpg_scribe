from dataclasses import dataclass
from typing import Literal


@dataclass
class Sense:
    name: str
    range: int | None = None
    type Acuity = Literal['precise', 'imprecise', 'vague']
    acuity: Acuity | None = None
    description: str | None = None

    @staticmethod
    def from_json(data: dict):
        return Sense(
            name=data['name'],
            range=data['range'],
            acuity=data['acuity'],
            description=data['description'],
        )


def darkvision(range: int, acuity: Sense.Acuity, *, greater: bool = False) -> Sense:
    if not greater:
        return Sense('Darkvision', range, acuity, "A monster with darkvision can see perfectly well in areas of darkness and dim light, though such vision is in black and white only.")  # noqa: E501
    else:
        return Sense('Darkvision', range, acuity, "A monster with darkvision can see perfectly well in areas of darkness and dim light, though such vision is in black and white only. Some forms of magical darkness, such as a 4th-level darkness spell, block normal darkvision. A monster with greater darkvision, however, can see through even these forms of magical darkness.")  # noqa: E501


def lifesense(range: int, acuity: Sense.Acuity) -> Sense:
    return Sense('Lifesense', range, acuity, "Lifesense allows a monster to sense the vital essence of living and undead creatures within the listed range. The sense can distinguish between the vitality energy animating living creatures and the void energy animating undead creatures, much as sight distinguishes colors.")  # noqa: E501


def low_light_vision(range: int, acuity: Sense.Acuity) -> Sense:
    return Sense('Low-Light Vision', range, acuity, "The monster can see in dim light as though it were bright light, so it ignores the concealed condition due to dim light.")  # noqa: E501


def scent(range: int, acuity: Sense.Acuity) -> Sense:
    return Sense('Scent', range, acuity, """Scent involves sensing creatures or objects by smell and is usually a vague sense. The range is listed in the ability, and it functions only if the creature or object being detected emits an aroma (for instance, incorporeal creatures usually do not exude an aroma).
    If a creature emits a heavy aroma or is upwind, the GM can double or even triple the range of scent abilities used to detect that creature, and the GM can reduce the range if a creature is downwind."""  # noqa: E501
                       .replace('\n', '<br>'))


def tremorsense(range: int, acuity: Sense.Acuity) -> Sense:
    return Sense('Tremorsense', range, acuity, "Tremorsense allows a monster to feel the vibrations through a solid surface caused by movement. It is usually an imprecise sense with a limited range (listed in the ability). Tremorsense functions only if the monster is on the same surface as the subject, and only if the subject is moving along (or burrowing through) the surface.")  # noqa: E501


def wavesense(range: int, acuity: Sense.Acuity) -> Sense:
    return Sense('Wavesense', range, acuity, "This sense allows a monster to feel vibrations caused by movement through a liquid. It's usually an imprecise sense with a limited range (listed in the ability). Wavesense functions only if the monster and the subject are in the same body of liquid, and only if the subject is moving through the liquid.")  # noqa: E501
