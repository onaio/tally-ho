#!/bin/bash

PROJECT_HOME=/var/www
PROJECT_NAME="tally-system"
DJANGO_SETTINGS_MODULE="libya_tally.settings.local_settings"
CODE_SRC="$PROJECT_HOME/tally-system"
VENV="$PROJECT_HOME/.virtualenvs"
DB_NAME=tally
DB_USER=tally
DB_PASS=tally
DB_HOST=127.0.0.1
GIT="true"
USER=ubuntu

sudo useradd $USER

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ precise-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
sudo wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install nginx git python-setuptools python-dev binutils libproj-dev Postgresql-9.3-postgis libpq-dev
sudo easy_install pip
sudo pip install virtualenvwrapper uwsgi

sudo -u postgres psql -U postgres -d postgres -c "CREATE USER $DB_USER with password '$DB_PASS';"
sudo -u postgres psql -U postgres -d postgres -c "CREATE DATABASE $DB_USER OWNER $DB_USER;"

sudo mkdir -p $PROJECT_HOME
sudo chown -R $USER $PROJECT_HOME

if [ GIT ]; then
    cd $PROJECT_HOME && (git clone git@github.com:onaio/tally-system.git || (cd tally-system && git fetch))
else
    cd $PROJECT_HOME && cp -R ~/libya-tally .
fi

config_path_tmp="$CODE_SRC/deploy/var/www/tally-system/libya_tally/settings/local_settings.py"
config_path="$CODE_SRC/libya_tally/settings/local_settings.py"
cp $config_path_tmp $config_path
sed -i.bak -e "s/REPLACE_DB_NAME/$DB_NAME/g" $config_path
sed -i.bak -e "s/REPLACE_DB_USER/$DB_USER/g" $config_path
sed -i.bak -e "s/REPLACE_DB_PASSWORD/$DB_PASS/g" $config_path
sed -i.bak -e "s/REPLACE_DB_HOST/$DB_HOST/g" $config_path

sudo cp "$CODE_SRC/deploy/etc/init/tally.conf" /etc/init/tally.conf
sudo cp "$CODE_SRC/deploy/etc/nginx/sites-available/nginx.conf" /etc/nginx/sites-available/tally.conf
sudo unlink /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/tally.conf /etc/nginx/sites-enabled/tally

WORKON_HOME=$VENV source /usr/local/bin/virtualenvwrapper.sh && WORKON_HOME=$VENV mkvirtualenv $PROJECT_NAME
echo "export WORKON_HOME=$VENV" >> ~/.bashrc
echo "export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE" >> ~/.bashrc

cd $CODE_SRC && source $activate && pip install -r requirements/common.pip
cd $CODE_SRC && source $activate && python manage.py syncdb --noinput --settings=$DJANGO_SETTINGS_MODULE
cd $CODE_SRC && source $activate && python manage.py migrate --settings=$DJANGO_SETTINGS_MODULE
cd $CODE_SRC && source $activate && python manage.py collectstatic --noinput --settings=$DJANGO_SETTINGS_MODULE
sudo /etc/init.d/nginx restart
sudo mkdir -p /var/log/uwsgi
sudo chown -R $USER /var/log/uwsgi
sudo start tally
