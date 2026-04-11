# Preliminary Vote Integration (PVP) — First Pass

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let tally-ho ingest PVP (Preliminary Vote Protocol) results from ODK Central via a portable-media upload bundle, so that a majority of result forms can skip the manual Data Entry 1 pass during the live tally.

**Why:** HNEC plans to deploy PVP on ~60% of stations. Tally-ho must remain airgapped, so we cannot pull from ODK Central directly — we rely on the companion tool `odk-central-sync/` to produce a zip bundle on a network-connected machine, then carry it into the tally environment on portable media.

**Architecture:**

```text
ODK Central ──► odk-central-sync ──► zip bundle ──► (portable media) ──► Tally-ho upload view
                                                                                │
                                                                                ├─ Parse + validate
                                                                                ├─ Confirmation screen
                                                                                │   (will-import list + will-exclude list)
                                                                                ▼  (user confirms)
                                                                         Celery import task
                                                                                │
                                                                                ├─ Resolve barcode → ResultForm
                                                                                ├─ Apply tally.pvp_mode
                                                                                ├─ Write DE1 Results
                                                                                ├─ Write DE1 ReconciliationForm
                                                                                ├─ Store PvpSubmission + images
                                                                                ├─ Advance form_state to DATA_ENTRY_2
                                                                                └─ Tag ResultForm via FK
```

The upload lands a form at `DATA_ENTRY_2` with `EntryVersion.DATA_ENTRY_1` results already written. The human DE2 clerk then enters the form normally; if round-2 matches, it proceeds to corrections/QC as usual; if it doesn't, the existing corrections flow handles the discrepancy.

**Tech stack:** Django, Celery, pyODK + pandas + click (companion sync tool), pytest.

**GitHub Issue:** _(TBD — link when filed)_

---

## Scope

### In scope (pass 1)

- Sync tool (`odk-central-sync`) emits barcode + round1/round2 candidate votes + all `reconciliation_r1-*`/`reconciliation_r2-*` fields in the bundled CSV.
- New models: `PvpUploadBundle`, `PvpSubmission`.
- New `Tally.pvp_mode` enum field (`DISABLED`, `DE1_ONLY`, `DE1_AND_DE2`).
- `ResultForm.pvp_submission` FK.
- Upload screen under super_admin: zip upload → validation → confirmation → async import.
- Celery task that performs the import, matching the existing `import_result_forms` async pattern.
- `DE1_ONLY` mode implementation: PVP round2 data populates `EntryVersion.DATA_ENTRY_1` candidate results + reconciliation form; form advances to `DATA_ENTRY_2` for a human clerk to enter independently.
- `DE1_AND_DE2` mode wired into the enum and config UI but **not implemented** — picking it errors/warns "coming in pass 2." This is deliberate so the config lives in the right shape from day one.
- Sanity checks run at parse time: required fields present, barcode resolves to a form in this tally, form is in `UNSUBMITTED`. Invalid rows appear in the "will exclude" list with a reason; valid rows appear in the "will import" list.
- Duplicate detection: if a bundle contains more than one PVP submission for the same `(barcode, tally)`, **reject the entire bundle** with a clear error. Pass 2 will add a picker.
- Idempotency: a `ResultForm` that already has a non-null `pvp_submission` FK is excluded on re-upload with reason `already_imported`.
- Tagging of PVP-sourced forms in result form detail views, print covers, and row-per-form exports (DuckDB).
- Images from the bundle (`clerk_signature`, `forms_picture_1st_page`, `forms_picture_2nd_page`) stored as `FileField`s on `PvpSubmission` under `MEDIA_ROOT/pvp/<tally_id>/<submission_id>/`.
- Permissions: super admin only.

### Out of scope (pass 1)

