export {}

function analyse(analyseEndpoint: string) {
    interface Classification {
        id: string
        bracket: string
        full: string
    }

    function findTable(element: HTMLElement) {
        let table = element.dataset.table!
        if (table == 'dc') {
            const dc_table = element.closest<HTMLElement>('[data-dc-table]')?.dataset.dcTable
            if (dc_table)
                return dc_table
        }
        if (table == 'damage') {
            const damage_table = element.closest<HTMLElement>('[data-damage-table]')?.dataset.damageTable
            if (damage_table)
                return damage_table
        }
        return table
    }

    function parseValue(element: HTMLElement, table: string) {
        if (table === 'damage' || table.endsWith('-damage'))
            return Array.from(element.getElementsByClassName('damage-dice')).map(e => e.textContent)
        else
            return Number(element.textContent)
    }

    window.fetch(analyseEndpoint, {
        method: 'POST',
        body: JSON.stringify({
            level: Number(document.getElementById('statistic-level')!.textContent),
            values: Array.from((document.getElementsByClassName('statistic')) as HTMLCollectionOf<HTMLElement>).map(e => {
                const table = findTable(e)
                return {id: e.id, value: parseValue(e, table), table}
            })
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
    .then((classifications: Classification[]) => {
        for (const classification of classifications) {
            const element = document.getElementById(classification.id)!
            element.classList.add(`${classification.bracket.toLowerCase()}-statistic`)
            element.title = classification.full
        }
    })
}

$.ready.then(() => 
{
    const analyseEndpoint = document.getElementById('analyse-endpoint')!.textContent.trim()
    document.getElementById('analyse')!.addEventListener('click', _ => analyse(analyseEndpoint))
})