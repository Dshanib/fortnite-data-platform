# Runbook (Phase 1)

## Startup order

1. Copy env: `cp .env.example .env` and fill secrets
2. Start infra: `docker compose up -d`
3. Init DuckDB: `python -m serving.duckdb_init`
4. Health checks:
   - `python scripts/check_minio.py`
   - `python scripts/check_kafka.py`
5. Run ingestion (requires Kafka + sources):
   - `python -m ingestion.ingest_ccu`
   - `python -m ingestion.ingest_shop`
   - `python -m ingestion.ingest_cosmetics`
6. Start bot: `python -m bot.app`

## MinIO profiles

**Internal (local)**

```bash
# merge from .env.internal.example into .env
MINIO_PROFILE=internal
MINIO_ENDPOINT=http://localhost:9000
```

**External (remote host)**

```bash
MINIO_PROFILE=external
MINIO_ENDPOINT=http://192.168.1.50:9000
```

Health URL is derived: `{MINIO_ENDPOINT}/minio/health/live`

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Kafka connection refused | `docker compose ps`; wait for healthy Kafka |
| MinIO health 404/connection | Verify `MINIO_ENDPOINT` scheme/host/port |
| Bot silent / errors | Confirm `TELEGRAM_BOT_TOKEN` in `.env` |
| Queries return no data | Run `serving.duckdb_init`; load tables via future pipelines |
| `python` permission denied | Activate `.venv` or use `py -3.14` |

## Memory

Aim for ≥4 GB free RAM before running Kafka + MinIO + bot together.
