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

| Topic | Future producer |
|-------|-----------------|
| `fortnite.raw.shop` | `ingest_shop` |
| `fortnite.raw.cosmetics` | `ingest_cosmetics` |
| `fortnite.raw.islands` | `ingest_islands` |
| `fortnite.raw.island_metrics` | `ingest_island_metrics` |
| `fortnite.ops.ingestion_status` | health / connectivity |

Ingestion pipelines are **not** wired to Kafka in this validation phase.

For LAN/external clients, adjust `KAFKA_ADVERTISED_LISTENERS` in `docker-compose.yml` (see comments there).

## Docker (MinIO + full stack)

Infra credentials are read from your **local `.env` only** (not documented here).

```bash
docker compose --env-file .env up -d minio
python scripts/check_minio.py
python scripts/send_minio_test_data.py
```

`send_minio_test_data.py` writes one sample JSON object under each medallion prefix (`bronze/`, `silver/`, `gold/`) using paths like `{layer}/{entity}/{YYYY/MM/DD}/{file}.json`.

## Ingestion

```bash
python -m ingestion.ingest_shop
python -m ingestion.ingest_cosmetics
python -m ingestion.ingest_islands
python -m ingestion.ingest_island_metrics
```

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
