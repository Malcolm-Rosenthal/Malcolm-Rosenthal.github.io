/* The visitor's choice of style: fun or serious.

   Loaded in <head> without `defer`, on purpose: the attribute has to be on
   <html> before the page is drawn, or a visitor who chose serious sees the
   fun page flash first on every click.

   The choice is kept in the browser's own storage, so it follows the visitor
   from page to page. A browser that refuses storage (private windows do)
   just gets the default each time. */
(function () {
  var root = document.documentElement;
  var DEFAULTS = { style: 'fun', look: 'garden' };

  function read(key) {
    try { return localStorage.getItem('site-' + key); } catch (e) { return null; }
  }
  function write(key, value) {
    try { localStorage.setItem('site-' + key, value); } catch (e) { /* no storage: fine */ }
  }
  function apply(key, value) {
    root.dataset[key] = value;
    document.querySelectorAll('[data-set-' + key + ']').forEach(function (b) {
      var on = b.getAttribute('data-set-' + key) === value;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  Object.keys(DEFAULTS).forEach(function (key) {
    root.dataset[key] = read(key) || DEFAULTS[key];
  });

  document.addEventListener('DOMContentLoaded', function () {
    Object.keys(DEFAULTS).forEach(function (key) {
      apply(key, root.dataset[key]);
      document.querySelectorAll('[data-set-' + key + ']').forEach(function (b) {
        b.addEventListener('click', function () {
          var value = b.getAttribute('data-set-' + key);
          apply(key, value);
          write(key, value);
        });
      });
    });
  });
})();
