#!/bin/bash

os=$(uname -o)
# On Git Bash, convert "/c/Users/..." to "/C:/Users/..." 
if [ "$os" = "Msys" ]; then
    wd=$(pwd | sed 's/^../\U&:/')
else
    wd=$PWD
fi

# Do not mount directly onto /app, since the venv is located there and would be
# wiped out.
docker run -it \
    -v $wd/bootstrap/development/docker/config:/app/config \
    -v $wd/bootstrap/development/docker/scripts:/app/scripts \
    -v $wd/bootstrap/development/docker/secrets:/app/secrets \
    coldfront-app-config:latest \
    python3 scripts/generate_secrets.py
