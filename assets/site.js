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

/* The trail: the way this visitor came, not the way the site is filed.

   Each page is built with its own fixed trail (Home > Research > ...), which is
   what a visitor sees with scripts off, or when they land on a page straight
   from a bookmark or another site. Otherwise the trail follows the route they
   took: arrive at a page through a door and it goes on the end; click a crumb,
   or press Back to a page already on the trail, and everything after it drops
   off; Home starts it afresh. The route lives in the tab's own session storage,
   so it is gone when the tab is closed, and nothing about it leaves the browser.

   Called by a one-line script right after the trail in the page, so the trail
   is settled before the page is first drawn. */
window.siteTrail = function () {
  var nav = document.querySelector('nav.trail');
  if (!nav) return;
  var KEY = 'site-trail';

  function key(url) {                       // a page's identity: no #heading, no index.html
    var a = new URL(url, location.href);
    return a.origin + a.pathname.replace(/index\.html$/, '');
  }
  function find(list, k) {
    for (var i = 0; i < list.length; i++) if (list[i].key === k) return i;
    return -1;
  }

  var section = (document.body.className.match(/mc-\w+/) || [''])[0];
  var fixed = [].map.call(nav.querySelectorAll('.crumb'), function (c, i) {
    var here = c.tagName !== 'A';
    return { key: key(here ? location.href : c.href), href: here ? location.href : c.href,
             html: c.innerHTML, home: i === 0, mc: i === 0 ? '' : section };
  });
  if (!fixed.length) return;
  var cur = fixed[fixed.length - 1];

  var stack = [];
  try { stack = JSON.parse(sessionStorage.getItem(KEY) || '[]'); } catch (e) { stack = []; }
  if (!Array.isArray(stack)) stack = [];

  var at = find(stack, cur.key);
  var from = document.referrer ? find(stack, key(document.referrer)) : -1;
  if (fixed.length === 1) stack = [cur];                          // the home page: start afresh
  else if (at > 0) { stack = stack.slice(0, at); stack.push(cur); }  // back to somewhere already on the trail
  else if (from >= 0) stack = stack.slice(0, from + 1).concat([cur]);  // on through a door
  else stack = fixed;                                             // a bookmark, another site: the filed trail
  try { sessionStorage.setItem(KEY, JSON.stringify(stack)); } catch (e) { /* no storage: fine */ }

  var same = stack.length === fixed.length && stack.every(function (e, i) { return e.key === fixed[i].key; });
  if (same) return;                                               // already drawn

  nav.textContent = '';
  stack.forEach(function (e, i) {
    var last = i === stack.length - 1;
    if (i) { var sep = document.createElement('span'); sep.className = 'sep'; nav.appendChild(sep); }
    var el = document.createElement(last ? 'span' : 'a');
    el.className = 'crumb' + (e.home ? ' home' : '') + (e.mc ? ' ' + e.mc : '');
    if (!last) el.href = e.href;
    el.innerHTML = e.html;
    nav.appendChild(el);
  });
};
