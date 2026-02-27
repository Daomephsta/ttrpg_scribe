import slug from 'slug'
import tocbot from 'tocbot'

slug.reset

function truncate(s: string, max_length: number): string
{
  if (s.length > max_length)
  {
    return s.substring(0, max_length - 3) + '...'
  }
  return s
}

document.addEventListener("DOMContentLoaded", () => {
  $('h1, h2, h3, h4, h5, h6').each((_, e) => {
      if (e.id == '')
        e.id = slug(e.textContent);
  });
  tocbot.init({
    tocSelector: '.toc',
    contentSelector: 'main',
    headingLabelCallback: text => text.toLowerCase(),
    includeTitleTags: true
  })
})
