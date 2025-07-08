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
    .

docker buildx build \
    --target coldfront-app-base \
    --tag coldfront-app-base:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    .

docker buildx build \
    --target coldfront-app-config \
    --tag coldfront-app-config:$IMAGE_TAG \
    --cache-from=type=local,src=/tmp/.buildx-cache \
    .
