FROM ubuntu:latest

RUN apt update && \
    apt install -y gnupg lsb-release wget

RUN sh -c 'echo "deb https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list' && \
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    apt update && \
    apt -y install postgresql-client-15

WORKDIR /var/www/coldfront_app/coldfront

CMD ["sleep", "infinity"]
