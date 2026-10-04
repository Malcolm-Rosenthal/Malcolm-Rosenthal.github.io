/* The visitor's choice of style: fun (the default) or serious.

   Loaded in <head> without `defer`, on purpose: the attribute has to be on
   <html> before the page is drawn, or a visitor who chose serious sees the
   fun page flash first on every click.

   The choice is kept in the browser's own storage, so it follows the visitor
   from page to page. A browser that refuses storage (private windows do)
   just gets fun each time.

   The button's two labels are both in the page; the stylesheet shows the one
   that fits (`.when-fun`, `.when-serious`), so there is nothing to rewrite
   here and no flash of the wrong word. */
(function () {
  var root = document.documentElement;
  var KEY = 'site-style';

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* no storage: fine */ }
  root.dataset.style = saved === 'serious' ? 'serious' : 'fun';

  document.addEventListener('click', function (ev) {
    if (!ev.target.closest('[data-toggle-style]')) return;
    var next = root.dataset.style === 'serious' ? 'fun' : 'serious';
    root.dataset.style = next;
    try { localStorage.setItem(KEY, next); } catch (e) { /* no storage: fine */ }
  });
})();
