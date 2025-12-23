#!/bin/bash
set -e

# Copy pre-built static files to shared volume if volume is mounted
# Static files are collected at build time and baked into the image
# This allows Apache on the host to serve them
if [ -n "$STATIC_VOLUME_PATH" ]; then
    echo "Copying static files to shared volume at $STATIC_VOLUME_PATH..."

    # Create target directory if it doesn't exist
    mkdir -p "$STATIC_VOLUME_PATH"

    # Copy static files from image to the mounted volume
    # Static files were already collected during docker build
    if [ -d "/var/www/coldfront_app/coldfront/static_root" ]; then
        cp -rf /var/www/coldfront_app/coldfront/static_root/* "$STATIC_VOLUME_PATH/"
        echo "Static files copied successfully to $STATIC_VOLUME_PATH"
    else
        echo "WARNING: static_root directory not found in image!"
    fi
fi

# Execute the main container command
exec "$@"
