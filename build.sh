#!/usr/bin/env bash
# Wrapper for running Django manage.py commands inside the running
# docker-compose `web` container.
#
# Usage:
#   ./build.sh create_demo_tally --clean
#   ./build.sh create_demo_pvp_bundle --tally-id 3
#   ./build.sh migrate
exec docker-compose exec \
  -e DJANGO_SETTINGS_MODULE=tally_ho.settings.docker \
  web python manage.py "$@"
