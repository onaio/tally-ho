# Result Form Images — display PVP bundle images + optional manual upload

**Status:** DRAFT FOR REVIEW — not yet approved for implementation.

**Goal:** Give every result form a unified set of attached images, stored,
displayed, and managed identically regardless of origin. The image comes
from one of two sources:

1. **Imported** — the `clerk_signature`, `forms_picture_1st_page`, and
   `forms_picture_2nd_page` images that arrive inside a PVP bundle zip and
   today are extracted onto `PvpSubmission` and never displayed.
2. **Uploaded** — an optional image a clerk attaches while working on a
   form, including non-PVP forms.

**Why:** PVP bundles already carry photographs of the signed paper form,
but nothing renders them — the provenance is captured and then invisible.
Separately, clerks working a normal (non-PVP) form have no way to attach a
photo of the paper. Both needs are the same feature with two ingest paths.

**Non-goal:** Not a document-management system. Images only (JPEG/PNG). No
PDFs, no versioning, no annotation.

---

## Release split

**v1 — generalize + display.** Introduce the unified `ResultFormImage`
model, route the PVP bundle images into it, and display them on every form
screen. No manual upload UI. Because v1 is the first thing in the app to
render a stored image, the authenticated media view ships here too — the
sensitive PVP form photos must not be served from the open `^media/` route
the moment they become visible.

**v2 — manual upload.** Add the "attach an image" form, the delete action,
and the permission/state rules around them. The model, display component,
and secure media serving already exist from v1, so v2 is purely the
write/remove UI: a manual upload is just a `ResultFormImage` row with
`source=UPLOAD` flowing through the same display and storage v1 built.

The model carries `source`, `kind`, `caption`, and `uploaded_by` from v1
even though v1 only ever writes `PVP_IMPORT` rows — so v2 adds no schema
migration, only a form and two views.

---

## Decision: one storage home (`ResultFormImage`), not two

PVP shipped to `main` but is **not deployed** — there is no production PVP
image data. That removes any backfill/migration concern and makes the
clean single-table design free to adopt.

**All images applied to a form live in one table, `ResultFormImage`.** A
`source` field records how the image arrived (`UPLOAD` vs `PVP_IMPORT`); a
nullable `pvp_submission` FK records which bundle an imported image came
from. `PvpSubmission` **loses its three image `FileField`s** — the PVP
import writes `ResultFormImage` rows directly instead of storing images on
the submission.

Two facts make this the honest model rather than a lossy one:

- **The raw image source of truth is the retained bundle zip**
  (`PvpUploadBundle.zip_file`), not a `PvpSubmission` FileField. The
  original images are always recoverable from the zip, so moving the
  applied image into `ResultFormImage` loses no provenance — the
  `pvp_submission` FK keeps the link.
- **`PvpSubmission` stays a pure raw-payload record** — `round2_raw`,
  `recon_raw` (JSON). It never should have been the display home for
  images; that was incidental.

Result: one queryable table. `result_form.images.all()`, `Count('images')`,
"forms missing a signature", the export "has images" column, and any future
PVP reporting are all plain ORM — no Python-level accessor merging two
storage locations.

```text
             ┌──────────────────────────┐
  PVP bundle │ PvpUploadBundle.zip_file  │  ← raw image source of truth
  ──────────►│  (retained)               │    (images live in media/<f> here)
             └───────────┬──────────────┘
                         │ import extracts + writes
                         ▼
  manual upload ───►┌─────────────────────────┐
  (source=UPLOAD)   │ ResultFormImage         │  one home for all applied
                    │  source, kind, caption   │  images on a form
                    │  pvp_submission (FK,null) │◄─ provenance link when imported
                    └───────────┬──────────────┘
                                │ FK (related_name="images")
                                ▼
                           ResultForm ──► one include renders images on
                                          every form screen
```

---

## Data model

