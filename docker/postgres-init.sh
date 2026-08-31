#!/bin/bash
# Runs once on first Postgres boot. POSTGRES_USER (from env) is the schema OWNER
# used for migrations only. Here we add the RLS-constrained runtime app role.
# It gets NO DDL rights; table/sequence GRANTs are issued by the 0001 migration.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
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
