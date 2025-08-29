// Opens <a>, <area>, or <form> links using the popup target as popups
$.ready.then(() => 
    $(':is(a, area, form)[target=popup]').on('click', event => {
        const target = event.target as HTMLAnchorElement | HTMLAreaElement | HTMLFormElement
        const width = event.target.dataset.popupWidth || 400
        const height = event.target.dataset.popupHeight || 450
        window.open(target.href, 'popup', `width=${width},height=${height}`)
    })
)