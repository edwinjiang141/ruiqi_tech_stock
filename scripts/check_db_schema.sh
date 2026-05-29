#!/usr/bin/env bash
set -euo pipefail

PGPASSWORD="${PGPASSWORD:-ruiqi123}" psql \
  "postgresql://ruiqi@127.0.0.1:5432/ruiqi_stock" \
  -v ON_ERROR_STOP=1 \
  -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'stock_research_v12';" \
  -c "SELECT table_schema, COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema IN ('public', 'stock_research_v12') GROUP BY table_schema ORDER BY table_schema;"
