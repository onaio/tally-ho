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
mkvirtualenv tally --python=python2.7
pip install -r requirements/dev.pip 
```

### Recreate the database, then load the data and demo users

*This will remove all data in the database.*

The first argument is the database user, the second is the database host IP
address, and the third is the settings file.  Modify these arguments as needed.

```bash
./scripts/reload_all postgres 127.0.0.1 tally_ho.settings.common
```

## News

This is an [article about tally-ho](http://blog.ona.io/general/2014/06/12/Tally-Ho-Robust-Open-Source-Election-Software.html) and its use in Libya.

### Demo Users

The `create_demo_users` command will create demo users for each role with usernames like `super_administrator`, and password `data`.
