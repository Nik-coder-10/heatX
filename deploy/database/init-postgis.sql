-- =============================================================================
-- Urban Heat Mitigation Platform - PostGIS Initialization
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create application schema
CREATE SCHEMA IF NOT EXISTS urbanheat;

-- Set search path
ALTER DATABASE urbanheat SET search_path TO urbanheat, public, postgis;
