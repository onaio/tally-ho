# ODK Central Sync

Export candidate results from ODK Central for a list of centers.

## Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Copy `.pyodk_config.toml.example` to `.pyodk_config.toml` and fill in your credentials. See [pyODK docs](https://getodk.github.io/pyodk/#configure).

## Usage

Export specific centers:

```bash
uv run download-results --project-id=14 11034 11035 11036
```

Export all centers (auto-discovers `results_*` forms in the project):

```bash
uv run download-results --project-id=14
```

### Options

- `--project-id` (required) — ODK Central project ID
- `--output-dir` — Directory for output files (default: `results-output`)
- `--config` — Path to pyODK config file (default: `.pyodk_config.toml`)
- `--bundle` — Create a timestamped upload bundle in the output directory (default: `true`). Pass `--bundle=false` to skip.

## Output

Each run writes the following into `--output-dir`:

- `candidate_results.csv` — combined candidate results across all centers
- `<center_id>/results.zip` — raw ODK Central export per center (cached; reused on reruns)
- `media/` — extracted images from all centers, filenames prefixed by `center_id`
- `results_export_p<project_id>_<timestamp>.zip` — upload bundle containing `candidate_results.csv` and `media/`. This is the file to upload to the results system for integration with other results. Disable with `--bundle=false`.

### `candidate_results.csv` columns

One row per candidate per submission. Columns:

- Candidate fields from the ODK `candidate_results` repeat:
  `pos`, `candidate_id`, `candidate_order`, `candidate_name`,
  `candidate_result_round1`, `candidate_result_round2` (flattened from the
  ODK `candidate_result_r2-candidate_result_round2` path),
  `candidate_result_r2-result_note`, `PARENT_KEY`, `KEY`.
- Provenance: `xml_form_id`, `center_id`.
- Submission fields joined on `PARENT_KEY` → `meta-instanceID`:
  `station_number`, `staff_user_name`, `ballot_number`, `race_type`.
- **`barcode`** — the PVP scanned barcode (renamed from the ODK
  `intro-barcode` field). String type to preserve leading zeros.
- **Reconciliation fields** — both rounds (r1 and r2) captured by the PVP
  device, five fields each:
  `reconciliation_r1-number_ballots_received_r1`,
  `reconciliation_r1-number_voter_cards_r1`,
  `reconciliation_r1-number_valid_ballots_r1`,
  `reconciliation_r1-number_invalid_ballots_r1`,
  `reconciliation_r1-number_ballots_inside_box_r1`,
  and the equivalent `reconciliation_r2-*` columns.
- Image filenames (prefixed with `center_id`): `clerk_signature`,
  `forms_picture_1st_page`, `forms_picture_2nd_page`.
