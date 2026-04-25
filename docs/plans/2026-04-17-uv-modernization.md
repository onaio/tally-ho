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

## Unknowns (resolved)

- **`deploy/` folder and `scripts/`**: Both retired. The `deploy/` fabric
  folder was deleted (commit `db7681ca`). The dead-since-2014/2018 helper
  scripts (`scripts/install_ubuntu`, `scripts/install_app`, `scripts/deploy`,
  `scripts/deploy_replication`, `scripts/create_database`,
  `scripts/db_backup_or_restore`) were also deleted as part of the migration
  commit (`51840982`).
- **Production deploy path**: Identified — see Phase 2 below.

## Phase 1 status

Tasks 1–9 landed in commit `51840982 migrate to uv` on branch
`uv-migration`. Three notable divergences from the original plan:

- **Task 3 (ruff)** kept `line-length = 88` and `select = ["E4","E7","E9","F"]`
  — the ruleset that was actually enforced by the old `ruff.toml`. The
  plan's aspirational `line-length = 79` + broad `["E","F","W"]` would have
  introduced 78 violations across 40 files; tightening the ruleset is left
  as a separate effort.
- **Task 1 deps**: `xhtml2pdf` bumped `0.2.11` → `0.2.17` (compat-required —
  old pin pulls `reportlab==3.6.13` which can't build wheels on py3.12).
- **`deploy` dependency group skipped**: fabric was retired with the
  `deploy/` folder, so no `[dependency-groups] deploy = ["fabric"]` was added.

Follow-up (post-merge): three Dockerfile/.dockerignore tightenings landed in
a separate commit (COPY ordering bug, missing `.dockerignore`,
`.python-version` made trackable).

---

## Phase 2 — Production deploy: add `uv` mode to `onaio.django` ansible role

> **For Claude:** Implement task-by-task. Each task lands as its own commit
> in its own repo. Repos: `onaio/ansible-django` (R1),
> `onaio/ansible-tally-ho` (R2), `onaio/infrastructure` (R3).

**Goal:** Production deploys (orchestrated from `infrastructure/ansible/tally_ho.yml`)
must install dependencies via `uv sync --frozen --no-dev` against
`pyproject.toml` + `uv.lock`, instead of `pip install -r requirements/dev.pip`
(which no longer exists).

**Why:** Phase 1 deleted `requirements/*.pip`. The downstream
`onaio.ansible-django` role (consumed by `onaio.ansible-tally-ho`, consumed
by `onaio/infrastructure`) still expects `pip install -r {{ requirements }}`.
Next deploy will fail at the install step.

**Approach:** Add a new opt-in install mode `django_use_uv` to
`ansible-django` (joining the existing `django_use_regular_old_pip`,
`django_use_pipenv`, `django_use_poetry` modes). Off by default — no
behavior change for existing consumers. `tally-ho` opts in via
`ansible-tally-ho`'s `meta/main.yml`. `infrastructure` bumps the submodule.

**Scope notes:**

- `ansible-django` is a shared role — many consumers. The new mode is
  off-by-default; existing pip/pipenv/poetry paths are untouched.
- The role already installs `django_pip_packages` (uwsgi, celery,
  django-debug-toolbar, …) via a separate pip task (line 228 of
  `tasks/install.yml`) that runs **regardless** of which install mode is
  selected and targets `django_venv_path`. The new uv task only needs to
  handle the lockfile install — the existing extras task continues to work
  as-is, installing into the uv-managed venv.
- `onaio/ansible-django` will get an external review.

### Repo 1: `ansible-django` — add `django_use_uv` mode

#### Task 10: Add `django_use_uv` defaults

**Files:**

- Modify: `defaults/main.yml`

**What:** Add the new flag and its parameters alongside the existing mode flags:

```yaml
## uv (Astral)
django_use_uv: false
# Version of uv to install on the host. "latest" or a pinned version like "0.6.10".
django_uv_version: "latest"
# Path inside django_checkout_path where pyproject.toml + uv.lock live.
# Defaults to the checkout root.
django_uv_project_dir: "{{ django_checkout_path }}"
# Sync flags. Default mirrors what we want for prod: frozen lock, no dev deps.
django_uv_sync_args: "--frozen --no-dev"
```

**Verify:** `ansible-lint` clean.

---

#### Task 11: Install uv on the host

**Files:**

- Modify: `tasks/python.yml`

**What:** When `django_use_uv` is true, install uv via the official
installer script (idempotent — re-running upgrades). Install per-host
(not per-user) so it's usable across rebuilds.

```yaml
- name: Install uv (Astral)
  ansible.builtin.shell: |
    set -e
    curl -LsSf https://astral.sh/uv/{{ django_uv_version }}/install.sh \
      | env UV_INSTALL_DIR=/usr/local/bin sh
  args:
    creates: /usr/local/bin/uv
  become: true
  become_user: root
  when: django_use_uv | bool
```

Note: the `creates:` argument keeps the task idempotent without using
`changed_when: false` (which would mask real upgrades). Pinning a version
makes the `creates:` check meaningful; `latest` will only install once
unless `/usr/local/bin/uv` is removed.

**Verify:** `which uv && uv --version` on a converged host.

---

#### Task 12: Install Python packages via uv

**Files:**

- Modify: `tasks/install.yml`

**What:** Add a new task block, parallel to the existing `pipenv` /
`poetry` / `regular_old_pip` blocks (around line 121–226). Order: place
**after** the existing pip-based blocks but **before** the
`django_pip_packages` install at line 228 — so uwsgi/celery/etc. install
into the uv-created venv.

```yaml
- name: Install Python packages using uv sync
  ansible.builtin.command:
    cmd: >-
      uv sync
      {{ django_uv_sync_args }}
      --python {{ django_python_version }}
    chdir: "{{ django_uv_project_dir }}"
  environment:
    UV_PROJECT_ENVIRONMENT: "{{ django_venv_path }}"
    UV_LINK_MODE: copy
    UV_COMPILE_BYTECODE: "1"
  become: true
  become_user: "{{ django_system_user }}"
  changed_when: true
  when:
    - django_use_uv | bool
```

Why these env vars:

- `UV_PROJECT_ENVIRONMENT` directs uv to use the same venv path the rest of
  the role expects (`django_venv_path`), so uwsgi systemd units, the wsgi
  config, etc. don't change.
- `UV_LINK_MODE=copy` avoids hardlink failures across mount points.
- `UV_COMPILE_BYTECODE=1` matches the prod Dockerfile pattern.

`changed_when: true` is conservative — uv doesn't expose a clean
"no-op" exit signal we can match on. Acceptable cost.

**Caveat to verify during molecule run:** the existing
`Delete virtualenv` (line 25–31) runs only when
`django_recreate_virtual_env` is true; the existing
`Ensure required directories` (line 33–48) creates `django_venv_path` as
an empty dir owned by `django_system_user`. uv is fine with creating its
venv inside an empty existing dir, but molecule should confirm.

---

#### Task 13: Add `uv` molecule scenario

**Files:**

- Create: `molecule/uv/molecule.yml`
- Create: `molecule/uv/converge.yml`
- Create: `molecule/uv/prepare.yml` (if needed to seed a tiny pyproject)

**What:** Mirror the `default` scenario structure but converge against a
minimal Django app whose dependencies are managed by uv. Use a tiny
fixture project (committed under `tests/fixtures/sample-uv-project/`) with
a `pyproject.toml` declaring `django>=5,<6` plus a trivial `manage.py`,
so the molecule run actually exercises `uv sync` against a real lockfile.

The scenario sets:

```yaml
django_use_uv: true
django_use_regular_old_pip: false
django_git_url: ...                          # clone the fixture repo (or set up locally)
django_pip_packages: []                      # keep extras list empty for the test
```

Verify, via testinfra in the existing `tests/` directory, that:

- `/usr/local/bin/uv` exists and is executable.
- `{{ django_venv_path }}/bin/python` is a working Python.
- `{{ django_venv_path }}/bin/django-admin` exists (proving the lockfile
  install ran).

**Verify:** `molecule test -s uv` passes locally (in Docker).

---

#### Task 14: Document the new mode

**Files:**

- Modify: `README.md`

**What:** Add a short section "## uv (Astral) install mode" describing
the flag, the env vars uv reads, and the constraint that the consuming
project must have `pyproject.toml` + `uv.lock` checked in.

---

### Repo 2: `ansible-tally-ho` — opt in to `django_use_uv`

#### Task 15: Switch tally-ho's wiring to uv mode

**Files:**

- Modify: `meta/main.yml`
- Modify: `defaults/main.yml`
- Modify: `requirements.yml`

**Changes in `meta/main.yml` (under the `onaio.django` role vars):**

```diff
-      django_use_regular_old_pip: true
-      django_use_pipenv: false
+      django_use_uv: true
+      django_use_regular_old_pip: false
+      django_use_pipenv: false
       ...
-      django_pip_paths: "{{ tally_ho_requirements_paths }}"
+      # django_pip_paths intentionally unset — uv mode reads pyproject.toml + uv.lock
```

**Changes in `defaults/main.yml`:**

```diff
-tally_ho_requirements_paths:
-  - "{{ tally_ho_django_checkout_path }}/requirements/dev.pip"
-tally_ho_django_setuptools_version: "57.5.0"
+# Removed — uv mode does not need these.
```

Leave `tally_ho_django_pip_packages: [uwsgi, django-debug-toolbar]`
intact — the django role still installs these into the venv via its
mode-agnostic pip step. (Optionally drop `django-debug-toolbar` since it's
already in the app's `[dependency-groups] dev`, but stage runs with
`tally_ho_django_debug: True` and may want it; safer to leave for now.)

**Changes in `requirements.yml`:**

Pin the `ansible-django` role to a sha (or tag, once R1 cuts one) so
deploys are reproducible:

```diff
- src: git+https://github.com/onaio/ansible-django
  name: django
- version: master
+ version: <sha-of-the-merged-uv-mode-commit>
```

**Verify:** Bump the sha after R1 merges. Run a stage deploy end-to-end.

---

### Repo 3: `infrastructure` — bump the submodule

#### Task 16: Bump submodule + redeploy stage

**Files:**

- `ansible/roles/tally-ho/` (submodule pointer)

**What:**

```bash
cd ansible/roles/tally-ho
git fetch origin
git checkout <sha-of-Task-15-commit>
cd -
git add ansible/roles/tally-ho
git commit -m "Bump ansible-tally-ho: uv install mode"
```

No inventory changes needed — confirmed earlier sweep that no
`group_vars`/`host_vars` under `inventories/tally-ho/{stage,production}/`
override `tally_ho_requirements_paths`, `django_use_*`, or
`tally_ho_django_setuptools_version`.

**Verify:** Run `ansible-playbook -i inventories/tally-ho/stage tally_ho.yml`.
Watch for: uv install on host, `uv sync` in checkout, venv populated,
uwsgi/celery binaries present in venv, systemd services come up.

---

### Phase 2 pre-flight callouts

1. **Stage's `tally_ho_django_git_version` is `"django-upgrade"`** (a branch);
   prod's is `"v3.1.5"` (a tag). Whichever ref the stage deploy hits must
   already contain `pyproject.toml` + `uv.lock` (from the `uv-migration`
   merge). Either rebase `django-upgrade` onto current master, or push a
   fresh tag and point stage at it before running Task 16's verify step.
2. **`uwsgi`** still comes from `tally_ho_django_pip_packages`, not from
   project deps. The new `django_use_uv` mode in R1 must not break the
   existing extras-pip step. Tasks 12 + 13 explicitly preserve this.

## Out of scope

- Upgrading Django or other package versions beyond what's needed for
  compatibility — that's a separate effort.
- Changing the `odk-central-sync/` sub-project — it's already modern.
- `uwsgi.ini` — production server config, separate concern.
