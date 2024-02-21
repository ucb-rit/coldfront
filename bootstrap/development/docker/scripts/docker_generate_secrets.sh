#!/bin/bash

os=$(uname -o)

if [ "$os" = "Msys" ]; then
    wd=$(pwd | sed 's/^../\U&:/')
else
    wd=$PWD
fi

docker run -it \
    -v $wd/bootstrap/development/docker:/app \
    coldfront-app-config:latest \
    python3 scripts/generate_secrets.py

