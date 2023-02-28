#!/bin/sh

# This script clears out the PostgreSQL database with the given name and
# loads in the data from the given dump file generated by pg_dump. It
# skips loading entries from the Job table.

# Store second last and last arguments.
DB_NAME=${@:(-2):1}
DB_OWNER=admin
DUMP_FILE=${@: -1}

BIN=/usr/pgsql-15/bin/pg_restore

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] ; then
    echo "Usage: `basename $0` [OPTION] name-of-database absolute-path-to-dump-file"
    echo $'  -k, --kill-connections\t\tterminates all connections to the database so it can be dropped'
    exit 0
elif ! [[ "$DUMP_FILE" = /* ]] ; then
    echo "Path to database dump file must be absolute."
    exit 1
elif ! [[ -f "$DUMP_FILE" ]] ; then
    echo "Database dump file must be a file."
    exit 1
fi

if [[ "$1" == "-k" || "$1" == "--kill-connections" ]] ; then
  echo "TERMINATING DATABASE CONNECTIONS..."
  sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) 
    FROM pg_stat_activity 
    WHERE pid <> pg_backend_pid() AND datname = '$DB_NAME';"
fi

sudo -u postgres /bin/bash -c "echo DROPPING DATABASE... \
                    && psql -c 'DROP DATABASE $DB_NAME;'; \
                    \
                    echo RECREATING DATABASE... \
                    && psql -c 'CREATE DATABASE $DB_NAME OWNER $DB_OWNER;' \
                    \
                    && echo LOADING DATABASE... \
                    && $BIN -d $DB_NAME $DUMP_FILE; \
                    psql -c 'ALTER SCHEMA public OWNER TO $DB_OWNER;' $DB_NAME;"
