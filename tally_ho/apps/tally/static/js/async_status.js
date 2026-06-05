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
//   maxStallTicks    stop after this many consecutive ticks where the
//                    response is byte-identical to the previous tick
//                    (default 100). Any change resets the counter.
//                    Set to 0 to disable stall detection.
//   onStall          called with the last data payload when the stall
//                    cap is hit (default: console.warn)
//   onError          called with the fetch/parse error if a tick fails;
//                    the loop keeps going unless the callback returns
//                    false (default: console.error)
(function (global) {
  function pollStatus(url, onUpdate, options) {
    var opts = options || {};
    var intervalMs = opts.intervalMs || 1000;
    var terminal = opts.terminalStatuses || ['COMPLETED', 'FAILED'];
    var maxStallTicks = opts.maxStallTicks == null ? 100 : opts.maxStallTicks;
    var onStall = opts.onStall || function (data) {
      console.warn('pollStatus: stopped after stall', data);
    };
    var onError = opts.onError || function (err) { console.error(err); };

    var lastSnapshot = null;
    var stallCount = 0;

    function tick() {
      fetch(url, { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('status fetch failed: ' + r.status);
          return r.json();
        })
        .then(function (data) {
          onUpdate(data);
          if (terminal.indexOf(data.status) !== -1) return;
          if (maxStallTicks > 0) {
            var snapshot = JSON.stringify(data);
            if (snapshot === lastSnapshot) {
              stallCount += 1;
              if (stallCount >= maxStallTicks) {
                onStall(data);
                return;
              }
            } else {
              lastSnapshot = snapshot;
              stallCount = 0;
            }
          }
          setTimeout(tick, intervalMs);
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
