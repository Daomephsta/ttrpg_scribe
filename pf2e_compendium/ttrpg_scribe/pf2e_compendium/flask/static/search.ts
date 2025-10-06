export {}

const endpoints = JSON.parse($('#search-js-endpoints').text())

function updateQueryType() {
    const queryType = $('input[name="query_type"]:checked').val()
    $(`.search-query`).prop('hidden', true).prop('disabled', true)
    $(`#${queryType}_query`)
        .prop('hidden', false).prop('disabled', false)
        .trigger('focus')
}

interface SearchResult {
    _id: string
    doc_type: string
    name: string
    level?: number
    rarity?: string
}

function search() {
    function doSearch(endpoint: string, searchParams: {[key: string]: string}, init: RequestInit): Promise<void> {
        const url = new URL(endpoint, document.baseURI)
        for (const [k, v] of Object.entries(searchParams)) {
            url.searchParams.set(k, v)
        }
        const resultsJson: Promise<Array<SearchResult>> = fetch(url, init).then(r => {
            if (r.ok) {
                return r.json()
            }
            throw new Error(`${endpoint} returned ${r.status} ${r.statusText}`)
        })
        return resultsJson.then(results => {
            $('#results legend').text(`Results (${results.length})`)
            $('#results tbody').empty().append(results.map(r => {
                const url = endpoints.compendiumContent.replace('DOC_TYPE', r.doc_type).replace('ID', r._id)
                return $(`<tr></tr>`)
                    .append($(`<td>`, { 'class': 'name' })
                        .append($('<a>', { href: url, target: 'preview' }).text(r.name)))
                    .append($(`<td>`, { 'class': 'level' }).text(r.level != undefined ? r.level : ''))
                    .append($(`<td>`, { 'class': 'rarity' }).text(r.rarity || ''))[0]
            }))
        })
    }

    const queryType = $('input[name="query_type"]:checked').val()
    const $docType = $<HTMLInputElement>('input[name="doc_type"]')
    const docTypeParam: {doc_type?: string} = $docType.length > 0 ? {doc_type: $docType.val()} : {}
    let request: Promise<SearchResult[]> = Promise.all([])
    switch (queryType) {
        case 'simple':
        {
            const query = $<HTMLInputElement>('#simple_query').val()!
            doSearch(endpoints.search, {query, ...docTypeParam}, {method: 'POST'})
            break
        }
        case 'complex':
        {
            try {
            const query = JSON.parse($<HTMLTextAreaElement>('#complex_query').val()!)
            doSearch(endpoints.search, {query_type: 'complex', ...docTypeParam}, {
                method: 'POST',
                body: JSON.stringify(query),
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            } 
            catch (error) {
                if (error instanceof SyntaxError) {
                    alert(error.message)
                }
            }
            break
        }
        
    }
}

$.ready.then(() => 
{
    updateQueryType()
    $('input[name="query_type"]').on('input', updateQueryType)
    $('.search-button').on('click', search)
})