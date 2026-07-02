// Wires up the live-polling DOM updates on the PVP import result page.
// Reads the status URL + target element ids from `data-*` attributes on
// the root container so the template stays free of JS literals.
(function () {
  var root = document.getElementById('pvp-result-root');
  if (!root) return;
  var url = root.getAttribute('data-status-url');
  var statusEl = document.getElementById('pvp-status');
  var countEl = document.getElementById('pvp-count');
  var importedAtEl = document.getElementById('pvp-imported-at');

  pollStatus(url, function (data) {
    statusEl.textContent = data.status;
    countEl.textContent = data.number_of_submissions;
    importedAtEl.textContent = data.imported_at || '—';
  });
})();
