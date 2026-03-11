from ttrpg_scribe.pf2e_compendium.actions import Action
from ttrpg_scribe.pf2e_compendium.creature import PF2Creature, Sense


def with_actions(*actions: Action) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions += actions
    return template


def without_actions(*action_names: str) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions = [a for a in creature.actions
                            if a.name not in action_names]
    return template


def replace_actions(actions: dict[str, Action]) -> PF2Creature.Template:
    def template(creature: PF2Creature):
        creature.actions = [actions.get(a.name, a) for a in creature.actions]
    return template


def darkvision(creature: PF2Creature):
    for i in range(len(creature.senses)):
        if creature.senses[i].name == 'low-light-vision':
            creature.senses[i] = Sense('darkvision')
            return
    creature.senses.append(Sense('darkvision'))
