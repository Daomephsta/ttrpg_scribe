function getInitiative(row)
{
    initiative_cell = row.querySelector('td:nth-child(2)')
    input = initiative_cell.querySelector('input')
    if (input)
        return Number(input.value)
    return Number(initiative_cell.textContent)
}

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

onload = (_) =>  {
    for (const input of document.getElementsByClassName('damage'))
    {
        updateDeadStatus(input)
        input.addEventListener('dblclick', (event) =>
        {
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

document.addEventListener('keyup', (event) =>
{
    if (event.key == 'n')
        nextTurn();
})