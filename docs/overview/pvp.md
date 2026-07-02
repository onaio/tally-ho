# Preliminary Vote Protocol (PVP)

PVP is HNEC's pre-tally device workflow: at the polling station, a clerk
keys in candidate results twice (round 1 and round 2) on a tablet running
an ODK form. If the two rounds match, the device captures a signed copy
that can be ingested by tally-ho — skipping the manual Data Entry 1 pass
that would otherwise be done from paper.

## How a result gets into tally-ho

The diagram below shows the upload pipeline. The final per-row write
and the post-import path differ by `Tally.pvp_mode` — see *What the
operator sees* below for the per-mode specifics.

```text
ODK Central                  network host                     tally-ho host
    │                              │                                │
    │  pyODK pull                  │                                │
    ├──► odk-central-sync ────► .zip bundle                         │
    │     (centers + media)       │  (carry on USB)                 │
    │                              ├──► PVP upload screen ──────────┤
    │                              │                                ├─ Parse
    │                              │                                ├─ Validate
    │                              │                                ├─ Confirmation screen
    │                              │                                │   (will-import / will-skip / missing-images)
    │                              │                                ▼  user confirms
    │                              │                         Celery import task
    │                              │                                │
    │                              │                                ├─ For each row, write per-mode:
    │                              │                                │
    │                              │                                │   DE1_ONLY:
    │                              │                                │   • DE1 Result rows (votes = round 2)
    │                              │                                │   • DE1 ReconciliationForm
    │                              │                                │   • Form state UNSUBMITTED → DATA_ENTRY_2
    │                              │                                │     (human DE2 clerk; mismatch → corrections)
    │                              │                                │
    │                              │                                │   DE1_AND_DE2:
    │                              │                                │   • DE1 Result + recon (round 1)
    │                              │                                │   • DE2 Result + recon (round 2)
    │                              │                                │   • FINAL Result + recon (round 1 == round 2)
    │                              │                                │   • Form state UNSUBMITTED → QUALITY_CONTROL
    │                              │                                │     (no manual DE2, no corrections)
    │                              │                                │
    │                              │                                └─ Link ResultForm.pvp_submission
```

## What the operator sees

1. **Configure the tally** — Tally-manager edits the tally and picks a
   *PVP Mode*:
   - `DE1_ONLY`: round 2 is written as `DATA_ENTRY_1`; a human DE2 clerk
     still enters round 2 from paper independently. Corrections catches
     any mismatch.
   - `DE1_AND_DE2`: round 1 → `DATA_ENTRY_1`, round 2 → `DATA_ENTRY_2`.
     The device already guarantees round 1 == round 2, so the form
     skips corrections and goes straight to `QUALITY_CONTROL`.
2. **Upload a bundle** — Super-admin opens the PVP upload screen,
   selects the `.zip` produced by `odk-central-sync`. Tally-ho sanity-
   parses the zip and redirects to the confirmation screen. Uploads
   against a tally whose `pvp_mode` is `DISABLED` are rejected up
   front — the operator sees a form error rather than a confirmation
   screen full of `pvp_disabled` skip reasons.
3. **Confirm** — The confirmation screen shows three lists:
   - **Will import** — submissions that pass parse-time validation
   - **Will skip** — rows that fail validation, with a reason code
   - **Missing images** — image filenames referenced by the CSV but
     not present in the zip (these submissions still import, just
     with empty image fields)
4. **Result** — After confirming, a Celery task does the import. The
   result page shows the bundle status (`PENDING`, `IMPORTING`,
   `COMPLETED`, `FAILED`) and the count of submissions imported, and
   refreshes itself in place until the bundle reaches a terminal
   status (no page reload needed). If the import ends in `FAILED`, the
   exception message that aborted it is captured on the bundle and
   surfaced on the result page so the operator sees the cause without
   having to check task logs.

## Validation rules (parse-time)

A row is **skipped** (never persisted) if any of these is true:

| Reason | Meaning |
|---|---|
| `pvp_disabled` | Tally's `pvp_mode` was flipped to `DISABLED` between upload and confirm (uploads to an already-`DISABLED` tally are rejected earlier — see step 2) |
| `required_fields` | Missing barcode, ballot_number, instance ID, or all rounds-2 votes |
| `barcode_not_found` | Barcode does not match any ResultForm in this tally |
| `form_not_unsubmitted` | The matched form's state is not `UNSUBMITTED` |
| `already_imported` | The matched form already has a linked PvpSubmission |

Bundle-level rejections (whole bundle fails fast):

- Zip can't be opened or `candidate_results.csv` is missing
- Required CSV columns are missing
- More than one row references the same barcode
- Any candidate row has a missing round, or round 1 ≠ round 2
  (the device guarantees both, so any departure signals upstream
  data corruption — surfaces as `RoundIntegrityError`)

## What the "PVP" badge means

