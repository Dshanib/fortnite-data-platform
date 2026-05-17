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

Edit `.env`:

- `FORTNITE_API_KEY` — optional, for Fortnite-API.com
- `FORTNITE_CLIENT_ID` / `FORTNITE_CLIENT_SECRET` — optional, for Ecosystem API OAuth
- `TELEGRAM_BOT_TOKEN`, MinIO, Kafka settings

## Validate API connectivity

```bash
python scripts/test_fortnite_api.py
python scripts/test_fortnite_ecosystem_api.py
```

## Docker (Kafka + MinIO)

```bash
docker compose up -d
python scripts/check_minio.py
python scripts/check_kafka.py
```

## Kafka topics

| Topic | Producer |
|-------|----------|
| `fortnite.raw.shop` | `ingest_shop` |
| `fortnite.raw.cosmetics` | `ingest_cosmetics` |
| `fortnite.raw.islands` | `ingest_islands` |
| `fortnite.raw.island_metrics` | `ingest_island_metrics` |
| `fortnite.ops.ingestion_status` | all pipelines |

## Ingestion

```bash
python -m ingestion.ingest_shop
python -m ingestion.ingest_cosmetics
python -m ingestion.ingest_islands
python -m ingestion.ingest_island_metrics
```

## Telegram bot

Requires `TELEGRAM_BOT_TOKEN` in `.env`.

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

## Troubleshooting

- **Ecosystem 401/403:** set Epic OAuth credentials in `.env`
- **Ecosystem 429:** rate limited; retry later or reduce `FORTNITE_ECOSYSTEM_ISLAND_PAGE_SIZE`
- **`python` permission denied:** use `source scripts/env.sh`

## Git

Development branch: `dev`. Never commit `.env`.
