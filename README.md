## Quick install

### Checkout the repos

```bash
git clone git@github.com:onaio/tally-system.git
git clone git@github.com:onaio/libya-data.git data
```

### Make a virutal environment and install requirements

Prerequisites: this assumes you have [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) and [PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides) installed.

```bash
mkvirtualenv tally --python=python2.7
pip install -r requirements/dev.pip 
```

### Recreate the database, then load the data and demo users

Change the user argument `postgres` if that is not a user able to drop and create databases.

```bash
./script/reload_all postgres libya_tally.settings.common
```
