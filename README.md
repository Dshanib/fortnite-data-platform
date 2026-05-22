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

```bash
# Default: up to 10 messages from fortnite.raw.shop
python scripts/kafka_to_bronze_once.py

python scripts/kafka_to_bronze_once.py --topic fortnite.raw.shop --max-messages 5
python scripts/kafka_to_bronze_once.py --topic fortnite.raw.island_metrics --max-messages 5
python scripts/kafka_to_bronze_once.py --full
```

Run ingestion first so Kafka topics contain data. Console: http://localhost:9001

**Important:** Ingestion writes to **Kafka only**. MinIO bronze is populated by `kafka_to_bronze_once.py` (not automatic). In the console, open `bronze/source=shop/` (not only `bronze/connectivity/` from the sample upload script).

## Silver (PySpark batch: Bronze JSON → Parquet)

### Prerequisites

- **Java 17+** (`JAVA_HOME` set)
- **PySpark** in the venv: `pip install -r requirements.txt`
- Bronze JSON already in MinIO (ingestion + `kafka_to_bronze_once.py`)
- Same MinIO variables as above (`MINIO_PROFILE`, `MINIO_ENDPOINT`, keys, bucket)

First Spark run downloads Hadoop AWS jars (~100MB).

### Run Bronze → Silver

```bash
# Recommended locally (fast, ~1 min): MinIO + PyArrow, no Spark JVM
pip install pandas pyarrow
python scripts/run_bronze_to_silver.py --engine python --sources shop,islands

# Full Spark path (first run may take 5–10 min for JAR download)
python scripts/run_bronze_to_silver.py --engine spark
```

Reads:

| Bronze prefix | Silver output |
|---------------|---------------|
| `bronze/source=shop/` | `silver/shop_items/` (partitioned by `snapshot_date`) |
| `bronze/source=cosmetics/` | `silver/cosmetics/` |
| `bronze/source=islands/` | `silver/islands/` |
| `bronze/source=island_metrics/` | `silver/island_metrics/` (partitioned by `metric_date`) |

Batch job only (no Structured Streaming yet).

## Gold (Silver Parquet → analytical Parquet)

Builds six gold datasets for analytics and the Telegram bot. Requires **silver** Parquet in MinIO; Kafka is not needed.

```bash
# Fast local path (recommended)
python scripts/run_silver_to_gold.py --engine python

# PySpark S3A path
python scripts/run_silver_to_gold.py --engine spark
```

| Gold dataset | Meaning |
|--------------|---------|
| `gold/current_island_activity` | Latest peak CCU, players, plays, minutes per island |
| `gold/top_islands_by_peak_ccu` | Islands ranked by peak CCU |
| `gold/island_metric_hourly` | Hourly avg/min/max per island metric |
| `gold/island_activity_anomalies` | peakCCU spikes vs rolling average / previous point |
| `gold/shop_rarity_distribution` | Item shop composition by cosmetic rarity (latest snapshot) |
| `gold/source_health_summary` | Ingestion success/failure counts from bronze health events |

Optional: `FORTNITE_GOLD_TOP_ISLANDS_N=10` limits the ranking table.

## DuckDB serving (Gold → queries)

DuckDB is the **serving/query layer** — not the storage layer. Gold Parquet stays in MinIO.

**Modes** (`DUCKDB_GOLD_READ_MODE`):

| Mode | Behavior |
|------|----------|
| `direct_minio` (default) | DuckDB `httpfs` reads `s3://<bucket>/gold/<dataset>/**/*.parquet` from MinIO |
| `local_cache` | Sync Gold to `GOLD_DATA_ROOT`, then read local Parquet (fallback if direct fails) |

```
MinIO gold/*.parquet  →  DuckDB views (direct_minio or local_cache)  →  QueryService  →  bot
```

### Configure

