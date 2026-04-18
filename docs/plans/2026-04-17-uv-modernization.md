# Modernize tally-ho to uv

**Goal:** Migrate the main tally-ho project from pip + requirements files to uv,
matching the pattern already established in `odk-central-sync/`. Consolidate
conflicting configs, update Docker, and update CI.

**Why:** The project currently has a hybrid setup — `odk-central-sync` uses
modern uv (`pyproject.toml` + `uv.lock` + `uv sync --locked`), while the main
Django app uses pip with requirements files and an unversioned `python:3`
Docker image. CI already installs uv but uses it in pip-compatibility mode.
Ruff has two conflicting config files (py39/line-length 88 vs py312/line-length
79). Docker pins gunicorn 19.9.0 (2017) and PostgreSQL 11.1.

**Constraints:**

- Must not break existing deployments (fabric-based) until they're explicitly
  retired.
- `odk-central-sync/` is a separate sub-project with its own `pyproject.toml`
  and `uv.lock` — leave it untouched.
- The main project targets Python 3.12 (per CI). Pin to `>=3.12,<3.13`.

---

## Current state

| Aspect | Now | Target |
|---|---|---|
| Dependencies | `requirements/{common,dev,deploy}.pip` | `pyproject.toml` `[project.dependencies]` + `[dependency-groups]` |
| Lockfile | none | `uv.lock` |
| Python version | unspecified (CI uses 3.12, ruff says py39 or py312) | `requires-python = ">=3.12,<3.13"`, `.python-version` file |
| Ruff config | two files: `ruff.toml` (py39, line-length 88) + `pyproject.toml` (py312, line-length 79) | single `[tool.ruff]` section in `pyproject.toml` |
| Docker base | `python:3` (unversioned) | `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` multistage |
| Docker deps | `pip install -r common.pip` + hardcoded gunicorn 19.9.0 | `uv sync --frozen --no-dev` |
| Docker compose services | postgres:11.1, nginx:1.15.6 | postgres:15-alpine (match CI), nginx:stable-alpine |
| CI deps | `uv pip install -r requirements/dev.pip` | `uv sync --locked` |
| CI uv install | `curl` script + manual PATH | `astral-sh/setup-uv@v5` |
| CI actions | `actions/checkout@v2`, `actions/setup-python@v2` | `actions/checkout@v4`, `actions/setup-python@v5` |

---

## Task breakdown

### Task 1: Create `[project]` table in `pyproject.toml`

**Files:**

- Modify: `pyproject.toml`

**What:**

- Add `[project]` with `name`, `version`, `description`, `requires-python = ">=3.12,<3.13"`.
- Add `[build-system]` with hatchling (matching odk-central-sync pattern).
- Move all `requirements/common.pip` packages into `[project.dependencies]`.
  Pin versions as they are in the requirements file (exact pins where specified,
  compatible ranges where already ranged like `psycopg[binary]>=3.1`).
- Add gunicorn to dependencies (upgrade from 19.9.0 to current stable).
- Add `[dependency-groups]` with a `dev` group containing everything from
  `requirements/dev.pip` that isn't already in `[project.dependencies]`.
- Add a `deploy` dependency group containing `fabric`.

**Verify:** `uv lock` succeeds and produces `uv.lock`.

---

### Task 2: Create `.python-version` file

**Files:**

- Create: `.python-version`

**What:** Write `3.12` to the file. This lets `uv python install` and
`uv run` pick the right interpreter automatically.

**Verify:** `uv python install` picks up 3.12.

---

### Task 3: Consolidate ruff config

**Files:**

- Modify: `pyproject.toml` (update `[tool.ruff]` section)
- Delete: `ruff.toml`

**What:** Merge the two configs into a single `[tool.ruff]` section in
`pyproject.toml`. Decisions:

- `target-version = "py312"` (match `requires-python` and CI).
- `line-length = 79` (match existing codebase formatting — the codebase was
  written against 79, not 88).
