export {}

function analyse(analyseEndpoint: string) {
    function idElementMap(className: string): {[id: string]: HTMLElement} {
        return Object.fromEntries($(`.${className}`).toArray().map(e => [e.id, e]))
    }

    function elementValueMap(elements: {[id: string]: HTMLElement}, valueFunction: (e: HTMLElement) => any) {
        return Object.fromEntries(Object.entries(elements).map(([id, e]) => [id, valueFunction(e)]))
    }

    function elementNumberMap(elements: {[id: string]: HTMLElement}) {
        return elementValueMap(elements, v => Number(v.textContent))
    }

    function elementDamageMap(elements: {[id: string]: HTMLElement}) {
        return elementValueMap(elements,
            v => Array.from(v.getElementsByClassName('statistic-damage-dice')).map(e => e.textContent))
    }

    interface Classification {
        name: string
        rank: number
        adjustment: number
        maximum?: number
        human: string
    }

    function applyClassification(element: HTMLElement, classification: Classification) {
        element.classList.add(`${classification.name.toLowerCase()}-statistic`)
        element.title = classification.human
    }

    function applyClassifications(elements: {[id: string]: HTMLElement}, classifications: {[id: string]: Classification}) {
        for (const [id, classification] of Object.entries(classifications)) {
            applyClassification(elements[id], classification)
        }
    }

    const level = document.getElementById('statistic-level')!
    const perception = document.getElementById('statistic-perception')!
    const skills = idElementMap('statistic-skill-mod')
    const attributes = idElementMap('statistic-attribute')
    const saves = idElementMap('statistic-save')
    const ac = document.getElementById('statistic-armour-class')!
    const hp = document.getElementById('statistic-hit-points')!
    const resistances = idElementMap('statistic-resistance')
    const weaknesses = idElementMap('statistic-weakness')
    const strikes = {
        bonuses: idElementMap('statistic-strike-bonus'),
        damage: idElementMap('statistic-strike-damage')
    }
    const dcs = idElementMap('statistic-dc')
    const spellAttackBonuses = idElementMap('statistic-spell-attack')
    const otherDamage = idElementMap('statistic-damage')

    window.fetch(analyseEndpoint, {
        method: 'POST',
        body: JSON.stringify({
            level: Number(level.textContent),
            perception: Number(perception.textContent),
            skills: elementNumberMap(skills),
            attributes: elementNumberMap(attributes),
            saves: elementNumberMap(saves),
            ac: Number(ac.textContent),
            hp: Number(hp.textContent),
            resistances: elementNumberMap(resistances),
            weaknesses: elementNumberMap(weaknesses),
            strikes: {
                bonuses: elementNumberMap(strikes.bonuses),
                damage: elementDamageMap(strikes.damage)
            },
            dcs: elementNumberMap(dcs),
            spell_attack_bonuses: elementNumberMap(spellAttackBonuses),
            damage: elementDamageMap(otherDamage)
        }),
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(r => {
        if (r.ok) {
            return r.json()
        }
        throw new Error(`${analyseEndpoint} returned ${r.status} ${r.statusText}`)
    })
    .then((json: {[k: string]: any}) => {
        applyClassification(perception, json['perception'])
        applyClassifications(skills, json['skills'])
        applyClassifications(attributes, json['attributes'])
        applyClassifications(saves, json['saves'])
        applyClassification(ac, json['ac'])
        applyClassification(hp, json['hp'])
        applyClassifications(resistances, json['resistances'])
        applyClassifications(weaknesses, json['weaknesses'])
        applyClassifications(strikes.bonuses, json['strikes']['bonuses'])
        applyClassifications(strikes.damage, json['strikes']['damage'])
        applyClassifications(dcs, json['dcs'])
        applyClassifications(spellAttackBonuses, json['spell_attack_bonuses'])
        applyClassifications(otherDamage, json['damage'])
    })
}

$.ready.then(() => 
{
    const analyseEndpoint = $('#analyse-endpoint').text().trim()
    $('#analyse').on('click', _ => analyse(analyseEndpoint))
})