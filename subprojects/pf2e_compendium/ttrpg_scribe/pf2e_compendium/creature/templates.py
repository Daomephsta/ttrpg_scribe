from ttrpg_scribe.pf2e_compendium.actions import Action
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature, Sense


def with_actions(*actions: Action) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        for action in actions:
            creature.actions.add(action)
    return template


def without_actions(*action_names: str) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        for name in action_names:
            creature.actions.remove(name)
    return template


def replace_actions(*actions: Action) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        for action in actions:
            creature.actions.replace(action)
    return template


def darkvision(creature: PF2Creature):
    for i in range(len(creature.senses)):
        if creature.senses[i].name == 'low-light-vision':
            creature.senses[i] = Sense('darkvision')
            return
    creature.senses.append(Sense('darkvision'))
