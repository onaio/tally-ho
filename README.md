## Quick install

### Checkout the repos

```bash
git clone git@github.com:onaio/tally-system.git
git clone git@github.com:onaio/libya-data.git data
```

### Make a virutal environment and install requirements

```bash
mkvirtualenv tally --python=python2.7
pip install -r requirements/dev.pip 
```

### Load the data and demo users

```bash
./script/reload_all
python manage.py create_demo_users
```
