for (let button of document.getElementsByClassName('launch_encounter'))
{
    button.addEventListener('click', event => 
    {
        // Send POST request to /encounter endpoint (see dnd_scribe.server)
        fetch('/encounter', {
            method: 'POST', 
            headers: {
                'Accept': 'text/html',
                'Content-Type': 'application/json'
            }, 
            body: event.target.dataset['encounter']
        })
        .then(r => {
            let initiative = window.open(r.url, 'initiative')
            // Clear session storage for new encounter
            initiative.sessionStorage.clear()
        });
    });
}

const DICE = /(?:(?<dice_count>\d+)d(?<dice_size>\d+) \+ )?(?<base>\d+)/
var randomInteger = (min, max) => Math.floor(min + Math.random() * (max - min))

function launchRandomEncounter(event) 
{
    // Parse data attributes
    let {groups: {dice_count, dice_size, base}} = DICE.exec(event.target.dataset.size)
    let encounter_size = Number(base)
    dice_count = Number(dice_count | 0)
    dice_size = Number(dice_size | 0)
    // Generate random encounter size
    for (let i = 0; i < dice_count; i++) 
        encounter_size += randomInteger(1, dice_size)
    let creatures = [[encounter_size, JSON.parse(event.target.dataset.creature)]]
    // Send POST request to /encounter endpoint (see dnd_scribe.server)
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