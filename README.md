[![Build Status](https://travis-ci.org/onaio/tally-ho.svg?branch=master)](https://travis-ci.org/onaio/tally-ho)

## Tally-Ho!
Election results data entry and verification software built by [Ona Systems](http://company.ona.io) and commissioned by the Libyan [High National Elections Commission](http://hnec.ly/) and the [United Nations Development Program](http://www.undp.org).

## Quick install

### Checkout the repos

```bash
git clone git@github.com:onaio/tally-system.git
git clone git@github.com:onaio/libya-data.git data
```

### Make a virtual environment and install requirements

Prerequisites: this assumes you have [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) and [PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides) installed.

```bash
mkvirtualenv tally --python=python3.6.5
pip install -r requirements/dev.pip 
```

### Quick start with demo data

> This will remove all data in the database.

> TODO: add some demo result forms and candidate lists

To load demo data and start the server all in one, run

```bash
./scripts/quickstart
```

If you've aleady loaded the data, you can start the server with

```bash
python manage.py runserver
```

### Advanced: recreate the database, then load the data and demo users

> This will remove all data in the database.

> This will only work if you have data files in the folder `./data`

The first argument is the database user, the second is the database host IP
address, and the third is the settings file.  Modify these arguments as needed.

```bash
./scripts/reload_all postgres 127.0.0.1 tally_ho.settings.common
```

## News

* This is an [article about tally-ho](http://blog.ona.io/general/2014/06/12/Tally-Ho-Robust-Open-Source-Election-Software.html) and its use in Libya.
* This presentation at PyConZA 2014 about the project, [Writing Python Code to Decide an Election](https://blog.ona.io/general/2016/02/12/writing-python-code-to-decide-an-election.html).

### Demo Users

The `create_demo_users` command will create demo users for each role with usernames like `super_administrator`, and password `data`.
