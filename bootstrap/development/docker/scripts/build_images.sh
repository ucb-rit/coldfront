#!/bin/bash

if [ -z "$1" ]; then
  IMAGE_TAG="latest"
else
  IMAGE_TAG="$1"
fi

docker build \
    -f bootstrap/development/docker/images/os.Dockerfile \
    -t coldfront-os:$IMAGE_TAG .

docker build \
    -f bootstrap/development/docker/images/app-config.Dockerfile \
    --build-arg BASE_IMAGE_TAG=$IMAGE_TAG \
    -t coldfront-app-config:$IMAGE_TAG bootstrap/development/docker

docker build \
    -f bootstrap/development/docker/images/app-base.Dockerfile \
    --build-arg BASE_IMAGE_TAG=$IMAGE_TAG \
    -t coldfront-app-base:$IMAGE_TAG .

docker build \
    -f bootstrap/development/docker/images/db-postgres-shell.Dockerfile \
    --build-arg BASE_IMAGE_TAG=$IMAGE_TAG \
    -t coldfront-db-postgres-shell:$IMAGE_TAG .
