#!/bin/bash

DUMP_FILE_PATH=$1

# Terminate connections to the application database.
PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") psql \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid() AND datname = '$POSTGRES_DB';" \
    postgres

# Drop the database. This cannot be done within a transaction, so it must be run
# independently.
PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") psql \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -c "DROP DATABASE $POSTGRES_DB;" \
    postgres

# Create the database. This cannot be done within a transaction, so it must be
# run independently.
PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") psql \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -c "CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;" \
    postgres

# Create a postgres user and grant it superuser privileges.
PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") psql \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -c "CREATE USER postgres;
        ALTER USER postgres WITH SUPERUSER;" \
    postgres

# Restore the database from a dump file.
PGPASSWORD=$(cat "$POSTGRES_PASSWORD_FILE") pg_restore \
    -h $POSTGRES_HOST \
    -U $POSTGRES_USER \
    -d $POSTGRES_DB $DUMP_FILE_PATH
