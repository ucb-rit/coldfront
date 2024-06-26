FROM coldfront-os

RUN dnf update -y && \
    dnf install -y gnupg wget

RUN dnf install -y postgresql

WORKDIR /var/www/coldfront_app/coldfront

CMD ["sleep", "infinity"]
