#!/bin/bash

DEPLOYMENT=$1
if [ "$DEPLOYMENT" != "BRC" ] && [ "$DEPLOYMENT" != "LRC" ]; then
    echo "Invalid deployment. Please specify either 'BRC' or 'LRC'."
    exit 1
fi

WEB_PORT=$2

os=$(uname -o)
# On Git Bash, convert "/c/Users/..." to "/C:/Users/..."
if [ "$os" = "Msys" ]; then
    wd=$(pwd | sed 's/^../\U&:/')
else
    wd=$PWD
fi

# Re-copy local settings and strings.
cp coldfront/config/local_settings.py.sample coldfront/config/local_settings.py
cp coldfront/config/local_strings.py.sample coldfront/config/local_strings.py

# Re-copy the base main.yml file.
cp bootstrap/ansible/main.copyme bootstrap/development/docker/config/main.yml

# Re-generate the .env file for development.
# Do not mount directly onto /app, since the venv is located there and would be
# wiped out.
(docker run -it \
    -v $wd/bootstrap/ansible/.env.tmpl:/tmp/.env.tmpl \
    -v $wd/bootstrap/development/docker/config:/app/config \
    -v $wd/bootstrap/development/docker/scripts:/app/scripts \
    -w /app/scripts \
    coldfront-app-config:latest \
    python3 generate_django_env_file.py $DEPLOYMENT $WEB_PORT) 2>/dev/null > coldfront/config/.env