- Lint rules: keep the current pyproject.toml rules (`E`, `F`, `W`) for now.
  The ruff.toml's more aggressive ruleset (`E4`, `E7`, `E9`, `F`) is actually
  a subset — stick with the broader set.
- Keep the `exclude` list from pyproject.toml (includes migrations, models
  `__init__.py`).
- Drop the `[format]` section from ruff.toml — it's not actively used
  (pre-commit runs `ruff --fix`, not `ruff format`).

**Verify:** `uv run ruff check tally_ho/` produces the same results as before.

---

### Task 4: Verify `uv sync` and `uv run pytest`

**Files:** none (verification only)

**What:**

- `uv sync` installs all deps into `.venv`.
- `uv run pytest tally_ho/` runs the test suite.
- Fix any import or version compatibility issues that surface.
- `uv run python manage.py check` passes.

This is the gate before touching Docker or CI.

---

### Task 5: Update Dockerfile to multistage uv build

**Files:**

- Modify: `Dockerfile`

**What:** Rewrite as a multistage build following the pattern from the
docker-uv docs:

```dockerfile
# Stage 1: Build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev
COPY . /app
RUN uv run python manage.py collectstatic --no-input

# Stage 2: Runtime
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/tally_ho/static /app/tally_ho/static
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
```

---

### Task 6: Update docker-compose.yml

**Files:**

- Modify: `docker-compose.yml`

**What:**

- Upgrade `postgres:11.1` → `postgres:15-alpine` (match CI).
- Upgrade `nginx:1.15.6` → `nginx:stable-alpine`.
- Update the `web` command to use `uv run` instead of bare `python`/`gunicorn`.
- Remove hardcoded gunicorn version (it's now in pyproject.toml dependencies).

**Verify:** `docker compose up` starts cleanly, migrations run, demo data loads.

---

### Task 7: Update CI workflow

**Files:**

- Modify: `.github/workflows/config.yml`

**What:**

- Replace `curl`-based uv install with `astral-sh/setup-uv@v5` (matching
  odk-central-sync job).
- Replace `uv pip install -r requirements/dev.pip` with `uv sync --locked`.
- Update `actions/checkout@v2` → `@v4`.
- Update `actions/setup-python@v2` → `@v5`.
- Replace venv-based cache (`./venv`) with uv's built-in caching
  (`setup-uv@v5` handles this via `enable-cache: true`).
- Update test command to use `uv run pytest`.
- Keep `actions/cache@v3` for the `uv` cache if needed, or rely on
  `setup-uv@v5`'s cache support.

**Verify:** CI passes on a test branch push.

---

### Task 8: Clean up legacy files

**Files:**

- Delete: `requirements/common.pip`
- Delete: `requirements/dev.pip`
- Delete: `requirements/deploy.pip`
- Delete: `requirements/` directory (if empty)

**What:** Remove the old requirements files. They're fully replaced by
`pyproject.toml` + `uv.lock`. Add `uv.lock` to version control.

**Verify:** `uv sync --locked` still works. CI still passes. Docker still builds.

---

### Task 9: Update developer docs

**Files:**

- Modify: `README.md` — update setup instructions to use `uv sync` instead of
  `pip install -r requirements/dev.pip`.

**What:** Replace the old virtualenvwrapper + pip setup instructions with:

```bash
uv sync          # install all dependencies
uv run pytest    # run tests
uv run python manage.py runserver  # start dev server
```

---

## Unknowns (need answers before starting)

- **`deploy/` folder and `scripts/`**: These use `pip install`, `virtualenv`,
  and fabric. Need to understand whether they're actively used in production
  and whether they need to be updated as part of this plan or can stay as-is
  temporarily. If production deploys depend on `requirements/common.pip`
  existing, we can't delete it in task 8 until the deploy path is updated too.
  **Waiting for feedback.**

## Out of scope

- Upgrading Django or other package versions beyond what's needed for
  compatibility — that's a separate effort.
- Changing the `odk-central-sync/` sub-project — it's already modern.
- `uwsgi.ini` — production server config, separate concern.
