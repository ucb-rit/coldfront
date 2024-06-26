FROM coldfront-os

RUN dnf update -y && \
    dnf install -y gnupg wget

RUN dnf module install -y postgresql:15

WORKDIR /var/www/coldfront_app/coldfront

CMD ["sleep", "infinity"]
