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

## Demo Site

### [tally.ona.io](http://tally.ona.io)

Ona intermittently hosts a demo site of the Libya tally software at [tally.ona.io](http://tally.ona.io).

The demo user name and password (formatted as username/password) is:

* `super_administrator`/`datadata`

If it is not running and you would like to see a demo, please [email us](mailto:info@ona.io).

### Demo Users

Please login as username `super_administrator`, password `datadata` to look around the demo site.
