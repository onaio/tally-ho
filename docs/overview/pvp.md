# Preliminary Vote Protocol (PVP)

PVP is HNEC's pre-tally device workflow: at the polling station, a clerk
keys in candidate results twice (round 1 and round 2) on a tablet running
an ODK form. If the two rounds match, the device captures a signed copy
that can be ingested by tally-ho — skipping the manual Data Entry 1 pass
that would otherwise be done from paper.

## How a result gets into tally-ho

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
    │                              │                                ├─ For each row:
    │                              │                                │   • DE1 Result rows (one per candidate, votes = round 2)
    │                              │                                │   • DE1 ReconciliationForm
    │                              │                                │   • Form state UNSUBMITTED → DATA_ENTRY_2
    │                              │                                │   • Link ResultForm.pvp_submission
    │                              │                                ▼
    │                              │                         Manual DE2 clerk
    │                              │                         enters DE2 normally; mismatch goes
    │                              │                         to corrections as usual.
```

## What the operator sees

1. **Configure the tally** — Tally-manager edits the tally and sets
   *PVP Mode* to `DE1_ONLY`. (`DE1_AND_DE2` is rendered as disabled in
   pass 1; coming in pass 2.)
2. **Upload a bundle** — Super-admin opens the PVP upload screen,
   selects the `.zip` produced by `odk-central-sync`. Tally-ho sanity-
   parses the zip and redirects to the confirmation screen.
3. **Confirm** — The confirmation screen shows three lists:
   - **Will import** — submissions that pass parse-time validation
   - **Will skip** — rows that fail validation, with a reason code
   - **Missing images** — image filenames referenced by the CSV but
     not present in the zip (these submissions still import, just
     with empty image fields)
4. **Result** — After confirming, a Celery task does the import. The
   result page shows the bundle status (`PENDING`, `IMPORTING`,
   `COMPLETED`, `FAILED`) and the count of submissions imported.

## Validation rules (parse-time)

A row is **skipped** (never persisted) if any of these is true:

| Reason | Meaning |
|---|---|
| `pvp_disabled` | Tally's `pvp_mode` is `DISABLED` |
| `required_fields` | Missing barcode, ballot_number, instance ID, or all rounds-2 votes |
| `barcode_not_found` | Barcode does not match any ResultForm in this tally |
| `form_not_unsubmitted` | The matched form's state is not `UNSUBMITTED` |
| `already_imported` | The matched form already has a linked PvpSubmission |

Bundle-level rejections (whole bundle fails fast):

- Zip can't be opened or `candidate_results.csv` is missing
- Required CSV columns are missing
- More than one row references the same barcode

## What the "PVP" badge means

When you see a small `PVP` badge next to a result form's barcode (on the
print cover or detail page), it means the form's DATA_ENTRY_1 results
were populated by a PVP upload rather than by a manual clerk. A caption
shows the date the bundle was imported.

## What pass 1 doesn't do (yet)

- `DE1_AND_DE2` mode is not implemented — the dropdown shows it but
  rejects it both client-side and server-side. Pass 2 wires it up.
- No retry / partial-import recovery: if the Celery task fails mid-bundle,
  some submissions may be committed. The bundle is marked `FAILED`; an
  operator can manually re-trigger after fixing the underlying issue.
- No PVP-specific reporting beyond the per-form badge and two new
  columns (`from_pvp`, `pvp_mode_applied`) in the row-per-form CSV
  exports.
- No "reset PVP" admin action — once linked, a `ResultForm.pvp_submission`
  stays linked unless the submission is explicitly deleted.
- No support for replacement-form barcodes — the PVP devices won't
  scan them, by design.

## Trying it locally

The docker-compose stack seeds a small *Demo Tally* (id `1`, 2 ballots,
6 candidates, 8 result forms) on boot so the PVP upload flow can be
exercised end-to-end without setting up a real tally.

```bash
TALLY_HO_HTTP_PORT=9000 docker-compose up
```

1. Log in at <http://localhost:9000> as `tally_manager` / `data`, edit the
   Demo Tally and set *PVP Mode* to `DE1_ONLY`.
2. Generate a bundle that matches the demo tally:

   ```bash
   docker-compose exec web python manage.py create_demo_pvp_bundle \
     --tally-id 1 --settings=tally_ho.settings.docker
   ```

   The zip lands on the host at `data/demo_pvp_bundle_1.zip` (the web
   container's `/code/` is bind-mounted from the project root).
3. Log out, log in as `super_administrator` / `data`, open
   *Admin Operations → Upload PVP Bundle*, upload the zip, and confirm.
4. After the celery task finishes, any of the 8 demo forms should be at
   `DATA_ENTRY_2` with a *PVP* badge on its print cover.

Helper commands:

| Command | What it does |
|---|---|
| `create_demo_tally` | Idempotently seeds the demo tally. `--clean` wipes it first. Wired into compose boot. |
| `create_demo_pvp_bundle --tally-id N [--output PATH]` | Emits a bundle zip targeting every result form in tally `N`. Defaults to `data/demo_pvp_bundle_<N>.zip`. |

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
