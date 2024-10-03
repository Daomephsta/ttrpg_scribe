currentTurn = 0

function setCurrentTurn(turn)
{
    current = document.getElementById('current_turn')
    if (current)
        current.removeAttribute('id')
    currentTurn = turn % rows.length
    rows[currentTurn].id = 'current_turn'
}

function getRound()
{
    return Number(sessionStorage.getItem('current_round') || 1)
}

function setRound(round)
{
    sessionStorage.setItem('current_round', round)
    document.getElementById('current_round').textContent = `Round ${round}`
}

function getInitiative(row)
{
    return row.querySelector('.initiative').valueAsNumber
}

function sortInitiative()
{
    tbody = document.querySelector('#tracker tbody')
    rows = Array.from(tbody.querySelectorAll('tr'))
    rows.sort((a, b) => getInitiative(b) - getInitiative(a))
        .forEach(row => tbody.appendChild(row))
    setCurrentTurn(0)
}

function nextTurn()
{
    rows = document.querySelectorAll('#tracker tbody > tr')
    setCurrentTurn(currentTurn + 1)
    if (currentTurn == 0)
        setRound(getRound() + 1)
    // Skip dead creatures
    rows = document.querySelectorAll('#tracker tbody > tr')
    while(rows[currentTurn].classList.contains('dead'))
        nextTurn()
}

function updateDeadStatus(damageInput)
{
    let row = damageInput.closest('tr')
    if (damageInput.valueAsNumber >= damageInput.max)
        row.classList.add('dead')
    else
        row.classList.remove('dead')
}

function updateReinforcementControls()
{
    let quick = document.getElementById('reinforce_with_existing_controls')
    let creature = document.getElementById('reinforce_with_new_controls')
    if (document.getElementById('reinforce_with_existing').checked) {
        quick.classList.remove('collapsed')
        creature.classList.add('collapsed')
    }
    else if (document.getElementById('reinforce_with_new').checked) {
        creature.classList.remove('collapsed')
        quick.classList.add('collapsed')
    }
}

function saveRow(row)
{
    const type = row.className
    const name = row.querySelector('.name').textContent
    const json = {
        type: type,
        initiative: getInitiative(row),
        notes: row.querySelector('.notes').value,
    }
    console.log(json.name)
    if (type != 'player') {
        json.damage = row.querySelector('.damage').valueAsNumber
    }
    return [name, json]
}

function save()
{
    const json = {}
    for (const row of document.querySelectorAll('#tracker tbody tr'))
    {
        let [name, rowJson] = saveRow(row)
        json[name] = rowJson
    }
    const blob = new Blob([JSON.stringify(json)], {
        type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const downloadLink = document.createElement('a')
    downloadLink.href = url
    downloadLink.download = `encounter_${new Date().toISOString()}.json`

    document.body.appendChild(downloadLink)
    downloadLink.click()
    document.body.removeChild(downloadLink)
    URL.revokeObjectURL(url)
}

function loadRow(row, json)
{
    row.classList.add(json.type)
    row.querySelector('.initiative').value = json.initiative
    row.querySelector('.notes').value = json.notes
    if (json.type != 'player') {
        row.querySelector('.damage').value = json.damage
    }
}

function loadFrom(json) {
    for (const row of document.querySelectorAll('#tracker tbody tr'))
    {
        const name = row.querySelector('.name').textContent
        loadRow(row, json[name])
    }
    sortInitiative()
}

function load() {
    const loadDialog = document.getElementById('load_dialog')
    loadDialog.showModal()
    const form = document.getElementById('load_dialog_form')
    form.addEventListener('submit', (event) => {
        files = event.target.file_picker.files
        if (files.length > 0)
            files[0].text().then(contents => loadFrom(JSON.parse(contents)))
    },
    {
        once: true
    })
}

onload = (_) =>  {
    for (const input of document.getElementsByClassName('damage'))
    {
        updateDeadStatus(input)
        input.addEventListener('click', (event) =>
        {
            if (!event.shiftKey)
                return;
            const dialog = document.getElementById('health_dialog')
            dialog.returnValue = null
            const dialogValue = document.querySelector('#health_dialog .dialog_value')
            dialogValue.value = 0
            dialog.showModal()
            dialog.addEventListener('close', (_) =>
            {
                if (dialog.returnValue == 'damage_button')
                    input.value = input.valueAsNumber + dialogValue.valueAsNumber
                else if (dialog.returnValue == 'heal_button')
                    input.value = input.valueAsNumber - dialogValue.valueAsNumber
                updateDeadStatus(input)
            }, {once: true})
        })
    }
    updateReinforcementControls()
    setRound(getRound())
};

// Require confirmation when closing Initiative Tracker
window.addEventListener('beforeunload', (event) =>
{
    // except if all enemies are dead
    if (document.querySelectorAll('.enemy.dead').length < document.querySelectorAll('.enemy').length)
        event.preventDefault();
})