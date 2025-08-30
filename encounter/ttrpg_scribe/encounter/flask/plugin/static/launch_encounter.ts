export {}

function launchEncounter(event: JQuery.ClickEvent) 
{
    // Send POST request to /encounter endpoint (see ttrpg_scribe.server)
    fetch('/encounter', {
        method: 'POST', 
        headers: {
            'Accept': 'text/html',
            'Content-Type': 'application/json'
        }, 
        body: event.target.dataset['encounter']
    })
    .then(r => {
        let initiative = window.open(r.url, '_blank')
        // Clear session storage for new encounter
        initiative.sessionStorage.clear()
    });
}

const DICE = /(?:(?<dice_count>\d+)d(?<dice_size>\d+) \+ )?(?<base>\d+)/
var randomInteger = (min, max) => Math.floor(min + Math.random() * (max - min))

function launchRandomEncounter(event: JQuery.ClickEvent) 
{
    // Parse data attributes
    const {groups: {dice_count_g, dice_size_g, base}} = DICE.exec(event.target.dataset.size)
    let encounter_size = Number(base)
    const dice_count = Number(dice_count_g || 0)
    const dice_size = Number(dice_size_g || 0)
    // Generate random encounter size
    for (let i = 0; i < dice_count; i++) 
        encounter_size += randomInteger(1, dice_size)
    let creatures = [[encounter_size, JSON.parse(event.target.dataset.creature)]]
    // Send POST request to /encounter endpoint (see ttrpg_scribe.server)
    fetch('/encounter', {
        method: 'POST', 
        headers: {
            'Accept': 'text/html',
            'Content-Type': 'application/json'
        }, 
        body: JSON.stringify({npcs: creatures, pcs: JSON.parse(event.target.dataset.party)})
    })
    .then(r => window.open(r.url, 'initiative'));
}

$.ready.then(() => {
    $('.launch-encounter').on('click', launchEncounter)
    $('.launch-random-encounter').on('click', launchRandomEncounter)
})