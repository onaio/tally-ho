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
