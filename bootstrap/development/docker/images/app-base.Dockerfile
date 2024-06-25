FROM ubuntu:latest

RUN apt-get update && \
    apt-get install -y python3 python3-dev python3-pip && \
    apt-get install -y libfaketime && \
    # Necessary for mod-wsgi requirement
    apt-get install -y apache2-dev

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt --break-system-packages

WORKDIR /var/www/coldfront_app/coldfront