```python
# tally_ho/libs/models/enums/result_form_image_source.py  (new)
class ResultFormImageSource(Enum):
    UPLOAD     = 0  # a user attached it while working the form
    PVP_IMPORT = 1  # extracted from a PVP bundle at import time

# tally_ho/libs/models/enums/result_form_image_kind.py  (new)
class ResultFormImageKind(Enum):
    SUPPORTING       = 0  # default for manual uploads
    CLERK_SIGNATURE  = 1  # PVP clerk_signature
    FORM_PAGE_1      = 2  # PVP forms_picture_1st_page
    FORM_PAGE_2      = 3  # PVP forms_picture_2nd_page

# tally_ho/apps/tally/models/result_form_image.py  (new)
class ResultFormImage(BaseModel):
    tally        = FK(Tally, on_delete=PROTECT)
    result_form  = FK(ResultForm, related_name="images", on_delete=CASCADE)
    image        = ImageField(upload_to=result_form_image_upload_to)
    source       = EnumIntegerField(ResultFormImageSource,
                                    default=ResultFormImageSource.UPLOAD)
    kind         = EnumIntegerField(ResultFormImageKind,
                                    default=ResultFormImageKind.SUPPORTING)
    caption      = CharField(max_length=255, null=True, blank=True)
    uploaded_by  = FK(UserProfile, null=True, on_delete=SET_NULL)
    # Provenance link when source == PVP_IMPORT (null for manual uploads).
    pvp_submission = FK(PvpSubmission, null=True, blank=True,
                        on_delete=SET_NULL, related_name="applied_images")

# path: form_images/<tally_id>/<result_form_id>/<filename>
```

`ImageField` (not `FileField`) so Pillow validates the file is a real
image at save time; content-type + max-size validation on the upload form.

**`PvpSubmission` change:** remove `clerk_signature`,
`forms_picture_1st_page`, `forms_picture_2nd_page`. Safe to drop with a
plain schema migration — no deployed data. The `_save_images` /
`_attach_image` logic in `import_submission.py` is repointed to write
`ResultFormImage` rows (see Task 3).

---

## Where it comes from

| Path | Trigger | Row written |
|---|---|---|
| **Upload** | Clerk POSTs a file on a form screen | `ResultFormImage(source=UPLOAD, uploaded_by=request.user, kind=SUPPORTING)` |
| **Import** | PVP bundle import extracts `media/<filename>` from the zip | one `ResultFormImage(source=PVP_IMPORT, pvp_submission=…, kind=mapped)` per non-null bundle image |

Both write the identical row shape. Display and delete never branch on source.

---

## Display

- New include `includes/_result_form_images.html` renders
  `result_form.images.all()` as a thumbnail gallery, each linking to the
  full image, captioned with source + kind + date + (for uploads) the
  uploader.
- New inclusion template tag `{% result_form_images result_form %}` — same
  pattern as the existing `{% pvp_badge %}` tag in `pvp_tags.py`.
- **Mount point:** `center_details.html`. That single template is
  `{% include %}`d by ~13 screens (data entry, QC general/dashboard,
  corrections match/required, audit review + read-only, clearance review,
  intake clearance, super-admin history + reset confirmation). Mounting
  there surfaces the gallery everywhere a form is viewed, with one edit.
- Two single-form screens do *not* include `center_details.html` —
  `ViewResultFormDetailsView` (`workflow/view_result_form_details.html`)
  and `EditResultFormView` (`super_admin/edit_result_form.html`). Add the
  tag to those two templates too if the gallery should appear there (one
  line each).
- Renders nothing when the form has no images (mirrors `_pvp_badge`).

---

## Upload (and delete) — v2

The data-entry votes form is **not** `multipart/form-data`, and a failed
image upload must never block vote submission. So images get their own
small form and endpoints, orthogonal to the vote/recon forms:

- `POST result-form/<result_form_id>/images/add/` — a
  `ResultFormImageForm` (single `image` field + optional `caption`),
  multipart, creates a `ResultFormImage(source=UPLOAD)`.
- `POST result-form/<result_form_id>/images/<image_id>/delete/` — removes
  the row and its file.
- The "Attach image" widget + the gallery both live in the
  `_result_form_images.html` include, so they appear on the same screens.

**Open — permissions & eligibility (review):** which roles may upload and
delete, and in which `form_state`s. Strawman: any user assigned to the
form's current stage (data entry, QC, corrections, audit) plus super
admin may upload; delete is restricted to super admin. Uploads allowed in
any non-archived state.

---

## Reset behavior

`reset_to_unsubmitted` (`result_form.py:515`) already nulls
`ResultForm.pvp_submission` and deactivates PVP-written results. It should
also drop the applied PVP images so a reset form doesn't keep showing a
prior bundle's photos — a one-line delete of the form's
`source=PVP_IMPORT` `ResultFormImage` rows, mirroring how reset deactivates
PVP `Result` rows. Manual-upload rows (`source=UPLOAD`) are left untouched
by default (open question below). The original images remain recoverable
from `PvpUploadBundle.zip_file`.

---

## Security: authenticated media serving

