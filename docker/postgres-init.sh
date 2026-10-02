#!/bin/bash
# Provision the RLS runtime role. Mounted into the compose postgres container as an
# initdb script (runs once on an empty volume, over the unix socket, as POSTGRES_USER).
# Also runnable by hand against any Postgres: set PGHOST (and PGPASSWORD) plus the env vars
# below. The app role gets NO DDL rights; table/sequence GRANTs come from migration 0001.
set -e

psql -v ON_ERROR_STOP=1 ${PGHOST:+--host "$PGHOST"} --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${APP_DB_USER}') THEN
            CREATE ROLE ${APP_DB_USER} LOGIN PASSWORD '${APP_DB_PASSWORD}';
        END IF;
    END
    \$\$;
    -- can connect + resolve names, nothing more until the migration grants DML
    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_DB_USER};
    REVOKE ALL ON SCHEMA public FROM ${APP_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${APP_DB_USER};
SQL
