from typing import Literal

from ttrpg_scribe.core.dice import Dice, d

from . import DndCreature
from .ability import DEX, STR, Ability

type DamageType = Literal['acid', 'bludgeoning', 'cold', 'fire', 'force', 'lightning', 'necrotic', 'piercing', 'poison', 'psychic', 'radiant', 'slashing', 'thunder']  # noqa: E501


class Attack:
    default_ability = STR

    def __init__(self, name: str, dice: Dice, type: DamageType,
                 ability: Ability | None, attack: int | None, damage_bonus: int | None,
                 range: str, extra: str):
        self.name = name
        self.dice = dice
        self.type = type
        self.attack = attack
        self.damage_bonus = damage_bonus
        self.ability = ability if ability else self.default_ability
        self.range = range
        self.extra = extra

    def describe(self, attack_mod: int, damage: str) -> str:
        raise NotImplementedError

    def __call__(self, creature: DndCreature) -> tuple[str, str]:
        if self.damage_bonus is not None:
            damage = self.dice + self.damage_bonus
        else:
            damage = self.dice + self.ability.mod(creature)
        attack_mod = self.attack if self.attack is not None\
            else self.ability.mod(creature) + creature.prof
        desc = self.describe(attack_mod, f'{damage.damage_notation()} {self.type}')
        if self.extra:
            if self.extra[0].isupper():
                desc += '.'
            desc += f' {self.extra}'
        else:
            desc += '.'
        return (self.name, desc)


class Melee(Attack):
    def __init__(self, name: str, dice: Dice, type: DamageType,
                 ability: Ability | None = None, attack: int | None = None,
                 damage_bonus: int | None = None, reach: int = 5, extra: str = ''):

        super().__init__(name, dice, type, ability, attack, damage_bonus,
            f'{reach} ft.', extra)

    def describe(self, attack_mod: int, damage: str) -> str:
        return f'*Melee Weapon Attack*: {attack_mod:+d} to hit, '\
               f'reach {self.range}, one target. *Hit*: {damage} damage'


class Ranged(Attack):
    default_ability = DEX

    def __init__(self, name: str, range: tuple[int, int], dice: Dice,
                 type: DamageType, ability: Ability | None = None,
                 attack: int | None = None, damage_bonus: int | None = None, extra: str = ''):

        super().__init__(name, dice, type, ability,  attack, damage_bonus,
            f"{range[0]}/{range[1]} ft.", extra)

    def describe(self, attack_mod: int, damage: str) -> str:
        return f'*Ranged Weapon Attack*: {attack_mod:+d} to hit, '\
               f'range {self.range}, one target. *Hit*: {damage} damage'


def thrown(name: str, range: tuple[int, int], dice: Dice, type: DamageType):
    def weapon(ability: Ability = DEX) -> list[Attack]:
        return [
            Melee(name, dice, type, ability),
            Ranged(f'Throw {name}', range, dice, type, ability)
        ]
    return weapon


def versatile(name: str, dice_1h: Dice, dice_2h: Dice, type: DamageType):
    return [
        Melee(f'{name} (1H)', dice_1h, type),
        Melee(f'{name} (2H)', dice_2h, type),
    ]


# Simple Melee Weapons
club = Melee('Club', d(4), 'bludgeoning')
dagger = thrown('Dagger', (20, 60), d(4), 'piercing')
greatclub = Melee('Greatclub', d(8), 'bludgeoning')
handaxe = thrown('Handaxe', (20, 60), d(6), 'slashing')
javelin = thrown('Javelin', (30, 120), d(6), 'piercing')(STR)
light_hammer = thrown('Light Hammer', (20, 60), d(4), 'bludgeoning')(STR)
mace = Melee('Mace', d(6), 'bludgeoning')
quarterstaff = versatile('Quarterstaff', d(6), d(8), 'bludgeoning')
sickle = Melee('Sickle', d(4), 'slashing')
spear = [
    Melee('Spear (1H)', d(6), 'piercing'),
    Melee('Spear (2H)', d(8), 'piercing'),
    Ranged('Throw Spear', (20, 60), d(6), 'piercing', STR)
]

# Simple Ranged Weapons
light_crossbow = Ranged('Light Crossbow', (80, 320), d(8), 'piercing')
def dart(ability: Ability = DEX):  # noqa: E302
    return Ranged('Dart', (20, 60), d(4), 'piercing', ability)
shortbow = Ranged('Shortbow', (80, 320), d(6), 'piercing')  # noqa: E305
sling = Ranged('Sling', (30, 120), d(4), 'bludgeoning')

# Martial Melee Weapons
battleaxe = versatile('Battleaxe', d(8), d(10), 'slashing')
flail = Melee('Flail', d(8), 'bludgeoning')
glaive = Melee('Glaive', d(10), 'slashing')
greataxe = Melee('Greataxe', d(12), 'slashing')
greatsword = Melee('Greatsword', 2 * d(6), 'slashing')
halberd = Melee('Halberd', d(10), 'slashing')
lance = Melee('Lance', d(12), 'piercing')
longsword = Melee('Longsword', d(8), 'slashing')
maul = Melee('Maul', 2 * d(6), 'bludgeoning')
morningstar = Melee('Morningstar', 1 * d(8), 'piercing')
pike = Melee('Pike', 1 * d(10), 'piercing')
def rapier(ability: Ability = DEX):  # noqa: E302
    return Melee('Rapier', 1 * d(8), 'piercing', ability)
def scimitar(ability: Ability = DEX):  # noqa: E302
    return Melee('Scimitar', 1 * d(6), 'slashing', ability)
def shortsword(ability: Ability = DEX):  # noqa: E302
    return Melee('Shortsword', 1 * d(6), 'piercing', ability)
trident = [  # noqa: E305
    Melee('Trident (1H)', d(6), 'piercing'),
    Melee('Trident (2H)', d(8), 'piercing'),
    Ranged('Throw Trident', (20, 60), d(6), 'piercing', STR)
]
war_pick = Melee('War pick', 1 * d(8), 'piercing')
warhammer = versatile('Warhammer', d(8), d(10), 'bludgeoning')
def whip(ability: Ability = DEX):  # noqa: E302
    return Melee('Whip', 1 * d(4), 'slashing', ability)

# Martial Ranged Weapons
hand_crossbow = Ranged('Hand crossbow', (30, 120), d(6), 'piercing')  # noqa: E305
heavy_crossbow = Ranged('Heavy crossbow', (100, 400), d(10), 'piercing')
longbow = Ranged('Longbow', (150, 600), d(8), 'piercing')
