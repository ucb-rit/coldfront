FROM ubuntu:focal

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt update && \
    apt -y install python3.8 && \
    apt-get install -y python3.8-dev python3-pip && \
    # Necessary for mod-wsgi requirement
    apt-get install -y apache2-dev

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

WORKDIR /var/www/coldfront_app/coldfront
