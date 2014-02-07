FROM ubuntu
MAINTAINER Ukang'a Dickson

ADD ./deploy/context /tmp/context

ENV CODENAME precise

RUN echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $CODENAME-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN cp /tmp/context/apt.postgresql.org.gpg /apt.postgresql.org.gpg
ENV KEYRING /etc/apt/trusted.gpg.d/apt.postgresql.org.gpg
RUN test -e $KEYRING || touch $KEYRING
RUN apt-key --keyring $KEYRING add /apt.postgresql.org.gpg
RUN apt-get update -yq

ENV LANGUAGE en_US.UTF-8 ENV LANG en_US.UTF-8 ENV LC_ALL en_US.UTF-8
RUN locale-gen en_US.UTF.8
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get install -yq  python-dev python-setuptools python-distribute \
    python-pip libxml2-dev libxslt-dev make g++ libreadline-dev \
    libncurses5-dev libpcre3-dev  libpq-dev libpcre3-dev git-core nginx \
    postgresql-9.3 postgresql-contrib-9.3 Postgresql-9.3-postgis postgis \
    sed vim-nox supervisor

RUN pip install virtualenv uwsgi

VOLUME ["/var/lib/postgres/data", "/var/www/tally-system"]

ENV DB_NAME tally
ENV DB_USERNAME tally
ENV DB_PASS tally
ENV DB_HOST 127.0.0.1
ENV DATADIR /var/lib/postgres/data

ENV APP_DIR /var/www/tally-system
ENV VENV /var/www/.virtualenvs/tally-system
ENV ACTIVATE /var/www/.virtualenvs/tally-system/bin/activate
ENV DJANGO_SETTINGS_MODULE libya_tally.settings.local_settings

ENV PIP_DOWNLOAD_CACHE /pip_download_cache
RUN mkdir -p $PIP_DOWNLOAD_CACHE
RUN virtualenv $VENV

RUN mkdir -p $APP_DIR
ADD . $APP_DIR

RUN mkdir -p /data/postgres
RUN cp /tmp/context/var/lib/postgres/data/pg_hba.conf /data/postgres/pg_hba.conf
RUN cp /tmp/context/var/lib/postgres/data/postgresql.conf /data/postgres/postgresql.conf
RUN rm -rf /var/lib/postgresql/9.3/main
RUN ln -s $DATADIR /var/lib/postgresql/9.3/main

RUN rm /etc/nginx/nginx.conf
RUN cp /tmp/context/etc/nginx/nginx.conf /etc/nginx/

RUN mkdir -p /var/log/uwsgi && mkdir -p /var/log/tally-system/
RUN (cd $APP_DIR && pip install -r requirements/common.pip)

RUN cp /tmp/context/start /start
RUN chmod 0755 /start

# Cleanup
RUN apt-get clean

EXPOSE 5432
EXPOSE 80
EXPOSE 8000

CMD ["/start"]
