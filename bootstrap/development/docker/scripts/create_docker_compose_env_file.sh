#!/bin/bash

ENV_FILE_PATH=bootstrap/development/docker/.env

DEPLOYMENT=$1
if [ "$DEPLOYMENT" != "BRC" ] && [ "$DEPLOYMENT" != "LRC" ]; then
    echo "Invalid deployment. Please specify either 'BRC' or 'LRC'."
    exit 1
fi

PORT=$2
VALID_PORTS=("8880" "8881" "8882" "8883")
if [[ -z "$PORT" || ! " ${VALID_PORTS[@]} " =~ " ${PORT} " ]]; then
    valid_ports_string=$(IFS=,; echo "${VALID_PORTS[*]}")
    echo "Invalid port. Please specify one of the following: $valid_ports_string."
    exit 1
fi

if [ "$DEPLOYMENT" = "BRC" ]; then
    DB_NAME="cf_brc_db"
else
    DB_NAME="cf_lrc_db"
fi

USE_ENV_SETTINGS_INPUT=${3:-true}
USE_ENV_SETTINGS_INPUT=$(printf '%s' "$USE_ENV_SETTINGS_INPUT" | tr '[:upper:]' '[:lower:]')
if [[ "$USE_ENV_SETTINGS_INPUT" == "true" || "$USE_ENV_SETTINGS_INPUT" == "1" || "$USE_ENV_SETTINGS_INPUT" == "yes" ]]; then
    USE_ENV_SETTINGS=true
else
    USE_ENV_SETTINGS=false
fi

echo "DB_NAME=$DB_NAME" > $ENV_FILE_PATH
echo "WEB_PORT=$PORT" >> $ENV_FILE_PATH
echo "USE_ENV_SETTINGS=$USE_ENV_SETTINGS" >> $ENV_FILE_PATH
