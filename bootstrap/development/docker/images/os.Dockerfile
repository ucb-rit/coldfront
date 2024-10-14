FROM rockylinux/rockylinux:8.8

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

RUN mkdir -p /usr/src/python310 && \
    cd /usr/src/python310 && \
    wget https://www.python.org/ftp/python/3.10.14/Python-3.10.14.tgz && \
    tar -xzvf Python-3.10.14.tgz && \
    cd Python-3.10.14 && \
    ./configure --enable-optimizations --enable-shared && \
    make && \
    make install

RUN rm -rf /usr/src/python310

RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/local.conf && \
    ldconfig

# Install libfaketime.
RUN git clone https://github.com/wolfcw/libfaketime.git /opt/libfaketime && \
    cd /opt/libfaketime && \
    make && \
    make install && \
    dnf clean all && \
    rm -rf /opt/libfaketime
