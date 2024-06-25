FROM ubuntu:latest

RUN apt update && \
    apt install -y python3 python3-dev python3-pip python3-venv && \
    apt install -y libfaketime && \
    # Necessary for mod-wsgi requirement
    apt install -y apache2-dev

WORKDIR /var/www/coldfront_app/coldfront

RUN python3 -m venv /var/www/coldfront_app/venv

COPY requirements.txt .
# Pin setuptools to avoid ImportError. Source: https://stackoverflow.com/a/78387663
RUN /var/www/coldfront_app/venv/bin/pip install --upgrade pip wheel && \
    /var/www/coldfront_app/venv/bin/pip install setuptools==68.2.2 && \
    /var/www/coldfront_app/venv/bin/pip install -r requirements.txt

ENV PATH="/var/www/coldfront_app/venv/bin:$PATH"