- `DE1_AND_DE2` mode implementation (enum value exists, UI disables it, pass 2 will wire it up).
- `pvp_mode` immutability / lock-once-tally-has-begun. Pass 1 lets an admin edit `pvp_mode` at any time. Pass 2 will revisit immutability alongside `DE1_AND_DE2`.
- "QC as corrections" flow (only relevant with `DE1_AND_DE2`).
- Per-form selection on the "will import" list. Pass 1 is bulk-confirm only; pass 2 adds a picker.
- Reporting: no PVP dashboards, no PVP filter on existing reports. Pass 1 only has the per-form "sourced from PVP" badge.
- Sequence-number-as-votes sanity check. It's a reasonable check but belongs in a general result-form validation effort, not PVP-specific work.
- Quarantine-style votes-vs-recon checks. The existing quarantine/recon validation layer handles these at DE2 / corrections time.
- Hash-on-download / verify-on-upload integrity check. Cheap to add later; not critical for pass 1.
- Staff Registration Form import. Never.
- Reset-to-unsubmitted behavior for PVP forms. Pass 1 does nothing special; pass 2 may add a dedicated "reset PVP" step.
- Replacement forms via PVP. PVP devices only accept barcodes that map to center/station/ballot, and replacement-form barcodes don't. No-op by design.

### Open for review (to surface at next review meeting)

