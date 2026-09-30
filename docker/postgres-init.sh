#!/bin/bash
# Provision the two-tier database (compose no longer runs PG).
# Dokploy-managed Postgres: it already created the DB + user (= schema owner, use it as
# POSTGRES_USER/POSTGRES_DB and in DATABASE_URL_OWNER). Skip the bootstrap below and just
# run this script once from the DB's Dokploy terminal / a psql session (PGHOST=<pg-app-name>).
#
# One-time bootstrap as a Postgres superuser (creates the DB + schema-owner role):
#
#   sudo -u postgres psql <<SQL
#     CREATE ROLE nobojatra_owner LOGIN PASSWORD 'owner-pw';
#     CREATE DATABASE nobojatra OWNER nobojatra_owner;
#   SQL
#
# Then run this script to add the RLS-constrained runtime role:
#
#   set -a; . ./.env; set +a
#   PGPASSWORD="$POSTGRES_PASSWORD" ./docker/postgres-init.sh
#
# The app role gets NO DDL rights; table/sequence GRANTs come from migration 0001.
set -e

: "${PGHOST:=localhost}"

psql -v ON_ERROR_STOP=1 --host "$PGHOST" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
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
