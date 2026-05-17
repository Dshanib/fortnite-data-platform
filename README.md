# Fortnite Cloud DE — Phase 1

Modular data engineering foundation with **dual API ingestion**, Kafka, MinIO, DuckDB serving scaffold, and Telegram bot.

## Data sources (API only — no scraping)

| Source | URL | Used for |
|--------|-----|----------|
| [Fortnite-API.com](https://fortnite-api.com) | `https://fortnite-api.com` | Shop (`/v2/shop`), cosmetics (`/v2/cosmetics/br`) |
| [Fortnite Ecosystem API](https://api.fortnite.com/ecosystem/v1/docs/) | `https://api.fortnite.com/ecosystem/v1` | Islands, peak CCU, unique players, plays, minutes played |

Web scraping is **not** part of the primary architecture. `scrape_client.py` is deprecated.

See [docs/architecture.md](docs/architecture.md).

## Setup

```bash
cd d.e_proj
py -3.14 -m venv .venv
source scripts/env.sh
pip install -r requirements.txt
cp .env.example .env
```

Copy [`.env.example`](.env.example) to `.env` and add your **local** API keys and tokens there only.

Do **not** put secrets in this README or commit `.env` to git.

## Validate API connectivity

```bash
python scripts/test_fortnite_api.py
python scripts/test_fortnite_ecosystem_api.py
```

## Kafka

Local defaults (see `.env.example`):

- Zookeeper: `localhost:2181`
- Kafka broker: `localhost:9092`

### Start Kafka (Zookeeper + broker)

```bash
docker compose --env-file .env up -d zookeeper kafka
```

Wait ~30 seconds for Kafka to become ready.

### Create topics (idempotent)

```bash
python scripts/create_kafka_topics.py
```

### Validate producer connectivity

```bash
python scripts/check_kafka.py
```

Sends one small JSON test event to `fortnite.ops.ingestion_status` and prints success/failure with a timestamp.

### Kafka topics

| Topic | Producer |
|-------|----------|
| `fortnite.raw.shop` | `ingest_shop` |
| `fortnite.raw.cosmetics` | `ingest_cosmetics` |
| `fortnite.raw.islands` | `ingest_islands` |
| `fortnite.raw.island_metrics` | `ingest_island_metrics` |
| `fortnite.ops.ingestion_status` | ingestion health |

For LAN/external clients, adjust `KAFKA_ADVERTISED_LISTENERS` in `docker-compose.yml` (see comments there).

## MinIO (Bronze landing zone)

Credentials and endpoint are read from `.env` only — never commit secrets.

### Profiles

| Profile | Use case | Example `MINIO_ENDPOINT` |
|---------|----------|---------------------------|
| `internal` | Local Docker MinIO | `http://localhost:9000` |
| `external` | Remote MinIO / LAN host | `http://192.168.1.50:9000` |

Set `MINIO_PROFILE`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE` in `.env`. See `.env.internal.example` / `.env.external.example`.

### Start and verify

```bash
docker compose --env-file .env up -d minio
python scripts/check_minio.py
```

### Kafka → Bronze (JSON, one-shot consumer)

Bronze stores **raw Kafka event JSON** (full envelope + payload) with minimal transformation. Paths are hive-style:

`bronze/source=shop/event_date=YYYY-MM-DD/raw_shop_<timestamp>_<uuid>.json`

Silver/Gold **Parquet** layers come later (Spark processing).

```bash
# Default: up to 10 messages from fortnite.raw.shop
python scripts/kafka_to_bronze_once.py

python scripts/kafka_to_bronze_once.py --topic fortnite.raw.shop --max-messages 5
python scripts/kafka_to_bronze_once.py --topic fortnite.raw.island_metrics --max-messages 5
python scripts/kafka_to_bronze_once.py --full
```

Run ingestion first so Kafka topics contain data. Console: http://localhost:9001

## Ingestion

Requires Kafka running and topics created (see **Kafka** above). Each pipeline publishes a standard envelope (`event_id`, `source_name`, `event_type`, `event_time`, `ingested_at`, `request_status`, `latency_ms`, `payload`) with the **full raw API JSON** in `payload`, plus a health event to `fortnite.ops.ingestion_status`.

```bash
python -m ingestion.ingest_shop
python -m ingestion.ingest_cosmetics
python -m ingestion.ingest_islands
python -m ingestion.ingest_island_metrics
python scripts/run_all_ingestion_once.py
```

`run_all_ingestion_once.py` runs shop, cosmetics, islands, and **one** island metrics fetch (first island or `FORTNITE_ECOSYSTEM_DEMO_ISLAND_CODE` in `.env`). Full `ingest_island_metrics` without `max_islands` processes all islands returned by the API.

Cosmetics are published in **chunks** (`FORTNITE_COSMETICS_KAFKA_CHUNK_SIZE`, default `400`) so each Kafka message stays under broker size limits. Each chunk payload includes `ingestion_batch` metadata for reassembly downstream.

## Telegram bot

Requires a bot token in `.env` (see `.env.example`).

```bash
source scripts/env.sh
python -m bot.app
```

Example queries: `current ccu`, `average today`, `shop`, `health`. Bot uses mock `query_service` until DuckDB is wired.

**Future bot intents (documented):** per-island peak CCU, top islands by plays — not implemented yet.

## Tests

```bash
python -m compileall .
python -m pytest
```

## CI

On every **push** or **pull request** to `main` / `dev`, GitHub Actions runs:

- `python -m compileall .`
- `python -m pytest`

Workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). No secrets required (tests use mocked env from `tests/conftest.py`).

## Troubleshooting

- **Ecosystem 401/403:** configure Epic OAuth in `.env` (see `.env.example`)
- **Ecosystem 429:** rate limited; retry later or reduce `FORTNITE_ECOSYSTEM_ISLAND_PAGE_SIZE`
- **`python` permission denied:** use `source scripts/env.sh`
- **Unicode console errors (Windows):** scripts auto-configure UTF-8; or run  
  `set PYTHONIOENCODING=utf-8` (cmd) / `$env:PYTHONIOENCODING='utf-8'` (PowerShell)
- **Kafka connection refused:** start `zookeeper` and `kafka` via Docker Compose first

## Git

Development branch: `dev`. Never commit `.env`.
