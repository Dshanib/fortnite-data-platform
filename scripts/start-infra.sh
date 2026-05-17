#!/usr/bin/env bash
# Start Kafka, Zookeeper, and MinIO via Docker Compose from repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose --env-file .env up -d
docker compose ps
