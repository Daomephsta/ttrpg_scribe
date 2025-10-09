export {}

function toTitleCase(str: string) {
    return str.replace(/(?:^|\s)\w/g, m => m.toUpperCase());
}

function rarityLetter(rarity: string) {
    return rarity == 'unique' ? 'Q' : rarity[0].toUpperCase()
}

interface SpecificationJson {
    quantity: number,
    'level-min': number,
    'level-max': number,
    rarity: Array<string>,
    size: Array<string>,
    traits: Array<string>
}

function updateSpecification($specification: JQuery) {
    const data: SpecificationJson = JSON.parse($specification.find('.data').val() as string)
    $specification.find('.quantity').text(data.quantity)
    $specification.find('.level').text(data['level-min'] == data['level-max']
        ? data['level-min']
        : `${data['level-min']} to ${data['level-max']}`
    )
    $specification.find('.rarity').empty()
        .attr('title', data.rarity.map(toTitleCase).join(', '))
        .text(data.rarity.map(rarityLetter).join(''))
    $specification.find('.size')
        .attr('title', data.size.map(toTitleCase).join(', '))
        .text(data.size.map(s => s[0].toUpperCase()).join(''))
    const traits = data.traits.map(toTitleCase).join(', ')
    $specification.find('.traits')
        .attr('title', traits)
        .text(traits)
    return $specification
}

function addSpecification($specification?: JQuery) {
    if ($specification == undefined) {
        $specification = $($('#specification-template').html())
    }
    $specification.find('.duplicate').on('click', event => duplicateSpecification($(event.target.closest('.specification') as HTMLElement)))
    $specification.find('.edit').on('click', event => editSpecification($(event.target.closest('.specification') as HTMLElement)))
    updateSpecification($specification)
    return $specification.appendTo($('#specifications tbody'))
}

function duplicateSpecification($specification: JQuery) {
    return addSpecification($specification.clone())
}

function editSpecification($specification: JQuery) {
    const $dialog = $<HTMLDialogElement>('#specification-dialog')
    const dialog = $dialog[0]
    const $data = $specification.find('.data');
    const data: SpecificationJson = JSON.parse($data.val() as string)

    function writeData<K extends keyof SpecificationJson>(name: K, getter: (inputElement: JQuery<HTMLInputElement>) => SpecificationJson[K]) {
        data[name] = getter($dialog.find<HTMLInputElement>(`[name="${name}"]`))
    }

    type DataKey<T> = {
        [K in keyof SpecificationJson]: SpecificationJson[K] extends T ? K : never
    }[keyof SpecificationJson]

    function writeNumericData(name: DataKey<number>) {
        writeData(name, f => Number(f.val()))
    }

    function writeBoolArrayData(name: DataKey<Array<any>>) {
        writeData(name, f => f.filter(':checked').toArray().map(e => e.value))
    }

    for (const key of Object.keys(data) as Array<keyof SpecificationJson>) {
        $dialog.find(`[name="${key}"]`).val(data[key])
    }
    dialog.querySelector('form')!.addEventListener('submit', (_) => {
        writeNumericData('quantity')
        writeNumericData('level-min')
        writeNumericData('level-max')
        writeBoolArrayData('rarity')
        writeBoolArrayData('size')
        writeData('traits', f => f.val()!.split(',').map(s => s.toLowerCase().trim()))
        $data.val(JSON.stringify(data))
        updateSpecification($specification)
    }, { once: true })
    dialog.showModal()
}

interface GenerateResult {
    _id: string,
    quantity: number,
    name: string,
    level: number,
    rarity: string
}

function generate(oracleEndpoint: string, compendiumContentEndpoint: string) {
    const specifications = $<HTMLTextAreaElement>('.specification .data').toArray()
        .map(data => JSON.parse(data.value))
    fetch(oracleEndpoint, {
        method: 'POST',
        body: JSON.stringify(specifications),
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(r => {
        if (r.ok) {
            return r.json() as Promise<Array<GenerateResult>>
        }
        throw new Error(`${oracleEndpoint} returned ${r.status} ${r.statusText}`)
    })
    .then(results => {
        $('#results tbody').empty().append(results.map(r => {
            const url = compendiumContentEndpoint.replace('ID', r._id)
            return $(`<tr></tr>`)
                .append($(`<td>`, { 'class': 'quantity' }).text(r.quantity))
                .append($(`<td>`, { 'class': 'name' })
                    .append($('<a>', { href: url, target: 'preview' }).text(r.name)))
                .append($(`<td>`, { 'class': 'level' }).text(r.level))
                .append($(`<td>`, { 'class': 'rarity' }).text(toTitleCase(r.rarity)))
            [0]
        }))
    })
}

$.ready.then(() => 
{
    addSpecification()
    $('#add').on('click', event => addSpecification())
    const oracleEndpoint = $('#oracle-endpoint').text().trim()
    const compendiumContentEndpoint = $('#compendium-content-endpoint').text().trim()
    $('#generate').on('click', _ => generate(oracleEndpoint, compendiumContentEndpoint))
})