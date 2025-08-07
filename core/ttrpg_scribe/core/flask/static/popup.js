// Opens <a>, <area>, or <form> links using the popup target as popups
$.ready(() => 
    $(':is(a, area, form)[target=popup]').on('click', event => {
        const width = event.target.dataset.popupWidth || 400
        const height = event.target.popupHeight || 450
        window.open(link.href, 'popup', `width=${width},height=${height}`)
    })
)