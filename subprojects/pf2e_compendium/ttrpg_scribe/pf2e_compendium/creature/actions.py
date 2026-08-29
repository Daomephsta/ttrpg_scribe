from typing import Literal

from ttrpg_scribe.core.dice import SimpleDice
from ttrpg_scribe.pf2e_compendium.actions import (Action, defensive,
                                                  interaction, offensive)


def all_around_vision() -> Action:
    return defensive('All-Around Vision', "The monster can see in all directions simultaneously and therefore can't be flanked.", cost=0)  # noqa: E501


def aquatic_ambush(*, range: int) -> Action:
    return offensive('Aquatic Ambush',
                     f"Requirements</b> The monster is hiding in water and a creature that hasn't detected it is within {range} feet; <b>Effect</b> The monster moves up to its swim Speed + 10 feet toward the triggering creature, traveling on water and on land. Once the creature is in reach, the monster makes a Strike against it. The creature is off-guard against this Strike.",  # noqa: E501
                     cost=1)


def buck(*, dc: int) -> Action:
    return defensive('Buck', f"<b>Trigger</b> A creature Mounts or uses the Command an Animal action while riding the monster; <b>Effect</b> The triggering creature must succeed at a DC {dc} Reflex saving throw or fall off the creature and land prone. If the save is a critical failure, the triggering creature also takes 1d6 bludgeoning damage in addition to the normal damage for the fall",  # noqa: E501
                     cost='reaction')


def catch_rock() -> Action:
    return defensive('Catch Rock', "<b>Requirements</b> The monster must have a free hand but can Release anything it's holding as part of this reaction. <b>Trigger</b> The monster is targeted with a thrown rock Strike or a rock would fall on the monster. <b>Effect</b> The monster gains a +4 circumstance bonus to its AC against the triggering attack or to any defense against the falling rock. If the attack misses or the monster successfully defends against the falling rock, the monster catches the rock, takes no damage, and is now holding the rock.",  # noqa: E501
                     cost='reaction')


def change_shape(tradition: Literal['arcane', 'divine', 'occult', 'primal']) -> Action:
    return offensive('Change Shape', "The monster changes its shape indefinitely. It can use this action again to return to its natural shape or adopt a new shape. Unless otherwise noted, a monster cannot use Change Shape to appear as a specific individual. Using Change Shape counts as creating a disguise for the Impersonate use of Deception. The monster's transformation automatically defeats Perception DCs to determine whether the creature is a member of the ancestry or creature type into which it transformed, and it gains a +4 status bonus to its Deception DC to prevent others from seeing through its disguise. Change Shape abilities specify what shapes the monster can adopt. The monster doesn't gain any special abilities of the new shape, only its physical form. For example, in each shape, it replaces its normal Speeds and Strikes, and might potentially change its senses or size. Any changes are listed in its stat block.",  # noqa: E501
                     traits=['concentrate', tradition, 'polymorph'])


def constrict(damage: SimpleDice, damage_type: str, *, dc: int, greater: bool = False) -> Action:
    if not greater:
        return offensive('Constrict', f"The monster deals {damage} {damage_type} damage to any number of creatures grabbed or restrained by it. Each of those creatures can attempt a DC {dc} basic Fortitude save.")  # noqa: E501
    else:
        return offensive('Greater Constrict', f"The monster deals {damage} {damage_type} damage to any number of creatures grabbed or restrained by it. Each of those creatures can attempt a DC {dc} basic Fortitude save. A creature that fails this save falls unconscious, and a creature that succeeds is then temporarily immune to falling unconscious from Greater Constrict for 1 minute.")  # noqa: E501



def engulf(damage: SimpleDice, damage_type: str, *, dc: int, escape: int, rupture: int) -> Action:
    return offensive('Engulf', f"""The monster Strides up to double its Speed and can move through the spaces of any creatures in its path. Any creature of the monster's size or smaller whose space the monster moves through can attempt a DC {dc} Reflex save to avoid being engulfed. A creature unable to act automatically critically fails this save. If a creature succeeds at its save, it can choose to be either pushed aside (out of the monster's path) or pushed in front of the monster to the end of the monster's movement. The monster can attempt to Engulf the same creature only once in a single use of Engulf. The monster can contain as many creatures as can fit in its space.
    A creature that fails its save is pulled into the monster's body. It is grabbed, slowed 1, and has to hold its breath or start suffocating. The creature takes {damage} {damage_type} damage when first engulfed and at the end of each of its turns while it's engulfed. An engulfed creature can get free by Escaping against DC {escape}. An engulfed creature can attack the monster engulfing it, but only with unarmed attacks or with weapons of light Bulk or less. The engulfing creature is off-guard against the attack. If the monster takes piercing or slashing damage equaling or exceeding {rupture} from a single attack or spell, the engulfed creature cuts itself free. A creature that gets free by either method can immediately breathe and exits the engulfing monster's space.
    If the monster dies, all creatures it has engulfed are automatically released as the monster's form loses cohesion.""".replace('\n', '<br>'),   # noqa: E501
        cost=2)


