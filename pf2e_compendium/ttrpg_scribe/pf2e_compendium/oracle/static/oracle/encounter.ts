export {}

function toTitleCase(str) {
    return str.replace(/(?:^|\s)\w/g, m => m.toUpperCase());
}

function rarityLetter(rarity) {
    return rarity == 'unique' ? 'Q' : rarity[0].toUpperCase()
}

function updateSpecification($specification) {
    const data = JSON.parse($specification.find('.data').val())
    $specification.find('.quantity').text(data['quantity'])
    $specification.find('.level').text(data['level-min'] == data['level-max']
        ? data['level-min']
        : `${data['level-min']} to ${data['level-max']}`
    )
    $specification.find('.rarity').empty()
        .attr('title', data['rarity'].map(toTitleCase).join(', '))
        .text(data['rarity'].map(rarityLetter).join(''))
    $specification.find('.size')
        .attr('title', data['size'].map(toTitleCase).join(', '))
        .text(data['size'].map(s => s[0].toUpperCase()).join(''))
    const traits = data['traits'].map(toTitleCase).join(', ')
    $specification.find('.traits')
        .attr('title', traits)
        .text(traits)
    return $specification
}

function addSpecification() {
    const $specification = $($('#specification-template').html())
    updateSpecification($specification)
    return $specification.appendTo($('#specifications tbody'))
}

function duplicateSpecification($specification) {
    const $duplicate = updateSpecification($specification.clone())
    return $duplicate.appendTo($('#specifications tbody'))
}

function editSpecification($specification) {
    const $dialog = $<HTMLDialogElement>('#specification-dialog')
    const dialog = $dialog[0]
    const $data = $specification.find('.data');
    const data = JSON.parse($data.val())

    function writeData(name, getter) {
        data[name] = getter($dialog.find(`[name="${name}"]`))
    }

    function writeNumericData(name) {
        writeData(name, f => Number(f.val()))
    }

    function writeBoolArrayData(name) {
        writeData(name, f => f.filter(':checked').toArray().map(e => e.value))
    }

    for (const key in data) {
        $dialog.find(`[name="${key}"]`).val(data[key])
    }
    dialog.querySelector('form').addEventListener('submit', (_) => {
        writeNumericData('quantity')
        writeNumericData('level-min')
        writeNumericData('level-max')
        writeBoolArrayData('rarity')
        writeBoolArrayData('size')
        writeData('traits', f => f.val().split(',').map(s => s.toLowerCase().trim()))
        $data.val(JSON.stringify(data))
        updateSpecification($specification)
    }, { once: true })
    dialog.showModal()
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
    }).then(r => r.json()).then(results => {
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
    $('.duplicate').on('click', event => duplicateSpecification($(event.target.closest('.specification'))))
    $('.edit').on('click', event => editSpecification($(event.target.closest('.specification'))))
    $('.add').on('click', addSpecification)
    const oracleEndpoint = $('#oracle-endpoint').text().trim()
    const compendiumContentEndpoint = $('#compendium-content-endpoint').text().trim()
    $('.generate').on('click', _ => generate(oracleEndpoint, compendiumContentEndpoint))
})