| Variable | Purpose |
|----------|---------|
| `DUCKDB_PATH` | Embedded DuckDB file (default `data/serving.duckdb`) |
| `DUCKDB_GOLD_READ_MODE` | `direct_minio` or `local_cache` |
| `GOLD_DATA_ROOT` | Local cache for `local_cache` mode (default `data/gold`) |
| `MINIO_*` | Used by `direct_minio` for S3-compatible access |
| `GOLD_*_PATH` | Optional per-dataset path/glob override |

### Initialize views and run checks

```bash
# Read Gold directly from MinIO (no local sync)
python scripts/check_duckdb_serving.py --mode direct_minio

# Local cache: sync from MinIO then query
python scripts/check_duckdb_serving.py --mode local_cache

# Local cache without re-download
python scripts/check_duckdb_serving.py --mode local_cache --skip-sync
```

Views: `vw_current_island_activity`, `vw_top_islands_by_peak_ccu`, `vw_island_metric_hourly`, `vw_island_activity_anomalies`, `vw_shop_rarity_distribution`, `vw_source_health_summary`.

`QueryService` returns `status` (`ok` / `no_data` / `error`), `message`, and `data` — never crashes on missing Gold data.

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

## Demo and continuous refresh

### One-shot demo run

Validates MinIO/Kafka, ingests APIs, writes bronze/silver/gold, and checks DuckDB serving:

```bash
python scripts/demo_run.py --serving-mode direct_minio
```

Flags: `--skip-ingestion`, `--skip-kafka-to-bronze`, `--skip-spark`, `--max-messages-per-topic 20`, `--serving-mode local_cache`.

Does **not** start the bot; at the end it prints `python -m bot.app`.

See [docs/continuous_execution_plan.md](docs/continuous_execution_plan.md) for the multi-process runtime model.

### Continuous mode (3 terminals)

**Terminal 1 — infrastructure**

```bash
docker compose up -d
```

**Terminal 2 — background refresh**

```bash
python scripts/continuous_refresh.py --interval-seconds 300 --serving-mode direct_minio
```

**Terminal 3 — Telegram bot**

```bash
python -m bot.app
```

### Data freshness

- **Ingestion** pulls latest API data into Kafka.
- **Kafka** buffers events until the bronze worker drains them.
- **Bronze** stores raw JSON in MinIO.
- **Spark/Python batch jobs** update Silver and Gold (including `island_activity_anomalies`).
- **DuckDB** reads the latest Gold Parquet (`direct_minio` or synced `local_cache`).
- The **Telegram bot** only queries the serving layer (`QueryService`); it does not update the lake.

After `continuous_refresh.py` completes a cycle, the bot sees new Gold data on the next query without restart.

### Limitations

- `continuous_refresh.py` is for local demo, not a production scheduler.
- **Airflow** / **Prefect** can replace the refresh loop later.
- Respect API rate limits; full island metrics may take several minutes.
- Low-activity islands often have **null** `peakCCU`, so top-island and anomaly lists may be short.

## Telegram bot

Requires a bot token in `.env`. Data is served via **QueryService** over DuckDB Gold views (MinIO or local cache).

```bash
source scripts/env.sh
python scripts/check_duckdb_serving.py --mode direct_minio
python -m bot.app
```

### Menu (primary UX — Hebrew)

| Command / action | Query |
|------------------|-------|
| `/start`, `/menu` | תפריט ראשי בעברית |
| **📊 כמה שחקנים מחוברים?** | `get_current_ccu()` |
| **🏆 האיים הכי פופולריים** | `get_top_islands(10)` |
| **🛒 מה יש בחנות היום?** | `get_shop_rarity_distribution()` |
| **⚠️ חריגות פעילות** | `get_recent_anomalies(10)` |
| **💬 עזרה ומדריך** | מדריך שימוש |
| **🏠 חזרה לתפריט** | חזרה מהתוצאה |

Free-text works in Hebrew or English (`פעילות`, `חנות`, `איים`, `חריגות`, `ccu`).

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