def fast_healing(value: int) -> Action:
    return defensive('Fast Healing', f"The monster regains {value} Hit Points each round at the beginning of its turn.", cost=0)  # noqa: E501


def ferocity() -> Action:
    return defensive('Ferocity', "<b>Trigger</b> The monster is reduced to 0 HP; <b>Effect</b> The monster avoids being knocked out and remains at 1 HP, but its wounded value increases by 1. When it is wounded 3, it can no longer use this ability.", cost='reaction')  # noqa: E501


def frightful_presence(*, area: int, dc: int) -> Action:
    return defensive('Frightful Presence', f"""A creature that first enters a {area} foot radius must attempt a DC {dc} Will save. Regardless of the result of the saving throw, the creature is temporarily immune to this monster's Frightful Presence for 1 minute.
    <b>Critical Success</b> The creature is unaffected by the presence.
    <b>Success</b> The creature is frightened 1.
    <b>Failure</b> The creature is frightened 2.
    <b>Critical Failure</b> The creature is frightened 4.""".replace('\n', '<br>'),  # noqa: E501
    cost=0, traits=['aura', 'emotion', 'fear', 'mental'])


def grab(*, improved: bool = False) -> Action:
    desc = """<b>Requirements</b> The monster's last action was a successful Strike that lists Grab in its damage entry, or the monster has a creature grabbed or restrained; <b>Effect</b> If used after a Strike, the monster attempts to Grapple the creature using the body part it attacked with. This attempt neither applies nor counts toward the creature's multiple attack penalty.
        The monster can instead use Grab and choose one creature it's grabbing or restraining with an appendage that has Grab to automatically extend that condition to the end of the monster's next turn.""".replace('\n', '<br>')  # noqa: E501
    if not improved:
        return offensive('Grab', desc)
    else:
        return offensive('Improved Grab', f"{desc} A monster with Improved Grab still needs to spend an action to extend the duration for creatures it already has grabbed.", cost='free')  # noqa: E501


def knockdown(*, improved: bool = False) -> Action:
    return offensive('Improved Knockdown' if improved else 'Knockdown',
                     "<b>Requirements</b> The monster's last action was a successful Strike that lists Knockdown in its damage entry; <b>Effect</b> The monster attempts to Trip the creature. This attempt neither applies nor counts toward the monster's multiple attack penalty.",  # noqa: E501
                     cost = 'free' if improved else 1)


def light_blindness() -> Action:
    return defensive('Light Blindness', "When first exposed to bright light, the monster is blinded until the end of its next turn. After this exposure, light doesn't blind the monster again until after it spends 1 hour in darkness. However, as long as the monster is in an area of bright light, it's dazzled.", cost=0)  # noqa: E501


def pull() -> Action:
    return offensive('Pull', "<b>Requirements</b> The monster's last action was a success with a Strike that lists Pull in its damage entry; <b>Effect</b> The monster attempts to Reposition the creature, moving it closer to the monster. This attempt neither applies nor counts toward the monster's multiple attack penalty. If Pull lists a distance, change the distance the creature is pulled on a success to that distance.")  # noqa: E501


def push(*, improved: bool = False) -> Action:
    return offensive('Improved Push' if improved else 'Push',
                     "<b>Requirements</b> The monster's last action was a successful Strike that lists Push in its damage entry; <b>Effect</b> The monster attempts to Shove the creature. This attempt neither applies nor counts toward the monster's multiple attack penalty. If Push lists a distance, change the distance the creature is pushed on a success to that distance.",  # noqa: E501
                     cost = 'free' if improved else 1)


def reactive_strike() -> Action:
    return defensive(  # defensive, because it's a 'reaction' usually triggered off-turn
        'Reactive Strike',
        trigger="A creature within the monster's reach uses a manipulate action or a move action, makes a ranged attack, or leaves a square during a move action it's using.",  # noqa: E501
        desc="<div class=\"details\"><b>Effect</b> The monster attempts a melee Strike against the triggering creature. If the attack is a critical hit and the trigger was a manipulate action, the monster disrupts that action. This Strike doesn't count toward the monster's multiple attack penalty, and its multiple attack penalty doesn't apply to this Strike</div>",  # noqa: E501
        cost='reaction')


def rend() -> Action:
    return offensive('Rend', "A Rend entry lists a Strike the monster has; <b>Requirements</b> The monster hit the same enemy with two consecutive Strikes of the listed type in the same round; <b>Effect</b> The monster automatically deals that Strike's damage again to the enemy.")  # noqa: E501


