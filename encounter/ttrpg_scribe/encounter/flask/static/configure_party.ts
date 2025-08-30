export {}

function addCharacter()
{
    const $addCharacterName = $('#add-character-name')
    $('<label>')
        .append($('<span>', {'className': 'character', 'textContent': $addCharacterName.val()}))
        .append($('<input>', {type: 'checkbox', name: $addCharacterName.val(), checked: true}))
        .insertBefore($addCharacterName)
}

$.ready.then(() => 
{
    $('#add-character').on('click', addCharacter)
})