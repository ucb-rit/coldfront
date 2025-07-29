#!/bin/bash

if [ -z "$1" ]; then
  IMAGE_TAG="latest"
else
  IMAGE_TAG="$1"
fi

docker buildx use default

docker buildx build \
    --target coldfront-os \
    --tag coldfront-os:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    --load \
    .

docker buildx build \
    --target coldfront-app-base \
    --tag coldfront-app-base:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    --load \
    .

docker buildx build \
    --target coldfront-app-config \
    --tag coldfront-app-config:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    --load \
    .

docker buildx build \
    --target coldfront-db-postgres-shell \
    --tag coldfront-db-postgres-shell:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    --load \
    .

docker buildx build \
    --target coldfront-email-server \
    --tag coldfront-email-server:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    --load \
    .
