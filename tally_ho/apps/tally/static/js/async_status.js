// Generic JSON-status poller. Polls `url` on an interval, invokes
// `onUpdate(data)` after each successful tick, and stops when the
// returned `status` field is in `terminalStatuses`.
//
// Usage:
//   pollStatus('/.../status/123/', (data) => {
//     document.getElementById('status').textContent = data.status;
//   });
//
// Options:
//   intervalMs       polling interval in ms (default 1000)
//   terminalStatuses array of status strings that end the loop
//                    (default ['COMPLETED', 'FAILED'])
//   onError          called with the fetch/parse error if a tick fails;
//                    the loop keeps going unless the callback returns
//                    false (default: console.error)
(function (global) {
  function pollStatus(url, onUpdate, options) {
    var opts = options || {};
    var intervalMs = opts.intervalMs || 1000;
    var terminal = opts.terminalStatuses || ['COMPLETED', 'FAILED'];
    var onError = opts.onError || function (err) { console.error(err); };

    function tick() {
      fetch(url, { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('status fetch failed: ' + r.status);
          return r.json();
        })
        .then(function (data) {
          onUpdate(data);
          if (terminal.indexOf(data.status) === -1) {
            setTimeout(tick, intervalMs);
          }
        })
        .catch(function (err) {
          if (onError(err) === false) return;
          setTimeout(tick, intervalMs);
        });
    }

    tick();
  }

  global.pollStatus = pollStatus;
})(window);
