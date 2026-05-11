-- Criação de roles e bancos adicionais
CREATE ROLE app_readonly WITH LOGIN PASSWORD 'readonly_pass';
GRANT CONNECT ON DATABASE app_database TO app_readonly;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO app_readonly;

-- Extensões comuns
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";