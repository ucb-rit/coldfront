#!/bin/bash

if [ "$DEBUGPY" = "1" ]; then
  exec python3 -m debugpy --listen 0.0.0.0:5678 --wait-for-client manage.py runserver 0.0.0.0:80
else
  exec python3 manage.py runserver 0.0.0.0:80
fi
