# Fortnite Cloud DE — Phase 1

Modular data engineering foundation: ingestion, Kafka, MinIO storage, DuckDB serving, and Telegram bot.

## Scope (Phase 1)

**Included:** ingestion, Kafka producer, MinIO abstraction, DuckDB serving, Telegram bot, validation, config, Docker Compose, tests, docs.

**Excluded:** PySpark, NLP-to-SQL, dashboards, Airflow, production cloud deployment.

## Architecture

```
Fortnite API / scrape → ingestion → Kafka → (future) → MinIO bronze
                                                    ↘ DuckDB → bot
```

See [docs/architecture.md](docs/architecture.md) and [docs/runbook.md](docs/runbook.md).

## Prerequisites

- Python 3.14+ (`py -3.14`)
- Docker Desktop
- Git

## Setup

```bash
cd d.e_proj
py -3.14 -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your `TELEGRAM_BOT_TOKEN` and MinIO settings.

### MinIO: internal vs external

| Profile | Use case | Example file |
|---------|----------|----------------|
| `internal` | Local Docker MinIO | [.env.internal.example](.env.internal.example) |
| `external` | Remote MinIO on LAN | [.env.external.example](.env.external.example) |

Copy the relevant MinIO block into `.env`. No localhost assumptions are hardcoded in code.

## Docker (MinIO + Kafka)

All local infrastructure runs via Docker Compose — **do not run a separate MinIO install** for this project.

```bash
# Stop any old standalone MinIO container using ports 9000/9001 if present
docker compose up -d
```

| Service | URL |
|---------|-----|
| MinIO S3 API | `http://localhost:9000` |
| MinIO Console | `http://localhost:9001` (user/pass: `minioadmin`) |
| Kafka | `localhost:9092` |

`minio-init` creates the `fortnite-data` bucket automatically. Set `MINIO_ENDPOINT=http://localhost:9000` in `.env`.

## Kafka topics

| Topic | Default name |
|-------|----------------|
| CCU | `fortnite.raw.ccu` |
| Shop | `fortnite.raw.shop` |
| Cosmetics | `fortnite.raw.cosmetics` |
| Ingestion status | `fortnite.ops.ingestion_status` |

## Health checks

```bash
python scripts/check_minio.py
python scripts/check_kafka.py
```

## DuckDB serving

```bash
python -m serving.duckdb_init
```

Predefined queries live in `serving/query_service.py` (no free-form SQL from the bot).

## Ingestion

```bash
python -m ingestion.ingest_ccu
python -m ingestion.ingest_shop
python -m ingestion.ingest_cosmetics
```

## Telegram bot

```bash
python -m bot.app
```

Supported intents: current CCU, avg CCU today, anomalies, shop summary, source health, help.

## Tests

```bash
python -m compileall .
python -m pytest
```

## Project layout

```
config/          settings
common/          logging, models, validators
producers/       Kafka producer
ingestion/       CCU, shop, cosmetics + clients
storage/         MinIO, paths, writers
serving/         DuckDB + query_service
bot/             Telegram handlers
scripts/         health checks
tests/           unit tests
docs/            architecture, runbook
```

## Troubleshooting

- **`python` permission denied:** activate `.venv` or run `scripts/setup-path.ps1`
- **Low RAM:** close apps before full Docker stack (~4 GB+ free recommended)
- **No bot data:** tables empty until pipelines populate DuckDB (Phase 1 returns structured no-data)

## Git

Development branch: `dev`. Never commit `.env`.