`tally_ho/urls.py:89` serves `^media/(?P<path>.*)$` via Django's `serve`
with **no authentication**. Result-form images are photographs of signed
paper ballots — sensitive. This plan adds a login-required media view for
form images that streams the file after checking the requester has access
to the tally, and routes `_result_form_images.html` links through it
rather than the raw `.url`. Whether to *also* lock down the existing open
`^media/` route is called out for review — a pre-existing gap, arguably a
separate security task.

---

## Task breakdown (TDD; each task a commit with tests green)

## v1 — generalize + display PVP images

### Task 1 — `ResultFormImageSource` + `ResultFormImageKind` enums

Enums under `tally_ho/libs/models/enums/`, matching the `PvpMode`
pattern. Tests assert values. Commit.

### Task 2 — `ResultFormImage` model + migration

Model, `__init__.py` export, `result_form_image_upload_to`, migration.
Tests: round-trip save with an image; `result_form.images` reverse
accessor; path lands under `form_images/<tally_id>/<result_form_id>/`;
`ImageField` rejects a non-image. Commit.

### Task 3 — PVP import writes `ResultFormImage`; drop `PvpSubmission` FileFields

Modify `tally_ho/libs/pvp/import_submission.py`: the existing
`transaction.on_commit` image path (`_save_images` / `_attach_image`) is
repointed to create one `ResultFormImage(source=PVP_IMPORT,
pvp_submission=…, kind=mapped)` per non-null bundle image instead of
writing `PvpSubmission` fields. Remove the three FileFields from
`PvpSubmission` + schema migration (no data — not deployed). Tests:
importing a bundle with images links N `ResultFormImage` rows to the form
with `source=PVP_IMPORT`; a submission with null images links none. Commit.

### Task 4 — Reset drops PVP-sourced images

Extend `reset_to_unsubmitted` to delete the form's `source=PVP_IMPORT`
`ResultFormImage` rows. Tests: reset removes PVP images + files; leaves
`source=UPLOAD` rows intact. Commit.

### Task 5 — Display include + template tag

`_result_form_images.html`, `result_form_images` tag, mount in
`center_details.html` (and the two non-`center_details` detail screens if
agreed). Tests: renders thumbnails for a form with images; renders nothing
for a form without; a PVP form shows its imported images. Commit.

### Task 6 — Authenticated media view for form images

Login-required streaming view with a tally-access check; point the
include's links at it. Tests: authed request with access → 200 + bytes;
no access → 403; anonymous → redirect to login. Commit.
(Decision on the existing open `^media/` route captured separately.)

### Task 7 — Exports (secondary)

Add an image count / "has images" column to the row-per-form export
(`tally_ho/libs/views/exports.py`) — a plain `Count('images')`. Tests for
the export column. Commit.

### Task 8 — Docs (v1)

Update `docs/overview/pvp.md` — imported images now display; note images
live on `ResultFormImage`, not `PvpSubmission`. Commit.

## v2 — manual upload

### Task 9 — Upload form + view + delete + URL

`ResultFormImageForm` (image + caption, size/content-type validation),
add/delete views, URLs, wire the widget into the include. Tests:
authorized POST creates a row and file; unauthorized → 403; oversized /
non-image rejected with a form error; delete removes row + file. Commit.

### Task 10 — Permissions, state rules, and reset-of-manual-uploads

Enforce which roles may upload/delete and in which `form_state`s (open
question 3), and decide whether reset clears `source=UPLOAD` rows (open
question 5). Tests per rule. Update `docs/overview/pvp.md` with the
attach-image flow. Commit.

---

## Open questions for review

1. **Model name & scope.** `ResultFormImage` (images only) vs a broader
   `ResultFormAttachment` (room for PDFs later). Recommend `ResultFormImage`
   — narrow and honest; rename later if needed.
2. **`kind` enum vs freeform.** Keep the four-value `ResultFormImageKind`
   so PVP's semantic slots survive, or collapse to "image" and let
   `source` carry meaning? Recommend keeping `kind`.
3. **Permissions.** Who may upload / delete, and in which `form_state`s?
   (Strawman above.)
4. **Authenticated media.** Guard form images only, or also close the
   pre-existing open `^media/` serve? Recommend guarding form images now,
   filing the broader `^media/` lockdown as a separate security task.
5. **Reset & manual uploads.** On reset, PVP-sourced rows are deleted
   (recommended). Should manual `source=UPLOAD` rows also be cleared, or
   survive the reset as clerk-attached evidence? Recommend survive.
6. **Validation limits.** Max file size, accepted content types, max
   images per form?
7. **Print cover.** Do the images belong on the printed cover sheet, or is
   on-screen display enough for pass 1?
