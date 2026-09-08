export {}

function addCharacter()
{
    const $addCharacterName = $('#add-character-name')
    $('.character').last()
        .after(
            $('<input>', {type: 'checkbox', name: $addCharacterName.val(), checked: true}),
            $('<span>', {'class': 'character'}).text($addCharacterName.val() as string)
        )
}

$.ready.then(() => 
{
    $('#add-character').on('click', addCharacter)
})