def retributive_strike() -> Action:
    return defensive('Retributive Strike', "<b>Trigger</b> An enemy damages the monster's ally, and both are within 15 feet of the monster. <b>Effect</b> The ally gains resistance to all damage against the triggering damage equal to 2 + the monster's level. If the foe is within reach, the monster makes a melee Strike against it.", cost='reaction')  # noqa: E501


def shield_block() -> Action:
    return defensive('Shield Block', "<b>Trigger</b> The monster has its shield raised and takes damage from a physical attack; <b>Effect</b> The monster snaps its shield into place to deflect a blow. The shield prevents the monster from taking an amount of damage up to the shield's Hardness. The monster and the shield each take any remaining damage, possibly breaking or destroying the shield.", cost='reaction')  # noqa: E501


def sneak_attack(damage: SimpleDice) -> Action:
    return offensive('Sneak Attack', f"When the monster Strikes a creature that has the flat-footed condition with an agile or finesse melee weapon, an agile or finesse unarmed attack, or a ranged weapon attack, it also deals {damage} precision damage. For a ranged attack with a thrown weapon, that weapon must also be an agile or finesse weapon.", cost=0)  # noqa: E501


def stench(*, dc: int) -> Action:
    return defensive('Stench', f"A creature entering the aura or starting its turn in the area must succeed at a DC {dc} Fortitude save or become sickened 1 (plus slowed 1 as long as it's sickened on a critical failure). A creature that succeeds at its save or recovers from being sickened is temporarily immune to all stench auras for 1 minute.",  # noqa: E501
                     traits=['aura', 'olfactory'])


def swallow_whole(damage: SimpleDice, damage_type: str, *, size: str) -> Action:
    return offensive('Swallow Whole', f"""The monster attempts to swallow a {size} or smaller creature that it has grabbed or restrained in its jaws or mouth. If a swallowed creature is {size}, the monster can't use Swallow Whole again. If the creature is smaller than {size}, the monster can usually swallow more creatures; the GM determines the maximum. The monster attempts an Athletics check opposed by the target's Reflex DC. If it succeeds, it swallows the creature. The monster's mouth or jaws no longer clutch a creature it has swallowed, so the monster is free to use them to Strike or Grab once again. The monster can't attack creatures it has swallowed.<br>
    A swallowed creature is grabbed, is slowed 1, and has to hold its breath or start suffocating. The swallowed creature takes {damage} {damage_type} damage when first swallowed and at the end of each of its turns while it's swallowed. If the victim Escapes this ability's grabbed condition, it exits through the monster's mouth. This frees any other creature captured in the monster's mouth or jaws. A swallowed creature can attack the monster that has swallowed it, but only with unarmed attacks or with weapons of light Bulk or less. The swallowing creature is off-guard against the attack. If the monster takes piercing or slashing damage equaling or exceeding the listed Rupture value from a single attack or spell, the swallowed creature cuts itself free. A creature that gets free by either Escaping or cutting itself free can immediately breathe and exits the swallowing monster's space.<br>
    If the monster dies, a swallowed creature can be freed by creatures adjacent to the corpse if they spend a combined total of 3 actions cutting the monster open with a weapon or unarmed attack that deals piercing or slashing damage.""".replace('\n', '<br>'),  # noqa: E501
        traits=['attack'])


def swarm_mind() -> Action:
    return defensive('Swarm Mind', "This monster doesn't have a single mind (typically because it's a swarm of smaller creatures) and is immune to mental effects that target only a specific number of creatures. It is still subject to mental effects that affect all creatures in an area.", cost=0)  # noqa: E501


def telepathy(radius: int) -> Action:
    return interaction('Telepathy', f"The monster can communicate mentally with any creatures within {radius} feet, as long as they share a language. This doesn't give any special access to their thoughts and communicates no more information than normal speech would.",  # noqa: E501
                       cost=0, traits=['aura', 'magical', 'mental'])


def throw_rock() -> Action:
    return interaction('Throw Rock', "The monster interacts to pick up a rock within reach or retrieve a stowed rock and throws it, making a ranged Strike.")  # noqa: E501


def trample(*, dc: int) -> Action:
    return offensive('Trample', f"The monster Strides up to double its Speed and can move through the spaces of creatures of the listed size, Trampling each creature whose space it enters. The monster can attempt to Trample the same creature only once in a single use of Trample. The monster deals the damage of the listed Strike, but trampled creatures can attempt a DC {dc} basic Reflex save.", cost=3)  # noqa: E501


def void_healing() -> Action:
    return defensive('Void Healing', "The creature draws health from void energy rather than vitality energy. It is damaged by vitality damage and is not healed by healing vitality effects. It does not take void damage, and it is healed by void effects that heal undead.", cost=0)  # noqa: E501
