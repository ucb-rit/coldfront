FROM coldfront-os

WORKDIR /var/www/coldfront_app/coldfront

RUN python3 -m venv /var/www/coldfront_app/venv

COPY requirements.txt .
# Pin setuptools to avoid ImportError. Source: https://stackoverflow.com/a/78387663
RUN /var/www/coldfront_app/venv/bin/pip install --upgrade pip wheel && \
    /var/www/coldfront_app/venv/bin/pip install setuptools==68.2.2 && \
    /var/www/coldfront_app/venv/bin/pip install -r requirements.txt

ENV PATH="/var/www/coldfront_app/venv/bin:$PATH"
