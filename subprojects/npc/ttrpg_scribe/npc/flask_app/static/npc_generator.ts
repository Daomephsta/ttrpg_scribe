export {}

const REGIONS = JSON.parse($('#regions').text())
const ALL_RACES = JSON.parse($('#all_races').text())
const ALL_CULTURES = JSON.parse($('#all_cultures').text())

function regionChanged() {
    const regionInput = document.getElementById('region') as HTMLSelectElement
    const cultureInput = document.getElementById('culture') as HTMLSelectElement
    const raceInput = document.getElementById('race') as HTMLSelectElement

    cultureInput.replaceChildren(new Option(''))
    raceInput.replaceChildren(new Option(''))

    const cultures = regionInput.value === ''
        ? Object.keys(ALL_CULTURES)
        : REGIONS[regionInput.value]['cultures']

    for (const culture of cultures)
        cultureInput.add(new Option(culture))
}

function cultureChanged() {
    const cultureInput = document.getElementById('culture') as HTMLInputElement
    const raceInput = document.getElementById('race') as HTMLSelectElement

    raceInput.replaceChildren(new Option(''))

    const races = cultureInput.value === ''
        ? ALL_RACES
        : ALL_CULTURES[cultureInput.value]['races']

    for (const [race, subraces] of races) {
        if (subraces.length > 0) {
            const $group = $('<optgroup>', {label: race})
                .append(new Option(race))

            const group = document.createElement('optgroup')
            group.label = race
            group.appendChild(new Option(race))
            for (const [name, subname] of subraces) {
                const option = new Option(name, race)
                option.setAttribute('subrace', subname)
                group.appendChild(option)
            }
            raceInput.add(group)
        }
        else raceInput.add(new Option(race))
    }
}

function raceChanged() {
    const raceInput = document.getElementById('race') as HTMLSelectElement
    const subraceInput = document.getElementById('subrace') as HTMLSelectElement
    if (raceInput.value === '')
        subraceInput.value === ''
    else
        subraceInput.value = raceInput.selectedOptions[0].getAttribute('subrace')
}

function setFeedback(text, duration) {
    const $feedback = $('#feedback').text(text)
    setTimeout(() => $feedback.text(''), duration)
}

function reset() {
    for (const element of document.querySelector('form').elements) {
        if (element instanceof HTMLInputElement && element.type == 'text')
            element.value = ''
        else if (element instanceof HTMLSelectElement)
            element.selectedIndex = 0
    }
}

function generate(generateNpcEndpoint: string) {
    fetch(generateNpcEndpoint,
        {
            method: 'POST',
            body: new FormData(document.getElementById('features') as HTMLFormElement)
        })
        .then(response => response.json())
        .then(json => {
            const resultDocument = (document.getElementById('result-frame') as HTMLIFrameElement).contentDocument
            resultDocument.body.replaceChildren() // Clear body
            const table = resultDocument.body.appendChild(resultDocument.createElement('table'))
            for (const [feature, value] of json) {
                const row = table.appendChild(document.createElement('tr'))
                row.appendChild(document.createElement('th')).textContent = feature
                row.appendChild(document.createElement('td')).textContent = value
            }
            (document.getElementById('save') as HTMLButtonElement).disabled = false
        })
}

function save(saveNpcEndpoint: string) {
    fetch(saveNpcEndpoint,
        {
            method: 'POST'
        })
        .then(response => response.text())
        .then(text => {
            setFeedback(text, 1000);
            (document.getElementById('save') as HTMLButtonElement).disabled = true
        })
}

window.addEventListener('load', event => {
    regionChanged()
    cultureChanged()
})

$.ready.then(() => 
{
    $('#region').on('change', regionChanged)
    $('#culture').on('change', cultureChanged)
    $('#race').on('change', raceChanged)
    const generateNpcEndpoint = $('#generate-npc-endpoint').text().trim()
    $('#generate').on('click', _ => generate(generateNpcEndpoint))
    const saveNpcEndpoint = $('#save-npc-endpoint').text().trim()
    $('#save').on('click', _ => save(saveNpcEndpoint))
    $('#reset').on('click', reset)
})