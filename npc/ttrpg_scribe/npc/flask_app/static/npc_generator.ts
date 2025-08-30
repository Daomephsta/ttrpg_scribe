export {}

function readEmbeddedJson(id) {
    return JSON.parse(document.getElementById(id).innerText)
}

const REGIONS = readEmbeddedJson('regions')
const ALL_RACES = readEmbeddedJson('all_races')
const ALL_CULTURES = readEmbeddedJson('all_cultures')

function regionChanged() {
    const region_selector = document.getElementById('region') as HTMLSelectElement
    const culture_selector = document.getElementById('culture') as HTMLSelectElement
    const race_selector = document.getElementById('race') as HTMLSelectElement

    culture_selector.replaceChildren(new Option(''))
    race_selector.replaceChildren(new Option(''))

    const cultures = region_selector.value === ''
        ? Object.keys(ALL_CULTURES)
        : REGIONS[region_selector.value]['cultures']

    for (const culture of cultures)
        culture_selector.add(new Option(culture))
}

function cultureChanged() {
    const culture_selector = document.getElementById('culture') as HTMLInputElement
    const race_selector = document.getElementById('race') as HTMLSelectElement

    race_selector.replaceChildren(new Option(''))

    const races = culture_selector.value === ''
        ? ALL_RACES
        : ALL_CULTURES[culture_selector.value]['races']

    for (const [race, subraces] of races) {
        if (subraces.length > 0) {
            const group = document.createElement('optgroup')
            group.label = race
            group.appendChild(new Option(race))
            for (const [name, subname] of subraces) {
                const option = new Option(name, race)
                option.setAttribute('subrace', subname)
                group.appendChild(option)
            }
            race_selector.add(group)
        }
        else race_selector.add(new Option(race))
    }
}

function raceChanged() {
    const race_selector = document.getElementById('race') as HTMLSelectElement
    const subrace_selector = document.getElementById('subrace') as HTMLSelectElement
    if (race_selector.value === '')
        subrace_selector.value === ''
    else
        subrace_selector.value = race_selector.selectedOptions[0].getAttribute('subrace')
}

function setFeedback(text, duration) {
    const feedback = document.getElementById('feedback')
    feedback.textContent = text
    setTimeout(() => feedback.textContent = '', duration)
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