**Reconciliation field mapping.** The PVP ODK form does **not** capture `number_of_voters` (voters in the station's voter register). Tally-ho's `ReconciliationForm.number_of_voters` is a required field, transcribed from the paper by the manual DE clerk. Pass 1 derives it from `Station.registrants` at import time — lossy but non-blocking. This needs a review decision (either update the PVP ODK form to capture the field, or confirm that deriving from the station register is acceptable policy).

| tally-ho `ReconciliationForm` field | PVP source (round 2) | Fit |
|---|---|---|
| `number_of_voters` | **none** | **GAP — pass 1 derives from `Station.registrants`** |
| `number_of_voter_cards_in_the_ballot_box` | `reconciliation_r2-number_voter_cards_r2` | clean 1:1 |
| `number_valid_votes` | `reconciliation_r2-number_valid_ballots_r2` | clean 1:1 |
| `number_invalid_votes` | `reconciliation_r2-number_invalid_ballots_r2` | clean 1:1 |
| `number_sorted_and_counted` | `reconciliation_r2-number_ballots_inside_box_r2` | clean 1:1 |
| `ballot_number_from` / `ballot_number_to` | **none** | left null (already nullable) |
| `notes` | **none** | left null |
| _(no home)_ | `reconciliation_r2-number_ballots_received_r2` | **ORPHAN — stored in `PvpSubmission.recon_raw` JSON only** |

---

## Data model

```python
# tally_ho/libs/models/enums/pvp_mode.py  (new)
class PvpMode(Enum):
    DISABLED    = 0  # ignore PVP uploads for this tally
    DE1_ONLY    = 1  # PVP populates DE1; human clerk enters DE2 normally
    DE1_AND_DE2 = 2  # pass 2 — NOT implemented in pass 1

# tally_ho/libs/models/enums/pvp_import_status.py  (new)
class PvpImportStatus(Enum):
    IMPORTED = 0
    EXCLUDED = 1  # sanity check failed
    ALREADY_IMPORTED = 2  # ResultForm already tagged

# tally_ho/apps/tally/models/tally.py  (modified)
class Tally(BaseModel):
    ...
    pvp_mode = EnumIntegerField(PvpMode, default=PvpMode.DISABLED)

# tally_ho/apps/tally/models/pvp_upload_bundle.py  (new)
class PvpUploadBundle(BaseModel):
    tally = FK(Tally)
    uploaded_by = FK(UserProfile)
    filename = CharField(max_length=512)
    total_submissions = PositiveIntegerField()
    imported_count = PositiveIntegerField(default=0)
    excluded_count = PositiveIntegerField(default=0)
    already_imported_count = PositiveIntegerField(default=0)

# tally_ho/apps/tally/models/pvp_submission.py  (new)
class PvpSubmission(BaseModel):
    tally = FK(Tally)
    bundle = FK(PvpUploadBundle, related_name='submissions')
    result_form = FK(ResultForm, null=True, related_name='+')  # null if excluded
    odk_instance_id = CharField(max_length=255)  # from meta-instanceID
    odk_form_id = CharField(max_length=255)      # e.g. "results_14065"
    barcode = CharField(max_length=255, null=True)
    staff_user_name = CharField(max_length=255, null=True)
    submission_date = DateTimeField(null=True)
    status = EnumIntegerField(PvpImportStatus)
    exclusion_reason = CharField(max_length=128, null=True)
    pvp_mode_applied = EnumIntegerField(PvpMode, null=True)

    # Raw payloads — kept for provenance + future pass 2 dupe/round handling
    round1_raw = JSONField(default=dict)  # {candidate_id: votes}
    round2_raw = JSONField(default=dict)  # {candidate_id: votes}
    recon_raw  = JSONField(default=dict)  # {r1-*: n, r2-*: n} — includes orphan ballots_received

    # Images (stored under MEDIA_ROOT/pvp/<tally_id>/<submission_id>/)
    clerk_signature = FileField(upload_to=_pvp_upload_to, null=True)
    forms_picture_1st_page = FileField(upload_to=_pvp_upload_to, null=True)
    forms_picture_2nd_page = FileField(upload_to=_pvp_upload_to, null=True)

    class Meta:
        unique_together = (('tally', 'odk_instance_id'),)

# tally_ho/apps/tally/models/result_form.py  (modified)
class ResultForm(BaseModel):
    ...
    pvp_submission = OneToOneField(
        PvpSubmission, null=True, on_delete=models.SET_NULL,
        related_name='linked_result_form',
    )

    @property
    def from_pvp(self) -> bool:
        return self.pvp_submission_id is not None
```

---

## Import algorithm (pass 1, `DE1_ONLY`)

Per PVP submission row:

```text
1. If tally.pvp_mode == DISABLED:
     record EXCLUDED(reason="disabled"); skip.
2. Resolve ResultForm by (barcode, tally):
     if not found → EXCLUDED(reason="barcode_not_found"); skip.
3. If result_form.form_state != UNSUBMITTED:
     EXCLUDED(reason="form_not_unsubmitted"); skip.
4. If result_form.pvp_submission_id is not None:
     ALREADY_IMPORTED; skip.
5. (Bundle-level precheck already ran duplicate detection; we're guaranteed
    one row per barcode here.)
6. For each candidate row in the submission:
     Write Result(candidate, result_form, entry_version=DATA_ENTRY_1,
                  votes=candidate_result_round2, active=True, user=<pvp system user>)
7. Write ReconciliationForm(
        result_form, entry_version=DATA_ENTRY_1, active=True,
        number_of_voters=station.registrants,  # derived — see "Open for review"
        number_of_voter_cards_in_the_ballot_box=reconciliation_r2-number_voter_cards_r2,
        number_valid_votes=reconciliation_r2-number_valid_ballots_r2,
        number_invalid_votes=reconciliation_r2-number_invalid_ballots_r2,
        number_sorted_and_counted=reconciliation_r2-number_ballots_inside_box_r2,
        ballot_number_from=None, ballot_number_to=None, notes=None,
        user=<pvp system user>,
    )
8. Transition form_state: UNSUBMITTED → DATA_ENTRY_2.
   (Bypasses the usual INTAKE → DATA_ENTRY_1 path because PVP is DE1.)
9. Save PvpSubmission (status=IMPORTED, pvp_mode_applied=DE1_ONLY,
    images saved from the zip), link result_form.pvp_submission = this.
```

Important: pass 1 does **not** auto-populate DE2. Human clerks still enter DE2 independently. Corrections catches any discrepancy between PVP-sourced DE1 and human DE2.

### Bundle-level validation (runs before any per-row import)

1. **Zip opens cleanly** and contains `candidate_results.csv` at the root.
2. **Required columns present** in the CSV: `barcode`, `ballot_number`, `candidate_id`, `candidate_order`, `candidate_result_round1`, `candidate_result_round2`, the recon r2 fields, the image columns, `meta-instanceID`.
3. **Image integrity:** for each non-null image filename referenced in the CSV, check that `media/<filename>` exists in the zip. Missing images → warning on the confirmation screen; user can proceed (images left null on those submissions) or cancel.
4. **Duplicate detection:** if more than one submission row exists for any `(barcode, tally)`, reject the whole bundle with an error listing the offending barcodes.

### Sanity checks (per row)

| Name | Rule | Action on fail |
|---|---|---|
| `required_fields` | `barcode`, `ballot_number`, `meta-instanceID`, at least one candidate row with non-null `candidate_result_round2` | EXCLUDED(reason=`required_fields`) |
| `barcode_in_tally` | barcode must resolve to a `ResultForm` in **this tally** | EXCLUDED(reason=`barcode_not_found`) |
| `form_unsubmitted` | resolved form's `form_state == UNSUBMITTED` | EXCLUDED(reason=`form_not_unsubmitted`) |

---

## UI

**Upload screen** (`super-admin/<tally_id>/pvp/upload/`)

- File input for the zip.
- On POST, parse the bundle, run validation, redirect to confirmation.

**Confirmation screen** (`super-admin/<tally_id>/pvp/confirm/<bundle_id>/`)

- Shows `tally.pvp_mode` prominently ("PVP data will be imported as DE1 ONLY").
- "Will import" section: count + expandable list of `(barcode, center, station, ballot)` tuples.
- "Will exclude" section: count + expandable list of `(barcode, reason)`.
- "Missing images" warning: count + expandable list, with radio "proceed without images" / "cancel."
- Already-imported section: count + expandable list.
- Confirm button (enqueues Celery task) / Cancel button (discards the bundle).

**Result screen** (`super-admin/<tally_id>/pvp/result/<bundle_id>/`)

- Displayed after the Celery task runs.
- Final counts: imported, excluded, already-imported, errors.
- Link back to form progress.

**Result form tagging** (in detail view, print cover, row-per-form exports)

- A "PVP" badge + "Populated from PVP on `<date>` in mode `<pvp_mode_applied>`" caption.

---

## Task breakdown

Each task lands as a separate commit with tests green. Follow TDD: write the failing test, then the implementation, then refactor. Use `uv run pytest` to run tests.

### Task 1: Update `odk-central-sync` to emit barcode + rounds + recon

**Files:**

- Modify: `odk-central-sync/src/download_results_forms.py`
- Modify: `odk-central-sync/tests/` (add or create if empty — the project has a `tests` folder)

**Step 1 — failing test.** Write a test that loads a fixture zip of an ODK submission (one already exists at `odk-central-sync/results-output/14065/results.zip`) and asserts that `export_center_candidate_results` returns a DataFrame containing columns: `barcode`, `candidate_result_round1`, `candidate_result_round2`, `reconciliation_r1_number_ballots_received_r1`, ..., `reconciliation_r2_number_ballots_inside_box_r2`.

**Step 2 — implementation.** In `export_center_candidate_results`, extend the merge columns in the submissions DataFrame selection (line 147-155) to include:

- `intro-barcode` (rename to `barcode` in the merged DataFrame)
- All `reconciliation_r1-*` and `reconciliation_r2-*` numeric fields
- Note: `candidate_result_round1` and `candidate_result_r2-candidate_result_round2` already come through the candidate_results CSV; rename the r2 column to `candidate_result_round2` for cleanliness.

**Step 3 — tests pass, commit:**

```bash
git add odk-central-sync/src/download_results_forms.py odk-central-sync/tests/
git commit -m "odk-central-sync: extract barcode + rounds + reconciliation fields"
```

---

### Task 2: Create `PvpMode` and `PvpImportStatus` enums

**Files:**

- Create: `tally_ho/libs/models/enums/pvp_mode.py`
- Create: `tally_ho/libs/models/enums/pvp_import_status.py`
- Create: `tally_ho/libs/tests/models/enums/test_pvp_mode.py`

**Step 1 — tests.** Assert that `PvpMode.DISABLED.value == 0`, `DE1_ONLY == 1`, `DE1_AND_DE2 == 2`.

**Step 2 — implementation.** Match the pattern in `tally_ho/libs/models/enums/form_state.py` (uses `tally_ho.libs.utils.enum.Enum`, not stdlib).

**Step 3 — commit.**

---

### Task 3: Add `Tally.pvp_mode` field

**Files:**

- Modify: `tally_ho/apps/tally/models/tally.py`
- Create: `tally_ho/apps/tally/migrations/XXXX_tally_pvp_mode.py`
- Modify: `tally_ho/apps/tally/tests/models/test_tally.py` (create if missing)
- Modify: `tally_ho/apps/tally/forms/` — check whether there's a tally edit form; if so add `pvp_mode` to it with `DE1_AND_DE2` disabled in the widget.

**Step 1 — tests.** Assert a Tally saves with `pvp_mode=DISABLED` by default, and can be updated to `DE1_ONLY`.

**Step 2 — implementation.** Add the `EnumIntegerField(PvpMode, default=PvpMode.DISABLED)` field. Migration. In the tally edit form / super-admin UI, render the enum as a dropdown but disable the `DE1_AND_DE2` option with a tooltip "coming in pass 2."

**Step 3 — commit.**

---

### Task 4: Create `PvpUploadBundle` model

**Files:**

- Create: `tally_ho/apps/tally/models/pvp_upload_bundle.py`
- Modify: `tally_ho/apps/tally/models/__init__.py` (export)
- Create: migration
- Create: `tally_ho/apps/tally/tests/models/test_pvp_upload_bundle.py`

**Step 1 — tests.** Create a bundle row and assert fields save/load. Assert default counts are zero.

**Step 2 — implementation.** Model per the data-model sketch above. `BaseModel` subclass.

**Step 3 — commit.**

---

### Task 5: Create `PvpSubmission` model

**Files:**

- Create: `tally_ho/apps/tally/models/pvp_submission.py`
- Modify: `tally_ho/apps/tally/models/__init__.py`
- Create: migration
- Create: `tally_ho/apps/tally/tests/models/test_pvp_submission.py`

**Step 1 — tests.**

- Create a submission with raw JSON payloads and image files; assert round-trip.
- Assert `(tally, odk_instance_id)` uniqueness is enforced.
- Assert images save under `MEDIA_ROOT/pvp/<tally_id>/<submission_id>/`.

**Step 2 — implementation.** Per sketch. Write the `_pvp_upload_to` function that computes the image path from the submission's `tally_id` and pre-save id (or use a two-step save — save submission, then save images referencing `self.id`).

**Step 3 — commit.**

---

### Task 6: Add `ResultForm.pvp_submission` FK

**Files:**

- Modify: `tally_ho/apps/tally/models/result_form.py`
- Create: migration
- Modify: `tally_ho/apps/tally/tests/models/test_result_form.py`

**Step 1 — tests.** Assert `result_form.from_pvp` is `False` by default and `True` after linking a `PvpSubmission`. Assert unlinking (setting to null) flips it back.

**Step 2 — implementation.** `OneToOneField(PvpSubmission, null=True, on_delete=models.SET_NULL, related_name='linked_result_form')` + `from_pvp` property.

**Step 3 — commit.**

---

### Task 7: Bundle parser

**Files:**

- Create: `tally_ho/libs/utils/pvp_bundle.py`
- Create: `tally_ho/libs/tests/utils/test_pvp_bundle.py`
- Create: `tally_ho/libs/tests/fixtures/pvp/` — place a real bundle zip fixture here (copy from `odk-central-sync/results-output/` after running task 1).

**Step 1 — tests.**

- Valid bundle → returns a dataclass/namedtuple `ParsedBundle(rows, missing_images, total)`.
- Bundle missing `candidate_results.csv` → raises `InvalidBundleError`.
- Bundle with missing required columns → raises `InvalidBundleError`.
- Bundle with a referenced image not present in the zip → adds an entry to `missing_images` list, does not raise.
- Bundle with two rows having the same barcode → raises `DuplicateBarcodeError` listing the barcodes.

**Step 2 — implementation.** Pure function over the zip path. No Django imports (so it's testable as a plain unit test).

**Step 3 — commit.**

---

### Task 8: Sanity-check module

**Files:**

- Create: `tally_ho/libs/utils/pvp_sanity.py`
- Create: `tally_ho/libs/tests/utils/test_pvp_sanity.py`

**Step 1 — tests.** One test per check: `required_fields`, `barcode_in_tally`, `form_unsubmitted`. Each test asserts both the pass case and the fail case with the right `reason` code.

**Step 2 — implementation.** Single function `run_sanity_checks(row, tally, result_form_by_barcode) -> SanityResult(status, reason)`.

**Step 3 — commit.**

---

### Task 9: Per-submission import (pure function)

**Files:**

- Create: `tally_ho/libs/utils/pvp_import.py`
- Create: `tally_ho/libs/tests/utils/test_pvp_import.py`

**Step 1 — tests.**

- Given a row that passes all sanity checks, import writes `EntryVersion.DATA_ENTRY_1` `Result` rows matching round2 values.
- Import writes a DE1 `ReconciliationForm` with the mapping from the table above, `number_of_voters` pulled from `station.registrants`.
- Form state transitions from `UNSUBMITTED` → `DATA_ENTRY_2`.
- `PvpSubmission` is created with `status=IMPORTED`, `pvp_mode_applied=DE1_ONLY`, images attached.
- `ResultForm.pvp_submission` is linked.
- Idempotency: calling twice on the same form short-circuits the second call to `ALREADY_IMPORTED`.

**Step 2 — implementation.** One function `import_submission(parsed_row, tally, bundle, system_user) -> PvpSubmission`. Atomic (`@transaction.atomic`). Matches the algorithm in the "Import algorithm" section above.

**Step 3 — commit.**

---

### Task 10: Bundle-level import orchestrator

**Files:**

- Modify: `tally_ho/libs/utils/pvp_import.py`
- Modify: `tally_ho/libs/tests/utils/test_pvp_import.py`

**Step 1 — tests.**

- Given a parsed bundle with 3 valid + 1 invalid row, orchestrator creates 3 `IMPORTED` submissions and 1 `EXCLUDED` submission, updates the bundle's counts.
- Given a bundle where the tally's `pvp_mode == DISABLED`, every row becomes `EXCLUDED(disabled)`.

**Step 2 — implementation.** `import_bundle(parsed_bundle, tally, uploaded_by) -> PvpUploadBundle`. Creates the `PvpUploadBundle` row, iterates rows, calls `import_submission` per row, updates counters.

**Step 3 — commit.**

---

### Task 11: Celery task wrapper

**Files:**

- Create: `tally_ho/apps/tally/management/commands/async_pvp_import.py` (matching the `import_result_forms.py` pattern that uses `@app.task()` — see `tally_ho/apps/tally/management/commands/import_result_forms.py:178`)
- Create: `tally_ho/apps/tally/tests/management/commands/test_async_pvp_import.py`

**Step 1 — tests.** Assert the task (called synchronously via `.apply()`) end-to-end imports a fixture bundle and updates the `PvpUploadBundle` row.

**Step 2 — implementation.** `@app.task()` function that takes a path to the saved bundle zip + the `PvpUploadBundle.id` + the user id, runs `parse_bundle` then `import_bundle`, saves results.

**Step 3 — commit.**

---

### Task 12: Upload view + templates

**Files:**

- Create: `tally_ho/apps/tally/views/pvp.py`
- Create: `tally_ho/apps/tally/forms/pvp_upload_form.py`
- Create: `tally_ho/apps/tally/templates/super_admin/pvp_upload.html`
- Create: `tally_ho/apps/tally/templates/super_admin/pvp_confirm.html`
- Create: `tally_ho/apps/tally/templates/super_admin/pvp_result.html`
- Modify: `tally_ho/urls.py` — add `super-admin/<tally_id>/pvp/upload/`, `.../confirm/<bundle_id>/`, `.../result/<bundle_id>/`
- Create: `tally_ho/apps/tally/tests/views/test_pvp_views.py`

**Step 1 — tests.**

- Unauthorized user → 403.
- Super admin GET → renders upload form.
- Super admin POST valid zip → redirects to confirm page with bundle id.
- Super admin POST invalid zip → shows error on the upload form.
- Confirm page shows the counts and row lists.
- POST confirm → enqueues Celery task (mocked with `.apply()` for the test) and redirects to result page.

**Step 2 — implementation.** Views use the `super_admin` mixin pattern from existing views.

**Step 3 — commit.**

---

### Task 13: Result form tagging in templates

**Files:**

- Modify: `tally_ho/apps/tally/templates/super_admin/result_form_detail.html` (find the actual template name first)
- Modify: `tally_ho/apps/tally/templates/print_cover_common.html`
- Modify any result-form list templates that show per-form status
- Create/modify template tag tests

**Step 1 — tests.** Render the templates with a PVP-sourced form and assert the "PVP" badge + caption text are present. Render with a non-PVP form and assert absent.

**Step 2 — implementation.** A small inclusion template tag `{% pvp_badge result_form %}` in `tally_ho/apps/tally/templatetags/` that renders nothing when `not result_form.from_pvp` and renders a span with the pvp_mode_applied caption otherwise.

**Step 3 — commit.**

---

### Task 14: Row-per-form exports include PVP columns

**Files:**

- Find the DuckDB export code (likely under `tally_ho/apps/tally/views/reports/` or `tally_ho/apps/tally/management/commands/export_candidate_results.py`)
- Modify to add `from_pvp` (bool) and `pvp_mode_applied` (string) columns to the row-per-form outputs
- Modify/create export tests

**Step 1 — tests.** Export a tally with a mix of PVP and non-PVP forms; assert the two new columns are populated correctly.

**Step 2 — implementation.** Add the column expressions to the DuckDB query (or Django queryset) that generates the export.

**Step 3 — commit.**

---

### Task 15: Docs update

**Files:**

- Modify: `odk-central-sync/README.md` — document the new output columns
- Create: `docs/overview/pvp.md` — user-facing explainer: what PVP is, the upload flow, what the pass 1 badge means, what's deferred to pass 2

**Step 1 — commit.** No tests; prose only.

---

## Pass 2 backlog (explicit — do not start)

Collected from the scoping conversation and from in-line "pass 2" notes above:

- Implement `DE1_AND_DE2` mode (read round1 into DE1, round2 into DE2, route to QC-as-corrections).
- Decide and enforce `pvp_mode` immutability (lock-once-tally-has-begun; pick (i)/(ii)/(iii) from the scoping discussion).
- Pass 2 discussion: whether the QC-as-corrections step should reuse `QUALITY_CONTROL`, `CORRECTION`, or a new `PVP_REVIEW` state.
- Per-form selection UI on the "will import" list.
- Multiple PVP submissions per `(barcode, tally)` — add picker (latest complete, user chooses, etc.) instead of rejecting the bundle.
- "Reset PVP" admin action — explicit step to unlink `ResultForm.pvp_submission` so the form can be re-processed.
- Hash-on-download / verify-on-upload integrity check.
- Reporting dashboard: PVP vs non counts, QC rejection rates, audit-trigger rates, breakdown by ballot/race/sub-con.
- PVP filter on existing reports.
- Review decision on the `number_of_voters` gap (update the ODK form, or confirm station-register derivation is acceptable).
- Consider whether PVP-sourced forms should have stricter reconciliation requirements.
- Consider eligibility: weaken the "only `UNSUBMITTED`" rule to also permit `CLEARANCE` (or any pre-DE state) after admin review.
