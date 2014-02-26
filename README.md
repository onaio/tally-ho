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

*This will remove all data in the database.*

The first argument is the database user, the second is the database host IP
address, and the third is the settings file.  Modify these arguments as needed.

```bash
./script/reload_all postgres 127.0.0.1 libya_tally.settings.common
```
