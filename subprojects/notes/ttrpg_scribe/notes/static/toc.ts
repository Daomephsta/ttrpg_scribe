import slug from 'slug'
import tocbot from 'tocbot'

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