When you see a small `PVP` badge next to a result form's barcode (on the
print cover or detail page), it means the form's DATA_ENTRY_1 results
were populated by a PVP upload rather than by a manual clerk. A caption
shows the date the bundle was imported.

## Provenance after a reset

Resetting a PVP-imported form to `UNSUBMITTED` (via *Admin Operations →
Reset Form*) clears `ResultForm.pvp_submission` and deactivates the
PVP-written results. The form becomes eligible for re-upload via PVP
(or normal manual entry through INTAKE → DE1 → DE2), and the badge
disappears because it's no longer "currently sourced from PVP."

The original `PvpSubmission` row itself stays in the database as a
historical record — `ResultForm.pvp_submissions_history` returns every
PVP submission ever applied to a given form via a `(tally, barcode)`
join, oldest first. Reversion history also captures each PVP import
with the bundle id and ODK instance id.

`PvpUploadBundle.mode` snapshots the tally's `pvp_mode` at upload time
and never mutates after that, so exports and audit can always answer
"what mode was applied to this form?" even if `Tally.pvp_mode` is
later changed.

## What's not in scope yet

- `pvp_mode` immutability — admins can flip `Tally.pvp_mode` at any
  time. Future bundles use the new mode; existing bundles/submissions
  remember the mode they were imported under via
  `PvpUploadBundle.mode`. Locking the mode mid-tally is a separate
  decision.
- No PVP-specific reporting beyond the per-form badge and two new
  columns (`from_pvp`, `pvp_mode_applied`) in the row-per-form CSV
  exports.
- No support for replacement-form barcodes — the PVP devices won't
  scan them, by design.

## Trying it locally

The docker-compose stack seeds a small *Demo Tally* (typically `id=1`
on a fresh DB; 2 ballots, 6 candidates, 2 centers, 4 stations, 8 result
forms) on boot so the PVP upload flow can be exercised end-to-end
without setting up a real tally.

```bash
TALLY_HO_HTTP_PORT=9000 docker-compose up
```

1. Log in at <http://localhost:9000> as `tally_manager` / `data`, edit the
   Demo Tally and set *PVP Mode* to `DE1_ONLY` or `DE1_AND_DE2`.
2. Generate a bundle that matches the demo tally:

   ```bash
   ./build.sh create_demo_pvp_bundle --tally-id 1
   ```

   `./build.sh` is a thin wrapper around
   `docker-compose exec -e DJANGO_SETTINGS_MODULE=tally_ho.settings.docker
   web python manage.py …`. The zip lands on the host at
   `data/demo_pvp_bundle_1.zip` (the web container's `/code/` is
   bind-mounted from the project root).
3. Log out, log in as `super_administrator` / `data`, open
   *Admin Operations → Upload PVP Bundle*, upload the zip, and confirm.
4. The result page updates in place; the demo forms end up at
   `DATA_ENTRY_2` (under `DE1_ONLY`) or `QUALITY_CONTROL` (under
   `DE1_AND_DE2`) with a *PVP* badge on their print covers and a
   reversion history entry attributing the import to
   `super_administrator`.

Helper commands:

| Command | What it does |
|---|---|
| `./build.sh create_demo_tally [--clean]` | Idempotently seeds the demo tally (super-admin link + quarantine checks included). Wired into compose boot. |
| `./build.sh create_demo_pvp_bundle --tally-id N [--output PATH]` | Emits a bundle zip targeting every result form in tally `N`. Defaults to `data/demo_pvp_bundle_<N>.zip`. |

## Where it lives in code

| Component | Path |
|---|---|
| ODK pull tool (separate repo) | `odk-central-sync/` |
| `Tally.pvp_mode` model field | `tally_ho/apps/tally/models/tally.py` |
| `PvpUploadBundle` model | `tally_ho/apps/tally/models/pvp_upload_bundle.py` |
| `PvpSubmission` model | `tally_ho/apps/tally/models/pvp_submission.py` |
| Bundle parser | `tally_ho/libs/pvp/bundle.py` |
| Parse-time validation | `tally_ho/libs/pvp/validation.py` |
| Per-row + bundle import | `tally_ho/libs/pvp/import_submission.py` |
| Celery task | `tally_ho/apps/tally/management/commands/async_pvp_import.py` |
| Upload / confirm / result views | `tally_ho/apps/tally/views/pvp.py` |
| Templates | `tally_ho/apps/tally/templates/super_admin/pvp_*.html` |
| `pvp_badge` template tag | `tally_ho/apps/tally/templatetags/pvp_tags.py` |
| Export columns | `tally_ho/libs/views/exports.py` |
| Status JSON endpoint (`PvpStatusView`) | `tally_ho/apps/tally/views/pvp.py` |
| Reusable polling primitive | `tally_ho/apps/tally/static/js/async_status.js` |
| Demo seed commands | `tally_ho/apps/tally/management/commands/create_demo_{tally,pvp_bundle}.py` |
