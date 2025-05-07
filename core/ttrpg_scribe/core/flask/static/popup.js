// Opens <a>, <area>, or <form> links using the popup target as popups
onload = () => 
{
    for (const link of document.querySelectorAll(":is(a, area, form)[target=popup]"))
    {
        const width = link.dataset.popupWidth || 400, 
              height = link.dataset.popupHeight || 450
        link.addEventListener('click', () => window.open(link.href,
            'popup', `width=${width},height=${height}`))
    }
}