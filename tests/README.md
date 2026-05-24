# Tests

## Layout

| Path | Purpose |
|------|---------|
| `conftest.py` | Shared fixtures and test env defaults |
| `unit/` | Fast offline unit tests (default `pytest` run) |
| `unit/bot/` | Telegram bot routing, formatters, single-instance lock |
| `unit/config/` | Settings loading |
| `unit/common/` | Validators and shared helpers |
| `unit/ingestion/` | API clients, envelopes, chunking, island catalog |
| `unit/serving/` | DuckDB paths, query service |
| `unit/storage/` | MinIO paths, Kafka producer config |
| `unit/streaming/` | Bronze→Silver→Gold transformations |
| `unit/orchestration/` | Airflow DAG structure |
| `integration/` | Live API connectivity (network required) |

Operational scripts stay under `scripts/` (`check_*.py`, `run_*.py`). They are not pytest tests.

## Commands

```bash
# Unit tests only (default)
pytest

# Explicit unit tree
pytest tests/unit

# Live API checks (needs .env + network)
pytest tests/integration -m integration

# Same checks via scripts (used in runbook)
python scripts/check_fortnite_api.py
python scripts/check_fortnite_ecosystem.py
```
