#!/usr/bin/env bash
# Start core infra + Airflow (build image if needed).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env — copy from .env.example and set AIRFLOW_FERNET_KEY"
  exit 1
fi

if ! grep -q '^AIRFLOW_FERNET_KEY=.\+' .env 2>/dev/null; then
  echo "Set AIRFLOW_FERNET_KEY in .env before starting Airflow"
  exit 1
fi

echo "Starting core services (zookeeper, kafka, minio)..."
docker compose --env-file .env up -d zookeeper kafka minio

echo "Building / starting Airflow (postgres:13, init, webserver, scheduler)..."
docker compose --env-file .env --profile airflow up -d --build \
  airflow-postgres airflow-init airflow-webserver airflow-scheduler

echo ""
echo "Airflow UI: http://localhost:8080"
echo "Login: admin / admin (or values from _AIRFLOW_WWW_USER_* in .env)"
echo "Wait ~60s for webserver health, then unpause DAGs in the UI."
