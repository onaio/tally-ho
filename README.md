[![Build Status](https://travis-ci.org/onaio/tally-ho.svg?branch=master)](https://travis-ci.org/onaio/tally-ho)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/d610ecc632d340ff822c577054fdff38)](https://app.codacy.com/gh/onaio/tally-ho)
[![Coverage Status](https://coveralls.io/repos/github/onaio/tally-ho/badge.svg?branch=master)](https://coveralls.io/github/onaio/tally-ho?branch=master)

## Tally-Ho!

Election results data entry and verification software built by [Ona Systems](http://company.ona.io) and commissioned by the Libyan [High National Elections Commission](http://hnec.ly/) and the [United Nations Development Program](http://www.undp.org).

## Quick install

### Checkout the repos

```bash
git clone git@github.com:onaio/tally-ho.git
```

### Make a virtual environment and install requirements

Prerequisites: this assumes you have [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) and [PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides) installed.

```bash
mkvirtualenv tally --python=python3.6.5
pip install -r requirements/dev.pip
```

### Quick start with user demo data

> This will remove all data in the database.

To create the database, load demo users, and start the server all in one, run

```bash
./scripts/quickstart
```

If you've aleady setup the server, you can start the server with

```bash
python manage.py runserver --settings=tally_ho.settings.dev
```

### Loading tally demo data

> TODO: add some demo result forms and candidate lists

### Advanced: recreate the database, then load the data and demo users

> This will remove all data in the database.

> This will only work if you have data files in the folder `./data`

The first argument is the database user, the second is the database host IP
address, and the third is the settings file. Modify these arguments as needed.

```bash
./scripts/reload_all postgres 127.0.0.1 tally_ho.settings.common
```

## Docker Install

If you already have Docker and `docker-compose` installed on your machine you can quickly have a demo up by changing into the checked out code directory and running:

```bash
docker-compose build
docker-compose up
```

You can now visit the site at `127.0.0.1:8000`.

If you want to use Docker to run the site in production you will need to:

1. modify the `docker-compose.yml` file to change the NGINX listening port from 8000 to 80,
2. add the host you are running the site on to a new `ALLOWED_HOSTS` list in the `tally_ho/settings/docker.py` file.

## Running Tests

Pass the `-s` option if you want to use `ipdb.set_trace()` to debug during a test.

## Documentation

### Generating Model Graphs

The below assumes you have `pip` installed `requirements/dev.pip`.

Generate model graph for all models:

```
python manage.py graph_models --settings=tally_ho.settings.dev --pydot -a -g -o tally-ho-all-models.png
```

Generate model graph for app models:

```
python manage.py graph_models --settings=tally_ho.settings.dev --pydot -a -X GroupObjectPermission,UserObjectPermission,GroupObjectPermissionBase,BaseGenericObjectPermission,UserObjectPermissionBase,BaseObjectPermission,Version,Revision,Pageview,Visitor,Session,AbstractBaseSession,Site,LogEntry,User,Group,AbstractUser,Permission,ContentType,AbstractBaseUser,PermissionsMixin,BaseModel -g -o tally-ho-app-models.png
```

### Demo Users

The `create_demo_users` command will create demo users for each role with usernames like `super_administrator`, and password `data`.

### File Uploads

The `MAX_FILE_UPLOAD_SIZE` variable in `tally_ho/settings/common.py` file defines the file upload limit which is currently set to 10MB.

## News

- This is an [article about tally-ho](https://ona.io/home/writing-python-code-to-decide-an-election-2/) and its use in Libya.
- This presentation at PyConZA 2014 about the project, [Writing Python Code to Decide an Election](https://ona.io/home/writing-python-code-to-decide-an-election-2/).
