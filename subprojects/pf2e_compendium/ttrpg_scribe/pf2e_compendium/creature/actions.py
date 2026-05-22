from ttrpg_scribe.pf2e_compendium.actions import SimpleAction


def reactive_strike(name: str = 'monster'):
    return SimpleAction(
        'Reactive Strike',
        trigger=f"A creature within the {name}'s reach uses a manipulate action or a move action, makes a ranged attack, or leaves a square during a move action it's using.",  # noqa: E501
        desc=f"<div class=\"details\"><b>Effect</b> The {name} attempts a melee Strike against the triggering creature. If the attack is a critical hit and the trigger was a manipulate action, the {name} disrupts that action. This Strike doesn't count toward the {name}'s multiple attack penalty, and its multiple attack penalty doesn't apply to this Strike</div>",  # noqa: E501
        cost='reaction')
