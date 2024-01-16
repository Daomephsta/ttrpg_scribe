// Opens <a> links using the popup target as popups
onload = () => 
{
    for (const link of document.querySelectorAll("a[target=popup]"))
    {
        link.addEventListener('click', () => window.open(link.href,
            'popup', 'width=400,height=450'))
    }
}