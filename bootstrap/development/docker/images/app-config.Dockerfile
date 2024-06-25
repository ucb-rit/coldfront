FROM ubuntu:latest

RUN apt update && \
    apt install -y python3 python3-dev python3-pip python3-venv

WORKDIR /app

RUN python3 -m venv /app/venv

RUN /app/venv/bin/pip install --upgrade pip setuptools wheel && \
    /app/venv/bin/pip install jinja2 pyyaml

ENV PATH="/app/venv/bin:$PATH"
