function getRound(): number
{
    return Number(sessionStorage.getItem('current_round') || 1)
}

function setRound(round: number)
{
    sessionStorage.setItem('current_round', round.toString(10))
    $('#current-round').text(`Round ${round}`)
}

function getInitiative(row: Element): number
{
    return (row.querySelector('.initiative') as HTMLInputElement)!.valueAsNumber
}

function sortInitiative()
{
    const $trackerBody = $('#tracker tbody')
    const rows = $trackerBody.find('tr').detach()
        .toArray().sort((a, b) => getInitiative(b) - getInitiative(a))
    $trackerBody.append(rows)
}

function nextTurn()
{
    const $current = $('.current-turn').removeClass('current-turn')
    
    const $prev: JQuery<HTMLElement> = $current.prevAll(':not(.dead)')
        // @ts-ignore
        .uniqueSort() 
    const $next = $current.nextAll(':not(.dead)')
    $([...$next, ...$prev]).first().addClass('current-turn')
}

function updateDeadStatus(damageInput: HTMLInputElement)
{
    let $row = $(damageInput).closest('tr')
    const max = Number(damageInput.max)
    $row.toggleClass('dead', max > 0 && damageInput.valueAsNumber >= max)
}

function updateReinforcementControls()
{
    for (const input of $('#reinforcements input[type="radio"][name="reinforcement_type"]') as JQuery<HTMLInputElement>)
    {
        $(`${input.id}_controls`).toggleClass('collapsed', !input.checked)
    }
}


interface RowData 
{
    type: string,
    initiative: number,
    damage?: number,
    notes: string
}


function saveRow(row: HTMLElement): [string, RowData]
{
    const type: string = row.className
    const name: string = $('.name', row).text()
    const json: RowData = {
        type: type,
        initiative: getInitiative(row),
        notes: $('.notes', row).val() as string,
    }
    if (type != 'player') {
        json.damage = Number($('.damage', row).val())
    }
    return [name, json]
}

function save()
{
    const json = Object.fromEntries($('#tracker tbody tr').map((i, e) => [saveRow(e)]).get())
    const blob = new Blob([JSON.stringify(json)], {
        type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    $('a', {href: url, download: `encounter_${new Date().toISOString()}.json`})
        .appendTo(document.body)
        .each((i, e) => e.click())
        .remove()
    URL.revokeObjectURL(url)
}

function loadRow(row: HTMLElement, json: RowData)
{
    row.classList.add(json.type)
    row!.querySelector<HTMLInputElement>('.initiative')!.valueAsNumber = json.initiative
    row!.querySelector<HTMLInputElement>('.notes')!.value = json.notes
    if (json.damage != undefined) {
        row!.querySelector<HTMLInputElement>('.damage')!.valueAsNumber = json.damage
    }
}

function loadFrom(json: {[name: string]: RowData}) {
    for (const row of $('#tracker tbody tr'))
    {
        const $name = $('.name', row).text()
        loadRow(row, json[$name])
    }
    sortInitiative()
}

function load() {
    const loadDialog = document.getElementById('load_dialog') as HTMLDialogElement
    loadDialog.showModal()
    const form = document.getElementById('load_dialog_form') as HTMLFormElement
    form.addEventListener('submit', (event: SubmitEvent) => {
        const files = (event.target as HTMLFormElement).file_picker.files
        if (files.length > 0)
            files[0].text().then(contents => loadFrom(JSON.parse(contents)))
    },
    {
        once: true
    })
}

onload = (_) =>  {
    for (const input of document.getElementsByClassName('damage') as HTMLCollectionOf<HTMLInputElement>)
    {
        updateDeadStatus(input)
        input.addEventListener('click', (event: MouseEvent) =>
        {
            if (!event.shiftKey)
                return;
            const dialog = document.getElementById('health_dialog') as HTMLDialogElement
            dialog.returnValue = ''
            const dialogValue = document.querySelector('#health_dialog .dialog_value') as HTMLInputElement
            dialogValue.value = '0'
            dialog.showModal()
            dialog.addEventListener('close', (_) =>
            {
                if (dialog.returnValue == 'damage_button')
                    input.value = `${input.valueAsNumber + dialogValue.valueAsNumber}`
                else if (dialog.returnValue == 'heal_button')
                    input.value = `${input.valueAsNumber - dialogValue.valueAsNumber}`
                updateDeadStatus(input)
            }, {once: true})
        })
    }
    updateReinforcementControls()
    $('#tracker tbody tr').first().addClass('current-turn')
    setRound(getRound())
};

// Require confirmation when closing Initiative Tracker
window.addEventListener('beforeunload', (event) =>
{
    // except if all enemies are dead
    if ($('.enemy.dead').length < $('.enemy').length)
        event.preventDefault();
})