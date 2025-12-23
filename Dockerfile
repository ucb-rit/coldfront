############################
# Stage 1: os
############################

FROM rockylinux/rockylinux:8.10 AS coldfront-os

RUN dnf update -y && \
    dnf install -y \
    gcc \
    git \
    make \
    wget \
    openssl-devel \
    bzip2-devel \
    httpd-devel \
    libffi-devel \
    zlib-devel \
    readline-devel \
    redhat-rpm-config \
    sqlite-devel

RUN mkdir -p /usr/src/python313 && \
    cd /usr/src/python313 && \
    wget https://www.python.org/ftp/python/3.13.5/Python-3.13.5.tgz && \
    tar -xzvf Python-3.13.5.tgz && \
    cd Python-3.13.5 && \
    ./configure --enable-optimizations --enable-shared && \
    make && \
    make install

RUN rm -rf /usr/src/python313

RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && \
    ldconfig

# Install libfaketime.
RUN git clone https://github.com/wolfcw/libfaketime.git /opt/libfaketime && \
    cd /opt/libfaketime && \
    make && \
    make install && \
    dnf clean all && \
    rm -rf /opt/libfaketime

############################
# Stage 2: app-base
############################

FROM coldfront-os AS coldfront-app-base

WORKDIR /var/www/coldfront_app/coldfront

COPY requirements.txt .

RUN python3 -m venv /var/www/coldfront_app/venv

RUN /var/www/coldfront_app/venv/bin/pip install --upgrade pip wheel && \
    /var/www/coldfront_app/venv/bin/pip install setuptools && \
    /var/www/coldfront_app/venv/bin/pip install -r requirements.txt

ENV PATH="/var/www/coldfront_app/venv/bin:$PATH"

############################
# Stage 3: app-config
############################

FROM coldfront-os AS coldfront-app-config

RUN python3 -m venv /app/venv

RUN /app/venv/bin/pip install --upgrade pip setuptools wheel && \
    /app/venv/bin/pip install jinja2 pyyaml

ENV PATH="/app/venv/bin:$PATH"

############################
# Stage 4: app-production
############################

FROM coldfront-app-base AS coldfront-app-production

# Install system dependencies for health checks
RUN dnf install -y curl && dnf clean all

# Copy application code
COPY . /var/www/coldfront_app/coldfront

# Copy config files from samples if they don't exist
RUN cd /var/www/coldfront_app/coldfront/coldfront/config && \
    cp -n local_settings.py.sample local_settings.py && \
    cp -n local_strings.py.sample local_strings.py

# Collect static files at build time
# Use build_settings.py (via local_settings.py fallback chain)
ENV DJANGO_SETTINGS_MODULE=coldfront.config.settings \
    DJANGO__USE_ENV_SETTINGS=false

RUN python manage.py collectstatic --noinput --clear

# Copy entrypoint script and set permissions (must be executable by nobody user)
COPY bootstrap/production/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

# Set proper permissions for application directory
RUN chown -R nobody:nobody /var/www/coldfront_app

# Switch to non-root user
USER nobody

# Use entrypoint to copy static files to shared volume at startup
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

WORKDIR /var/www/coldfront_app/coldfront

# Add health check (checks every 30s, timeout 10s, 3 retries, 40s start period)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Expose port
EXPOSE 8000

# No default CMD - commands are specified in docker-compose.yml

############################
# Stage 5: db-postgres-shell
############################

FROM coldfront-app-base AS coldfront-db-postgres-shell

RUN dnf install -y gnupg

RUN dnf module install -y postgresql:15

WORKDIR /var/www/coldfront_app/coldfront
