# Tally-Ho

![Build Status](https://github.com/onaio/tally-ho/actions/workflows/config.yml/badge.svg?branch=master)
[![codecov](https://codecov.io/github/onaio/tally-ho/branch/master/graph/badge.svg?token=1PR3KIqgr6)](https://codecov.io/github/onaio/tally-ho)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/1e817ebba18946fa84cb129cdc914f0b)](https://app.codacy.com/gh/onaio/tally-ho/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

## Overview

Election results data entry and verification software built by [Ona Systems](http://company.ona.io), commissioned by the Libyan [High National Elections Commission](http://hnec.ly/) and [UNDP](http://www.undp.org).

## Quick Install

### Checkout the Repository

```bash
git clone git@github.com:onaio/tally-ho.git
```

### Set Up Virtual Environment and Install Requirements

Prerequisites: Ensure [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) and [PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides) are installed.

```bash
mkvirtualenv tally --python=python3.9
pip install -r requirements/dev.pip
```

Install `libpq-dev` for PostgreSQL headers:

```bash
sudo apt-get install libpq-dev
```

Install memcached and Redis:

```bash
sudo apt-get update && sudo apt-get install -y memcached redis-server
```

Ensure latest versions of pip, wheel, and setuptools:

```bash
python -m pip install -U pip wheel setuptools
```

Enable [pre-commit hook checks](https://pre-commit.com/#3-install-the-git-hook-scripts):

```bash
pre-commit install
```

### Running Celery

```bash
celery -A tally_ho.celeryapp worker --loglevel=info
```

### Quick Start with User Demo Data

> **Warning**: This will erase all database data.

```bash
./scripts/quick_start
```

If server setup is complete, start the server:

```bash
python manage.py runserver --settings=tally_ho.settings.dev
```

### Loading Tally Demo Data

> **Note**: Add demo result forms and candidate lists.

### Advanced: Recreate Database and Load Demo Users

> **Warning**: This erases all database data and only works with files in `./data`.

```bash
./scripts/reload_all postgres 127.0.0.1 tally_ho.settings.common
```

## Docker Installation

With Docker and `docker-compose` installed, build and run:

```bash
docker-compose build
docker-compose up
```

Visit `127.0.0.1:8000`. For production, modify the `docker-compose.yml` file:

1. Change NGINX port from 8000 to 80.
2. Add your host to `ALLOWED_HOSTS` in `tally_ho/settings/docker.py`.

## Running Tests

Run tests with:

```bash
pytest tally_ho
```

## Documentation

### Arabic Translations

Follow these steps for managing Arabic translations:

1. **Add Arabic Language**: Update `settings.py`:

    ```python
    # settings.py
        LANGUAGES = [
            ('en', 'English'),
            ('ar', 'Arabic'),
    ]

    # Ensure LANGUAGE_CODE is set to a default language (e.g., 'en')
        LANGUAGE_CODE = 'en'
    ```

2. **Generate Arabic Translation Files**:

    ```bash
    django-admin makemessages -l ar
    ```

3. **Edit Arabic Translations**: Update `locale/ar/LC_MESSAGES/django.po`.

4. **Compile Translations**:

    ```bash
    django-admin compilemessages
    ```

### Generating Model Graphs

Install requirements from `requirements/dev.pip` and [graphviz](https://graphviz.org/download/).

Generate all model graphs:

```bash
python manage.py graph_models --settings=tally_ho.settings.dev --pydot -a -g -o tally-ho-all-models.png
```

Generate specific app model graphs:

```bash
python manage.py graph_models --settings=tally_ho.settings.dev --pydot -a -X GroupObjectPermission,... -g -o tally-ho-app-models.png
```

### Demo Users

Use the `create_demo_users` command to create demo users with usernames like `super_administrator`, and password `data`.

### File Uploads

File upload limit is set to 10MB in `MAX_FILE_UPLOAD_SIZE` within `tally_ho/settings/common.py`.

## News

- Article: [Writing Python Code to Decide an Election](https://ona.io/home/writing-python-code-to-decide-an-election-2/).
- PyConZA 2014 presentation: [Writing Python Code to Decide an Election](https://ona.io/home/writing-python-code-to-decide-an-election-2/).
