FROM coldfront-os

RUN dnf update -y && \
    dnf install -y gnupg wget

RUN dnf install -y postgresql

CMD ["sleep", "infinity"]
