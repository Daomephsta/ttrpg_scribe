export {}

function addCharacter()
{
    const $addCharacterName = $('#add-character-name')
    $('<label>')
        .append($('<span>', {'class': 'character'}).text($addCharacterName.val() as string))
        .append($('<input>', {type: 'checkbox', name: $addCharacterName.val(), checked: true}))
        .insertBefore($addCharacterName.parent())
}

$.ready.then(() => 
{
    $('#add-character').on('click', addCharacter)
})