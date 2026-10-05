/* Data transparency notice (hosted editor only): shown until "Understood", which is remembered in
   localStorage under "md2pdf-notice". The items it names are listed on the site's data transparency page. */
(() => {
  const notice = document.getElementById('storage-notice');
  if (!notice || document.body.dataset.hosted !== 'true') return;
  const KEY = 'md2pdf-notice';
  let seen = false;
  try { seen = localStorage.getItem(KEY) === 'seen'; } catch (_) { /* Storage unavailable: show it every time. */ }
  if (seen) return;
  // The editor is also served under /es/ and /de/: send the reader to the page in that language.
  const route = location.pathname.split('/')[1];
  const link = document.getElementById('storage-notice-link');
  if (link && ['de', 'es'].includes(route)) link.href = link.href.replace('/data-transparency/', `/${route}/data-transparency/`);
  notice.hidden = false;
  document.getElementById('storage-notice-ok').addEventListener('click', () => {
    notice.hidden = true;
    try { localStorage.setItem(KEY, 'seen'); } catch (_) { /* Then it simply returns next time. */ }
  });
})();
