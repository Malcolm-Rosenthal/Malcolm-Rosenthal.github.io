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

/* {{age-hours}}: how old Mal is, in hours, to `data-figures` significant figures.
   The build writes in the value as of build day; this replaces it with the
   value as of now. `born` carries its own offset from UTC, so the answer is
   the same in every time zone; without one it would be read as local time. */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.age[data-born]').forEach(function (el) {
    var born = new Date(el.dataset.born.length === 10 ? el.dataset.born + 'T00:00' : el.dataset.born);
    var hours = (Date.now() - born.getTime()) / 3.6e6;
    if (!(hours > 0)) return;
    var parts = hours.toExponential((parseInt(el.dataset.figures, 10) || 4) - 1).split('e');
    el.innerHTML = parts[0] + ' &times; 10<sup>' + parseInt(parts[1], 10) + '</sup>';
  });
});

/* Animations play on their own, silently and on a loop, like the GIFs they
   were. A visitor who has asked their system for less motion gets them
   paused, with controls to play them if they want to. */
document.addEventListener('DOMContentLoaded', function () {
  if (!window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('video[autoplay]').forEach(function (v) {
    v.removeAttribute('autoplay'); v.pause(); v.controls = true;
  });
});
