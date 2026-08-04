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

COPY requirements.txt requirements-test.txt ./

RUN python3 -m venv /var/www/coldfront_app/venv

RUN /var/www/coldfront_app/venv/bin/pip install --upgrade pip wheel && \
    /var/www/coldfront_app/venv/bin/pip install setuptools && \
    /var/www/coldfront_app/venv/bin/pip install -r requirements.txt -r requirements-test.txt

# Install Playwright Chromium browser and its OS-level dependencies.
# playwright install-deps does not support Rocky Linux (falls back to apt-get);
# the RHEL 8 equivalents are installed via dnf manually instead.
# pango + cairo: Chromium dynamically links to libpango for text layout/shaping;
# cairo is pango's rendering backend.
RUN dnf install -y \
    alsa-lib \
    at-spi2-atk \
    at-spi2-core \
    atk \
    cairo \
    cups-libs \
    dbus-libs \
    flac-libs \
    gdk-pixbuf2 \
    gtk3 \
    libdrm \
    libX11 \
    libxcb \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXfixes \
    libXi \
    libXrandr \
    libXrender \
    libXtst \
    libxshmfence \
    mesa-libgbm \
    nspr \
    nss \
    opus \
    pango \
    pulseaudio-libs \
    liberation-serif-fonts && \
    /var/www/coldfront_app/venv/bin/playwright install chromium

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
# Stage 4: db-postgres-shell
############################

FROM coldfront-app-base AS coldfront-db-postgres-shell

RUN dnf install -y gnupg

RUN dnf module install -y postgresql:15

WORKDIR /var/www/coldfront_app/coldfront
