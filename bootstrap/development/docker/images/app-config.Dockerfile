ARG BASE_IMAGE_TAG=latest
FROM coldfront-os:${BASE_IMAGE_TAG}

WORKDIR /app

RUN python3 -m venv /app/venv

RUN /app/venv/bin/pip install --upgrade pip setuptools wheel && \
    /app/venv/bin/pip install jinja2 pyyaml

ENV PATH="/app/venv/bin:$PATH"
