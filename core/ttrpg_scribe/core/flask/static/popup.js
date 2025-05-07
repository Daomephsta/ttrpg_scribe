// Opens <a>, <area>, or <form> links using the popup target as popups
onload = () => 
{
    for (const link of document.querySelectorAll(":is(a, area, form)[target=popup]"))
    {
        link.addEventListener('click', () => window.open(link.href,
            'popup', 'width=400,height=450'))
    }
}